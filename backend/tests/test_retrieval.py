import uuid
from unittest.mock import AsyncMock

import pytest

from app.db.models import Chunk
from app.retrieval.vector import RetrievedChunk, search_vector


@pytest.mark.asyncio
async def test_search_vector_empty_query() -> None:
    db = AsyncMock()
    results = await search_vector("", uuid.uuid4(), db)
    assert results == []


@pytest.mark.asyncio
async def test_search_vector_execution(monkeypatch: pytest.MonkeyPatch) -> None:
    paper_id = uuid.uuid4()
    chunk1_id = uuid.uuid4()
    chunk2_id = uuid.uuid4()

    chunk1 = Chunk(
        id=chunk1_id,
        paper_id=paper_id,
        section="methodology",
        page_start=2,
        page_end=2,
        text="Dense retrieval using pgvector HNSW index.",
        bbox={"bounds": [50, 100, 400, 150]},
        embedding=[0.1] * 768,
    )
    chunk2 = Chunk(
        id=chunk2_id,
        paper_id=paper_id,
        section="abstract",
        page_start=1,
        page_end=1,
        text="Abstract of the research paper.",
        bbox={"bounds": [50, 50, 400, 90]},
        embedding=[0.2] * 768,
    )

    # Mock DB execute result: list of (Chunk, distance)
    class MockResult:
        def all(self):
            return [
                (chunk1, 0.15),
                (chunk2, 0.40),
            ]

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=MockResult())

    results: list[RetrievedChunk] = await search_vector(
        query="How does dense retrieval work?",
        paper_id=paper_id,
        db=mock_db,
        top_k=5,
    )

    assert len(results) == 2
    assert results[0].chunk_id == chunk1_id
    assert results[0].section == "methodology"
    assert results[0].similarity_score == 0.85
    assert results[0].page_start == 2

    assert results[1].chunk_id == chunk2_id
    assert results[1].section == "abstract"
    assert results[1].similarity_score == 0.60

    # Pastikan execute query dipanggil dengan benar
    assert mock_db.execute.called
