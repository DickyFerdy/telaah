import asyncio
import logging
from typing import Literal

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

EMBEDDING_MODEL = "text-embedding-004"
EMBEDDING_DIM = 768
GEMINI_API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{EMBEDDING_MODEL}:batchEmbedContents"

# Task type valid Gemini: "RETRIEVAL_DOCUMENT", "RETRIEVAL_QUERY", "SEMANTIC_SIMILARITY", dll.
TaskType = Literal["RETRIEVAL_DOCUMENT", "RETRIEVAL_QUERY", "SEMANTIC_SIMILARITY"]


def _generate_synthetic_embedding(text: str, dim: int = EMBEDDING_DIM) -> list[float]:
    """
    Fallback deterministik untuk mode pengujian atau saat API key tidak disetel.
    Menghasilkan vektor 768-dimensi yang dinormalisasi.
    """
    import hashlib
    import math

    seed = int(hashlib.sha256(text.encode("utf-8")).hexdigest()[:8], 16)
    vector = []
    norm = 0.0
    for i in range(dim):
        val = math.sin(seed + i)
        vector.append(val)
        norm += val * val
    norm = math.sqrt(norm)
    return [round(v / norm, 6) for v in vector]


async def embed(
    texts: list[str],
    task: TaskType = "RETRIEVAL_DOCUMENT",
    batch_size: int = 20,
    max_retries: int = 4,
) -> list[list[float]]:
    """
    Antarmuka tunggal untuk menghasilkan vektor embedding.
    
    Fitur:
    - Task type: 'RETRIEVAL_DOCUMENT' (untuk chunking) atau 'RETRIEVAL_QUERY' (untuk query user).
    - Batching otomatis (maks. 20 item per request ke Gemini).
    - Rate limit protection: exponential backoff saat HTTP 429.
    - Fallback sintetis jika `GEMINI_API_KEY` kosong (mempermudah unit testing offline).
    """
    if not texts:
        return []

    api_key = settings.gemini_api_key.strip()
    if not api_key or api_key.startswith("AQ.") or settings.environment == "testing":
        logger.warning(
            "GEMINI_API_KEY tidak disetel atau dummy key. Menggunakan synthetic embeddings untuk pengujian."
        )
        return [_generate_synthetic_embedding(t, EMBEDDING_DIM) for t in texts]

    results: list[list[float]] = []

    async with httpx.AsyncClient(timeout=30.0) as client:
        # Proses per batch
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            requests_payload = []
            for t in batch:
                requests_payload.append(
                    {
                        "model": f"models/{EMBEDDING_MODEL}",
                        "content": {"parts": [{"text": t}]},
                        "taskType": task,
                        "outputDimensionality": EMBEDDING_DIM,
                    }
                )

            payload = {"requests": requests_payload}
            delay = 2.0

            for attempt in range(max_retries):
                try:
                    resp = await client.post(
                        f"{GEMINI_API_URL}?key={api_key}",
                        json=payload,
                        headers={"Content-Type": "application/json"},
                    )

                    # Jika kena rate limit (429)
                    if resp.status_code == 429:
                        if attempt == max_retries - 1:
                            resp.raise_for_status()
                        logger.warning(
                            f"Rate limit Gemini (429). Menunggu {delay} detik (percobaan {attempt + 1}/{max_retries})..."
                        )
                        await asyncio.sleep(delay)
                        delay *= 2
                        continue

                    resp.raise_for_status()
                    data = resp.json()
                    raw_embeddings = data.get("embeddings", [])
                    for item in raw_embeddings:
                        values = item.get("values", [])
                        if len(values) != EMBEDDING_DIM:
                            raise ValueError(
                                f"Dimensi embedding tidak sesuai: diharapkan {EMBEDDING_DIM}, diterima {len(values)}"
                            )
                        results.append(values)
                    break
                except httpx.HTTPError as exc:
                    if attempt == max_retries - 1:
                        raise RuntimeError(
                            f"Gagal memanggil API embedding Gemini setelah {max_retries} percobaan: {exc!s}"
                        ) from exc
                    await asyncio.sleep(delay)
                    delay *= 2

            # Jeda kecil antar batch untuk mencegah spike kuota rate-limit
            if i + batch_size < len(texts):
                await asyncio.sleep(0.5)

    return results
