import uuid

import pytest
from httpx import Request, Response

from app.core.config import settings
from app.retrieval.reranker import rerank_chunks
from app.retrieval.vector import RetrievedChunk


def make_chunk(text: str, score: float = 0.5) -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=uuid.uuid4(),
        paper_id=uuid.uuid4(),
        section="experiments_results",
        page_start=1,
        page_end=1,
        text=text,
        bbox={},
        similarity_score=score,
    )


@pytest.mark.asyncio
async def test_rerank_chunks_few_items() -> None:
    chunks = [make_chunk("Chunk 1"), make_chunk("Chunk 2")]
    # Jika item <= top_n, langsung return
    res = await rerank_chunks("query", chunks, top_n=5)
    assert len(res) == 2


@pytest.mark.asyncio
async def test_rerank_chunks_fallback_lexical(monkeypatch: pytest.MonkeyPatch) -> None:
    # Set api key kosong -> menguji fallback leksikal
    monkeypatch.setattr(settings, "gemini_api_key", "")

    chunks = [
        make_chunk("Irrelevant text about astronomy.", score=0.9),
        make_chunk("Highly relevant text discussing neural network optimization.", score=0.6),
        make_chunk("General introduction to mathematics.", score=0.5),
    ]

    res = await rerank_chunks("neural network optimization", chunks, top_n=2)
    assert len(res) == 2
    # Chunk ke-2 memiliki overlap kata terbanyak -> harus naik ke peringkat 1
    assert "neural network optimization" in res[0].text


@pytest.mark.asyncio
async def test_rerank_chunks_gemini_mock(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "gemini_api_key", "mock-gemini-key")

    chunks = [
        make_chunk("Alpha chunk"),
        make_chunk("Beta chunk"),
        make_chunk("Gamma chunk"),
    ]

    # Mock response Gemini mengembalikan indeks [2, 0] (Gamma lalu Alpha)
    mock_payload = {
        "candidates": [
            {
                "content": {
                    "parts": [{"text": "[2, 0]"}]
                }
            }
        ]
    }

    async def mock_post(self, url, *args, **kwargs):
        req = Request("POST", str(url))
        return Response(200, json=mock_payload, request=req)

    monkeypatch.setattr("httpx.AsyncClient.post", mock_post)

    res = await rerank_chunks("test query", chunks, top_n=2)
    assert len(res) == 2
    assert res[0].text == "Gamma chunk"
    assert res[1].text == "Alpha chunk"
