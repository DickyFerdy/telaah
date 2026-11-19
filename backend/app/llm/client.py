import asyncio
import json
import logging
from collections.abc import AsyncGenerator

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

GEMINI_CHAT_MODEL = "gemini-1.5-flash"
GEMINI_STREAM_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_CHAT_MODEL}:streamGenerateContent"


async def stream_generate_answer(
    prompt: str,
    system_instruction: str,
    timeout: float = 30.0,
) -> AsyncGenerator[str, None]:
    """
    Menghasilkan streaming token jawaban dari Gemini API menggunakan Server-Sent Events.
    Jika GEMINI_API_KEY tidak disetel (mode testing/offline), menghasilkan streaming sintetis.
    """
    api_key = settings.gemini_api_key.strip()

    # Fallback mode pengujian offline
    if not api_key:
        logger.warning(
            "GEMINI_API_KEY tidak disetel. Menggunakan streaming jawaban sintetis."
        )
        sample_response = (
            "Berdasarkan paper yang diunggah, metode yang digunakan menggabungkan "
            "ekstraksi teks presisi [1] dengan pencarian semantik hybrid [2]. "
            "Hasil pengujian menunjukkan akurasi yang konsisten pada data evaluasi [1]."
        )
        for word in sample_response.split(" "):
            await asyncio.sleep(0.04)
            yield word + " "
        return

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "systemInstruction": {"parts": [{"text": system_instruction}]},
        "generationConfig": {
            "temperature": 0.2,
            "maxOutputTokens": 1024,
        },
    }

    url = f"{GEMINI_STREAM_URL}?alt=sse&key={api_key}"

    async with httpx.AsyncClient(timeout=timeout) as client, client.stream(
        "POST",
        url,
        json=payload,
        headers={"Content-Type": "application/json"},
    ) as response:
        response.raise_for_status()

        async for line in response.aiter_lines():
            line = line.strip()
            if not line or not line.startswith("data: "):
                continue

            data_str = line[len("data: ") :].strip()
            if data_str == "[DONE]":
                break

            try:
                data = json.loads(data_str)
                candidates = data.get("candidates", [])
                if candidates and "content" in candidates[0]:
                    parts = candidates[0]["content"].get("parts", [])
                    for part in parts:
                        text_piece = part.get("text", "")
                        if text_piece:
                            yield text_piece
            except json.JSONDecodeError:
                continue
