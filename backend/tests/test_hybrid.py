import uuid
from unittest.mock import AsyncMock

import pytest
from app.db.models import Chunk
from app.retrieval.hybrid import reciprocal_rank_fusion, search_hybrid
from app.retrieval.keyword import search_keyword
from app.retrieval.vector import RetrievedChunk


def make_retrieved_chunk(
    chunk_id: uuid.UUID, paper_id: uuid.UUID, text: str, score: float = 0.5
) -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=chunk_id,
        paper_id=paper_id,
        section="methodology",
        page_start=1,
        page_end=1,
        text=text,
        bbox={},
        similarity_score=score,
    )


def test_reciprocal_rank_fusion_scoring() -> None:
    paper_id = uuid.uuid4()
    id_a = uuid.uuid4()
    id_b = uuid.uuid4()
    id_c = uuid.uuid4()

    # List 1 (misal dari Vektor): A (rank 1), B (rank 2)
    list_vector = [
        make_retrieved_chunk(id_a, paper_id, "Document A"),
        make_retrieved_chunk(id_b, paper_id, "Document B"),
    ]

    # List 2 (misal dari Keyword): B (rank 1), C (rank 2)
    list_keyword = [
        make_retrieved_chunk(id_b, paper_id, "Document B"),
        make_retrieved_chunk(id_c, paper_id, "Document C"),
    ]

    # Dokumen B muncul di kedua daftar -> seharusnya memiliki skor RRF tertinggi!
    # Skor A: 1 / (60 + 1) = 0.01639
    # Skor B: 1 / (60 + 2) + 1 / (60 + 1) = 0.016129 + 0.016393 = 0.03252
    # Skor C: 1 / (60 + 2) = 0.01612
    fused = reciprocal_rank_fusion([list_vector, list_keyword], k=60, top_k=3)

    assert len(fused) == 3
    assert fused[0].chunk_id == id_b, "Dokumen B harus menjadi juara pertama karena ada di kedua daftar"
    assert fused[1].chunk_id == id_a
    assert fused[2].chunk_id == id_c
    assert fused[0].similarity_score > fused[1].similarity_score
    assert fused[1].similarity_score > fused[2].similarity_score


@pytest.mark.asyncio
async def test_search_keyword_execution() -> None:
    paper_id = uuid.uuid4()
    chunk_id = uuid.uuid4()
    mock_chunk = Chunk(
        id=chunk_id,
        paper_id=paper_id,
        section="abstract",
        page_start=1,
        page_end=1,
        text="Sample text matching keyword.",
        bbox={},
    )

    class MockResult:
        def all(self):
            return [(mock_chunk, 0.45)]

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=MockResult())

    results = await search_keyword("sample keyword", paper_id=paper_id, db=mock_db)
    assert len(results) == 1
    assert results[0].chunk_id == chunk_id
    assert results[0].similarity_score == 0.45


@pytest.mark.asyncio
async def test_search_hybrid_execution(monkeypatch: pytest.MonkeyPatch) -> None:
    paper_id = uuid.uuid4()
    id_1 = uuid.uuid4()
    id_2 = uuid.uuid4()

    chunk_1 = make_retrieved_chunk(id_1, paper_id, "Vector result")
    chunk_2 = make_retrieved_chunk(id_2, paper_id, "Keyword result")

    async def mock_search_vector(*args, **kwargs):
        return [chunk_1]

    async def mock_search_keyword(*args, **kwargs):
        return [chunk_2]

    monkeypatch.setattr("app.retrieval.hybrid.search_vector", mock_search_vector)
    monkeypatch.setattr("app.retrieval.hybrid.search_keyword", mock_search_keyword)

    mock_db = AsyncMock()
    results = await search_hybrid("hybrid test query", paper_id=paper_id, db=mock_db, top_k=2)

    assert len(results) == 2
    ids = [r.chunk_id for r in results]
    assert id_1 in ids
    assert id_2 in ids
