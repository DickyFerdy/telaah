import io
import uuid

import pytest
from app.core.config import settings
from httpx import AsyncClient


async def get_auth_token(client: AsyncClient) -> str:
    email = f"chat_tester_{uuid.uuid4().hex[:8]}@example.com"
    pwd = "password123"
    await client.post("/auth/register", json={"email": email, "password": pwd})
    res = await client.post("/auth/login", json={"email": email, "password": pwd})
    return res.json()["access_token"]


@pytest.mark.asyncio
async def test_chat_nonexistent_paper(client: AsyncClient) -> None:
    token = await get_auth_token(client)
    random_id = uuid.uuid4()

    res = await client.post(
        f"/papers/{random_id}/chat",
        headers={"Authorization": f"Bearer {token}"},
        json={"message": "Apa kesimpulan paper ini?"},
    )
    assert res.status_code == 404
    assert res.json()["detail"] == "Paper tidak ditemukan"


@pytest.mark.asyncio
async def test_chat_streaming_success(client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    # Set offline fallback key untuk pengujian
    monkeypatch.setattr(settings, "gemini_api_key", "")

    token = await get_auth_token(client)

    # 1. Upload sample PDF
    pdf_content = b"%PDF-1.4 sample content for chat test"
    upload_res = await client.post(
        "/papers",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("chat_doc.pdf", io.BytesIO(pdf_content), "application/pdf")},
    )
    assert upload_res.status_code == 201
    paper_id = upload_res.json()["id"]

    # 2. Kirim pesan ke endpoint SSE
    chat_res = await client.post(
        f"/papers/{paper_id}/chat",
        headers={"Authorization": f"Bearer {token}"},
        json={"message": "Bagaimana arsitektur RAG pada paper ini?"},
    )

    assert chat_res.status_code == 200
    assert "text/event-stream" in chat_res.headers["content-type"]

    body_text = chat_res.text
    # Pastikan terdapat event context, delta, dan done dengan citations
    assert "event: context" in body_text
    assert "event: delta" in body_text
    assert "event: done" in body_text
    assert "citations" in body_text
