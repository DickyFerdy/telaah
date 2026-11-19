import asyncio
import uuid
from collections import defaultdict

from sqlalchemy.ext.asyncio import AsyncSession

from app.retrieval.keyword import search_keyword
from app.retrieval.reranker import rerank_chunks
from app.retrieval.vector import RetrievedChunk, search_vector

RRF_CONSTANT_K = 60


def reciprocal_rank_fusion(
    ranked_lists: list[list[RetrievedChunk]],
    k: int = RRF_CONSTANT_K,
    top_k: int = 5,
) -> list[RetrievedChunk]:
    """
    Menggabungkan beberapa daftar peringkat (vektor dan kata kunci) menggunakan Reciprocal Rank Fusion (RRF).
    
    Rumus: RRF_Score(d) = SUM( 1 / (k + rank(d)) )
    di mana rank(d) adalah posisi dokumen d (1-indexed: 1, 2, ...).
    """
    rrf_scores: dict[uuid.UUID, float] = defaultdict(float)
    chunk_map: dict[uuid.UUID, RetrievedChunk] = {}

    for ranked_list in ranked_lists:
        for rank, chunk in enumerate(ranked_list, start=1):
            rrf_scores[chunk.chunk_id] += 1.0 / (k + rank)
            if chunk.chunk_id not in chunk_map:
                chunk_map[chunk.chunk_id] = chunk

    # Urutkan berdasarkan skor RRF tertinggi
    sorted_chunk_ids = sorted(
        rrf_scores.keys(),
        key=lambda cid: rrf_scores[cid],
        reverse=True,
    )

    fused_results: list[RetrievedChunk] = []
    for cid in sorted_chunk_ids[:top_k]:
        base_chunk = chunk_map[cid]
        # Buat salinan dengan similarity_score diisi skor RRF (dinormalisasi 4 desimal)
        fused_chunk = RetrievedChunk(
            chunk_id=base_chunk.chunk_id,
            paper_id=base_chunk.paper_id,
            section=base_chunk.section,
            page_start=base_chunk.page_start,
            page_end=base_chunk.page_end,
            text=base_chunk.text,
            bbox=base_chunk.bbox,
            similarity_score=round(rrf_scores[cid], 6),
        )
        fused_results.append(fused_chunk)

    return fused_results


async def search_hybrid(
    query: str,
    paper_id: uuid.UUID,
    db: AsyncSession,
    top_k: int = 5,
    candidates_limit: int = 20,
) -> list[RetrievedChunk]:
    """
    Melakukan pencarian hibrida menggabungkan:
    1. Dense Vector Search (pgvector Cosine distance via HNSW)
    2. Sparse Keyword Search (PostgreSQL full-text search ts_rank via GIN)
    
    Kedua pencarian dieksekusi secara paralel menggunakan `asyncio.gather`,
    lalu digabungkan menggunakan algoritma Reciprocal Rank Fusion (RRF).
    """
    cleaned_query = query.strip()
    if not cleaned_query:
        return []

    # Jalankan kedua pencarian secara simultan
    vector_task = search_vector(
        cleaned_query, paper_id=paper_id, db=db, top_k=candidates_limit
    )
    keyword_task = search_keyword(
        cleaned_query, paper_id=paper_id, db=db, top_k=candidates_limit
    )

    vector_results, keyword_results = await asyncio.gather(
        vector_task, keyword_task
    )

    # Gabungkan dengan RRF
    fused_candidates = reciprocal_rank_fusion(
        ranked_lists=[vector_results, keyword_results],
        k=RRF_CONSTANT_K,
        top_k=candidates_limit,
    )

    # 3. Jalankan Cross-Encoder Reranker pada kandidat RRF
    return await rerank_chunks(
        query=cleaned_query,
        chunks=fused_candidates,
        top_n=top_k,
    )
