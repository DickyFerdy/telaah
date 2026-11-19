import io
import uuid
from unittest.mock import AsyncMock

import pytest
from app.core.config import settings
from app.llm.not_found import (
    NOT_FOUND_DEFAULT_MESSAGE,
    is_not_found_response,
)
from httpx import AsyncClient


def test_is_not_found_response_true_cases() -> None:
    cases = [
        "Informasi tersebut tidak ditemukan di dalam paper ini.",
        "Maaf, topik ini tidak dibahas dalam dokumen ini.",
        "Hal tersebut tidak disebutkan di paper.",
        "Paper ini tidak memuat informasi mengenai hal tersebut.",
        "Informasi tersebut tidak ada dalam teks yang diberikan.",
        "This information is not found in the paper.",
        "It is not mentioned in the document.",
        "The paper does not contain any details on optimizer settings.",
        "No information found in the paper regarding this topic.",
    ]
    for text in cases:
        assert is_not_found_response(text) is True, f"Failed on: {text}"


def test_is_not_found_response_false_cases() -> None:
    cases = [
        "Paper ini menggunakan arsitektur transformer [1] dengan 12 layer.",
        "Penulis mengevaluasi model pada dataset GLUE dan SQuAD [2].",
        "Hasil eksperimen menunjukkan peningkatan performa sebesar 14% [3].",
        "",
        "   ",
    ]
    for text in cases:
        assert is_not_found_response(text) is False, f"Failed on: {text}"


async def get_auth_token(client: AsyncClient) -> str:
    email = f"notfound_tester_{uuid.uuid4().hex[:8]}@example.com"
    pwd = "password123"
    await client.post("/auth/register", json={"email": email, "password": pwd})
    res = await client.post("/auth/login", json={"email": email, "password": pwd})
    return res.json()["access_token"]


@pytest.mark.asyncio
async def test_chat_not_found_empty_retrieval(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "gemini_api_key", "")
    token = await get_auth_token(client)

    # 1. Upload sample PDF
    pdf_content = b"%PDF-1.4 sample content for not found test"
    upload_res = await client.post(
        "/papers",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("not_found_doc.pdf", io.BytesIO(pdf_content), "application/pdf")},
    )
    assert upload_res.status_code == 201
    paper_id = upload_res.json()["id"]

    # 2. Mock search_hybrid agar mengembalikan list kosong (0 chunk relevan)
    monkeypatch.setattr(
        "app.api.chat.search_hybrid",
        AsyncMock(return_value=[]),
    )

    # 3. Request ke chat SSE
    chat_res = await client.post(
        f"/papers/{paper_id}/chat",
        headers={"Authorization": f"Bearer {token}"},
        json={"message": "Berapa resep nasi goreng menurut paper ini?"},
    )
    assert chat_res.status_code == 200
    body_text = chat_res.text

    assert "event: delta" in body_text
    assert NOT_FOUND_DEFAULT_MESSAGE in body_text
    assert '"not_found": true' in body_text
