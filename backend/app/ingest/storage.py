import uuid
from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Chunk
from app.ingest.chunker import DocumentChunk


async def save_chunks_to_db(
    paper_id: uuid.UUID,
    chunks: Sequence[DocumentChunk],
    embeddings: Sequence[list[float]],
    db: AsyncSession,
) -> list[Chunk]:
    """
    Menyimpan daftar DocumentChunk beserta vektor embedding ke tabel `chunks` di PostgreSQL.
    """
    if len(chunks) != len(embeddings):
        raise ValueError(
            f"Jumlah chunks ({len(chunks)}) dan embeddings ({len(embeddings)}) harus sama."
        )

    db_chunks: list[Chunk] = []

    for chunk, emb in zip(chunks, embeddings, strict=True):
        chunk_record = Chunk(
            id=uuid.uuid4(),
            paper_id=paper_id,
            section=chunk.section,
            page_start=chunk.page_start,
            page_end=chunk.page_end,
            text=chunk.text,
            bbox=chunk.bbox,
            embedding=emb,
            tsv=None,  # Akan diisi di item berikutnya (kolom tsv pencarian kata kunci)
            token_count=chunk.token_count,
        )
        db.add(chunk_record)
        db_chunks.append(chunk_record)

    await db.commit()
    return db_chunks
