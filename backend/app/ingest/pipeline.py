import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Paper
from app.db.session import async_session_maker
from app.ingest.chunker import chunk_document_sections
from app.ingest.embedder import embed
from app.ingest.parser import parse_pdf
from app.ingest.sections import identify_document_sections
from app.ingest.storage import save_chunks_to_db

logger = logging.getLogger(__name__)


async def run_ingest_pipeline(
    paper_id: uuid.UUID,
    session: AsyncSession | None = None,
) -> None:
    """
    Menjalankan pipeline ingest paper ilmiah secara asinkron di latar belakang.
    
    Tahapan:
    1. Parsing PDF (ekstraksi teks per halaman & bounding box) -> status: 'parsing'
    2. Deteksi struktur bagian (abstract, methods, results, references)
    3. Chunking teks sadar bagian (section-aware chunking)
    4. Batch embedding (Gemini API) & simpan ke pgvector -> status: 'embedding'
    5. Penyelesaian -> status: 'ready'
    6. Penanganan error -> status: 'failed' + simpan error_message
    """
    logger.info(f"[Ingest Pipeline] Memulai pemrosesan paper {paper_id}")

    # Menggunakan sesi yang diberikan (misal saat testing) atau membuat sesi baru
    if session is not None:
        await _execute_pipeline(paper_id, session)
    else:
        async with async_session_maker() as db:
            await _execute_pipeline(paper_id, db)


async def _execute_pipeline(paper_id: uuid.UUID, db: AsyncSession) -> None:
    # 1. Ambil record paper
    paper = await db.scalar(select(Paper).where(Paper.id == paper_id))
    if not paper:
        logger.error(f"[Ingest Pipeline] Paper {paper_id} tidak ditemukan di database.")
        return

    try:
        # Update status -> parsing
        paper.status = "parsing"
        paper.error_message = None
        await db.commit()
        await db.refresh(paper)

        # 2. Parse PDF
        logger.info(f"[Ingest Pipeline] Mengekstrak teks PDF: {paper.file_path}")
        parsed_doc = parse_pdf(paper.file_path)
        paper.page_count = parsed_doc.total_pages
        await db.commit()

        # 3. Deteksi bagian
        logger.info(f"[Ingest Pipeline] Mengidentifikasi bagian dokumen ({parsed_doc.total_pages} halaman)")
        sections = identify_document_sections(parsed_doc)

        # 4. Chunking sadar bagian
        logger.info("[Ingest Pipeline] Melakukan chunking sadar bagian")
        chunks = chunk_document_sections(sections)

        if not chunks:
            raise ValueError("Tidak ada teks atau chunk yang berhasil diekstrak dari dokumen PDF.")

        # Update status -> embedding
        paper.status = "embedding"
        await db.commit()
        await db.refresh(paper)

        # 5. Batch embedding
        logger.info(f"[Ingest Pipeline] Menghasilkan embedding untuk {len(chunks)} chunks")
        chunk_texts = [c.text for c in chunks]
        embeddings = await embed(chunk_texts, task="RETRIEVAL_DOCUMENT")

        # 6. Simpan chunks & embeddings ke database
        logger.info("[Ingest Pipeline] Menyimpan chunks dan vektor ke PostgreSQL")
        await save_chunks_to_db(
            paper_id=paper.id,
            chunks=chunks,
            embeddings=embeddings,
            db=db,
        )

        # 7. Selesai -> status ready
        paper.status = "ready"
        await db.commit()
        logger.info(f"[Ingest Pipeline] Paper {paper_id} berhasil diproses. Status: READY")

    except Exception as exc:
        logger.exception(f"[Ingest Pipeline] Terjadi kesalahan saat memproses paper {paper_id}")
        await db.rollback()
        paper.status = "failed"
        paper.error_message = str(exc)
        await db.commit()
