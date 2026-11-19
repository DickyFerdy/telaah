import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Chunk
from app.ingest.embedder import embed


@dataclass
class RetrievedChunk:
    chunk_id: uuid.UUID
    paper_id: uuid.UUID
    section: str | None
    page_start: int | None
    page_end: int | None
    text: str
    bbox: dict[str, Any] | None
    similarity_score: float  # Nilai antara 0.0 s/d 1.0 (1.0 = identik)


async def search_vector(
    query: str,
    paper_id: uuid.UUID,
    db: AsyncSession,
    top_k: int = 5,
) -> list[RetrievedChunk]:
    """
    Melakukan pencarian semantik vektor pada chunk paper menggunakan operator cosine distance pgvector (<=>).
    
    Langkah:
    1. Mengubah query menjadi embedding vektor 768-dimensi dengan task 'RETRIEVAL_QUERY'.
    2. Menghitung jarak kosinus terhadap kolom `chunks.embedding` yang memiliki indeks HNSW.
    3. Mengurutkan hasil dari jarak terkecil (kemiripan tertinggi) dan membatasi `top_k`.
    """
    cleaned_query = query.strip()
    if not cleaned_query:
        return []

    # 1. Dapatkan embedding query
    query_vectors = await embed([cleaned_query], task="RETRIEVAL_QUERY")
    if not query_vectors or not query_vectors[0]:
        return []
    query_vector = query_vectors[0]

    # 2. Definisikan ekspresi jarak kosinus pgvector
    # chunk.embedding.cosine_distance(query_vector) menghasilkan nilai jarak antara 0 (identik) s/d 2 (berlawanan)
    distance_expr = Chunk.embedding.cosine_distance(query_vector).label("distance")

    stmt = (
        select(Chunk, distance_expr)
        .where(Chunk.paper_id == paper_id, Chunk.embedding.is_not(None))
        .order_by(distance_expr.asc())
        .limit(top_k)
    )

    result = await db.execute(stmt)
    rows = result.all()

    retrieved: list[RetrievedChunk] = []
    for chunk, distance in rows:
        # Konversi jarak kosinus ke skor kesamaan: similarity = 1.0 - (distance / 2.0) atau 1.0 - distance
        # Untuk vektor ter-normalisasi satuan, cosine_similarity = 1.0 - distance
        dist_val = float(distance) if distance is not None else 1.0
        similarity = round(max(0.0, 1.0 - dist_val), 4)

        retrieved.append(
            RetrievedChunk(
                chunk_id=chunk.id,
                paper_id=chunk.paper_id,
                section=chunk.section,
                page_start=chunk.page_start,
                page_end=chunk.page_end,
                text=chunk.text,
                bbox=chunk.bbox,
                similarity_score=similarity,
            )
        )

    return retrieved
