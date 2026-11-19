import asyncio
import json
import logging
import re
from collections.abc import AsyncGenerator
from typing import Any

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

GEMINI_CHAT_MODEL = "gemini-1.5-flash"
GEMINI_STREAM_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_CHAT_MODEL}:streamGenerateContent"
GEMINI_GENERATE_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_CHAT_MODEL}:generateContent"


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

    # Fallback mode pengujian offline / key dummy
    if not api_key or api_key.startswith("AQ.") or settings.environment == "testing":
        logger.warning(
            "GEMINI_API_KEY tidak disetel atau dummy key. Menggunakan streaming jawaban sintetis."
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


async def generate_structured_json(
    prompt: str,
    system_instruction: str,
    timeout: float = 30.0,
) -> dict[str, Any]:
    """
    Menghasilkan respons terstruktur JSON dari Gemini API menggunakan responseMimeType='application/json'.
    Jika GEMINI_API_KEY tidak disetel (mode testing/offline), mengembalikan data ringkasan terstruktur sintetis.
    """
    api_key = settings.gemini_api_key.strip()

    # Fallback mode pengujian offline / key dummy
    if not api_key or api_key.startswith("AQ.") or settings.environment == "testing":
        logger.warning(
            "GEMINI_API_KEY tidak disetel atau dummy key. Menggunakan JSON ringkasan terstruktur sintetis."
        )
        return {
            "tldr": (
                "Paper ini mengusulkan arsitektur jaringan berbasis mekanisme attention murni "
                "tanpa menggunakan rekursi atau konvolusi."
            ),
            "research_question": (
                "Bagaimana cara membangun model sequence transduction yang efisien dan "
                "berkinerja tinggi tanpa ketergantungan pada model berulang (RNN)?"
            ),
            "method": (
                "Menggunakan arsitektur Transformer yang sepenuhnya mengandalkan Scaled Dot-Product "
                "Attention dan Multi-Head Attention dengan tumpukan encoder dan decoder."
            ),
            "dataset": (
                "Dataset WMT 2014 English-to-German (4.5 juta pasang kalimat) dan WMT 2014 "
                "English-to-French (36 juta pasang kalimat)."
            ),
            "metrics": "BLEU score dan estimasi waktu komputasi pelatihan (FLOPs).",
            "results": (
                "Transformer mencapai skor BLEU 28.4 pada penerjemahan English-to-German, melampaui "
                "model terbaik sebelumnya dengan waktu pelatihan yang jauh lebih cepat."
            ),
            "limitations": (
                "Model membutuhkan memori komputasi signifikan untuk sequence yang sangat panjang "
                "akibat kompleksitas kuadratik attention O(n^2)."
            ),
        }

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "systemInstruction": {"parts": [{"text": system_instruction}]},
        "generationConfig": {
            "temperature": 0.1,
            "responseMimeType": "application/json",
            "maxOutputTokens": 2048,
        },
    }

    url = f"{GEMINI_GENERATE_URL}?key={api_key}"

    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(
            url,
            json=payload,
            headers={"Content-Type": "application/json"},
        )
        response.raise_for_status()
        data = response.json()

        candidates = data.get("candidates", [])
        if not candidates or "content" not in candidates[0]:
            raise ValueError("Respons Gemini tidak memuat kandidat teks.")

        parts = candidates[0]["content"].get("parts", [])
        raw_text = "".join(p.get("text", "") for p in parts).strip()

        # Bersihkan format pembungkus markdown ```json ... ``` jika model menyertakannya
        cleaned_text = re.sub(
            r"^```(?:json)?\s*", "", raw_text, flags=re.IGNORECASE
        )
        cleaned_text = re.sub(r"\s*```$", "", cleaned_text).strip()

        try:
            parsed_json = json.loads(cleaned_text)
            if not isinstance(parsed_json, dict):
                raise TypeError("Format JSON hasil generasi bukan merupakan objek (dict).")
            return parsed_json
        except json.JSONDecodeError as err:
            logger.error("Gagal mendecode JSON dari Gemini: %s", raw_text)
            raise ValueError(f"Output model bukan JSON yang valid: {err}") from err

