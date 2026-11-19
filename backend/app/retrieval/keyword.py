import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Chunk
from app.retrieval.vector import RetrievedChunk


async def search_keyword(
    query: str,
    paper_id: uuid.UUID,
    db: AsyncSession,
    top_k: int = 10,
) -> list[RetrievedChunk]:
    """
    Melakukan pencarian kata kunci (full-text search) menggunakan indeks GIN pada kolom `chunks.tsv`.
    
    Langkah:
    1. Mengubah query menjadi `plainto_tsquery('english', query)`.
    2. Menghitung peringkat relevansi menggunakan `ts_rank(chunks.tsv, query_ts)`.
    3. Mengurutkan hasil dari skor rank tertinggi dan membatasi `top_k`.
    """
    cleaned_query = query.strip()
    if not cleaned_query:
        return []

    # plainto_tsquery memproses kata-kata alami dan mengabaikan operator boolean liar
    ts_query = func.plainto_tsquery("english", cleaned_query)
    rank_expr = func.ts_rank(Chunk.tsv, ts_query).label("rank")

    stmt = (
        select(Chunk, rank_expr)
        .where(
            Chunk.paper_id == paper_id,
            Chunk.tsv.op("@@")(ts_query),
        )
        .order_by(rank_expr.desc())
        .limit(top_k)
    )

    result = await db.execute(stmt)
    rows = result.all()

    retrieved: list[RetrievedChunk] = []
    for chunk, rank in rows:
        rank_val = float(rank) if rank is not None else 0.0
        retrieved.append(
            RetrievedChunk(
                chunk_id=chunk.id,
                paper_id=chunk.paper_id,
                section=chunk.section,
                page_start=chunk.page_start,
                page_end=chunk.page_end,
                text=chunk.text,
                bbox=chunk.bbox,
                similarity_score=round(rank_val, 4),
            )
        )

    return retrieved
