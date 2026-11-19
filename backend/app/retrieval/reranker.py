import json
import logging
from collections.abc import Sequence

import httpx

from app.core.config import settings
from app.retrieval.vector import RetrievedChunk

logger = logging.getLogger(__name__)

GEMINI_RERANK_MODEL = "gemini-1.5-flash"
GEMINI_GENERATE_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_RERANK_MODEL}:generateContent"


def _fallback_rerank(
    query: str, chunks: Sequence[RetrievedChunk], top_n: int
) -> list[RetrievedChunk]:
    """
    Fallback deterministik berbasis tumpang-tindih leksikal (lexical overlap)
    dan skor kemiripan awal saat API key tidak aktif atau terjadi error jaringan.
    """
    query_terms = set(query.lower().split())

    def score_chunk(c: RetrievedChunk) -> float:
        chunk_words = set(c.text.lower().replace(".", " ").replace(",", " ").split())
        overlap = len(query_terms.intersection(chunk_words))
        # Bobot overlap kata dinaikkan agar kata kunci spesifik lebih dominan dari skor awal
        return overlap * 10.0 + (c.similarity_score or 0.0)

    sorted_chunks = sorted(chunks, key=score_chunk, reverse=True)
    return list(sorted_chunks[:top_n])


async def rerank_chunks(
    query: str,
    chunks: Sequence[RetrievedChunk],
    top_n: int = 5,
    timeout: float = 10.0,
) -> list[RetrievedChunk]:
    """
    Melakukan pemeringkatan ulang (reranking) pada daftar kandidat chunk
    menggunakan model cepat Gemini Flash untuk menilai interaksi mendalam antara query dan dokumen.
    
    Fitur:
    - Jika kandidat <= top_n, langsung kembalikan tanpa membebani LLM.
    - Menghasilkan daftar indeks yang paling relevan dengan pertanyaan.
    - Fallback otomatis ke skor awal jika API key kosong atau respons gagal.
    """
    if not chunks:
        return []

    if len(chunks) <= top_n:
        return list(chunks)

    api_key = settings.gemini_api_key.strip()
    if not api_key:
        logger.warning(
            "GEMINI_API_KEY tidak disetel. Menggunakan fallback reranking."
        )
        return _fallback_rerank(query, chunks, top_n)

    # Siapkan prompt evaluasi relevansi
    candidates_text = ""
    for idx, c in enumerate(chunks):
        # Ambil cuplikan awal teks chunk agar hemat token
        snippet = c.text[:300].replace("\n", " ")
        candidates_text += f"[{idx}] {snippet}\n\n"

    system_instruction = (
        "Anda adalah sistem reranking paper ilmiah berkecepatan tinggi. "
        "Tugas Anda: menilai daftar kandidat dokumen berdasarkan relevansi langsung terhadap pertanyaan pengguna. "
        "Kembalikan HANYA array JSON berisi indeks integer dokumen terbaik yang diurutkan dari yang paling relevan, "
        f"maksimal {top_n} item. Contoh format: [2, 0, 4]"
    )

    prompt = f"Pertanyaan: \"{query}\"\n\nKandidat Dokumen:\n{candidates_text}\n\nArray JSON indeks terurut:"

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "systemInstruction": {"parts": [{"text": system_instruction}]},
        "generationConfig": {
            "temperature": 0.0,
            "responseMimeType": "application/json",
        },
    }

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(
                f"{GEMINI_GENERATE_URL}?key={api_key}",
                json=payload,
                headers={"Content-Type": "application/json"},
            )
            resp.raise_for_status()
            data = resp.json()

            # Parse array JSON dari hasil generasi
            candidates = data.get("candidates", [])
            if candidates and "content" in candidates[0]:
                raw_text = candidates[0]["content"]["parts"][0]["text"].strip()
                ranked_indices = json.loads(raw_text)

                if isinstance(ranked_indices, list):
                    reranked: list[RetrievedChunk] = []
                    seen_indices = set()

                    for idx in ranked_indices:
                        if (
                            isinstance(idx, int)
                            and 0 <= idx < len(chunks)
                            and idx not in seen_indices
                        ):
                            reranked.append(chunks[idx])
                            seen_indices.add(idx)

                    # Jika ada slot yang tersisa dari top_n, lengkapi dengan urutan semula
                    for idx, c in enumerate(chunks):
                        if len(reranked) >= top_n:
                            break
                        if idx not in seen_indices:
                            reranked.append(c)
                            seen_indices.add(idx)

                    return reranked[:top_n]

    except (httpx.HTTPError, json.JSONDecodeError, KeyError, IndexError, ValueError) as exc:
        logger.warning(
            f"[Reranker] Gagal memanggil LLM reranker: {exc!s}. Menggunakan fallback reranking."
        )

    return _fallback_rerank(query, chunks, top_n)
