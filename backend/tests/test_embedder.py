import pytest
from app.core.config import settings
from app.ingest.embedder import EMBEDDING_DIM, embed
from httpx import Request, Response


@pytest.mark.asyncio
async def test_embed_synthetic_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    # Uji saat GEMINI_API_KEY kosong -> menggunakan synthetic embedding
    monkeypatch.setattr(settings, "gemini_api_key", "")

    texts = [
        "Attention is all you need for sequence transduction.",
        "Retrieval Augmented Generation combines pre-trained parametric memory.",
    ]
    vectors = await embed(texts, task="RETRIEVAL_DOCUMENT")

    assert len(vectors) == 2
    assert len(vectors[0]) == EMBEDDING_DIM
    assert len(vectors[1]) == EMBEDDING_DIM
    # Vektor harus ternormalisasi (~1.0 magnitude)
    norm = sum(v * v for v in vectors[0])
    assert pytest.approx(norm, rel=1e-2) == 1.0


@pytest.mark.asyncio
async def test_embed_empty_input() -> None:
    vectors = await embed([])
    assert vectors == []


@pytest.mark.asyncio
async def test_embed_gemini_api_mock(monkeypatch: pytest.MonkeyPatch) -> None:
    # Uji saat GEMINI_API_KEY terisi dengan mock respon Gemini batchEmbedContents
    monkeypatch.setattr(settings, "gemini_api_key", "test-api-key")

    mock_values = [0.05] * EMBEDDING_DIM
    mock_payload = {
        "embeddings": [
            {"values": mock_values},
            {"values": mock_values},
        ]
    }

    async def mock_post(self, url, *args, **kwargs):
        req = Request("POST", str(url))
        return Response(200, json=mock_payload, request=req)

    monkeypatch.setattr("httpx.AsyncClient.post", mock_post)

    texts = ["First query sentence", "Second query sentence"]
    vectors = await embed(texts, task="RETRIEVAL_QUERY", batch_size=2)

    assert len(vectors) == 2
    assert len(vectors[0]) == EMBEDDING_DIM
    assert vectors[0][0] == 0.05
