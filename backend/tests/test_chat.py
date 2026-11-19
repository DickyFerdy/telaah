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


@pytest.mark.asyncio
async def test_conversation_history_lifecycle(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "gemini_api_key", "")
    token = await get_auth_token(client)

    # 1. Upload sample PDF
    pdf_content = b"%PDF-1.4 history test"
    upload_res = await client.post(
        "/papers",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("history_doc.pdf", io.BytesIO(pdf_content), "application/pdf")},
    )
    paper_id = upload_res.json()["id"]

    # 2. Cek list percakapan awal (kosong)
    list_res1 = await client.get(
        f"/papers/{paper_id}/chat/conversations",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert list_res1.status_code == 200
    assert list_res1.json() == []

    # 3. Kirim pesan chat pertama
    await client.post(
        f"/papers/{paper_id}/chat",
        headers={"Authorization": f"Bearer {token}"},
        json={"message": "Apa fokus utama paper ini?"},
    )

    # 4. Cek list percakapan setelah chat
    list_res2 = await client.get(
        f"/papers/{paper_id}/chat/conversations",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert list_res2.status_code == 200
    conversations = list_res2.json()
    assert len(conversations) == 1
    conv = conversations[0]
    conv_id = conv["id"]
    assert conv["message_count"] == 2
    assert "Apa fokus utama" in (conv["preview"] or "")

    # 5. Ambil detail seluruh pesan dalam percakapan
    messages_res = await client.get(
        f"/papers/{paper_id}/chat/conversations/{conv_id}/messages",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert messages_res.status_code == 200
    msgs = messages_res.json()
    assert len(msgs) == 2
    assert msgs[0]["role"] == "user"
    assert msgs[0]["content"] == "Apa fokus utama paper ini?"
    assert msgs[1]["role"] == "assistant"

    # 6. Test isolasi pengguna lain
    other_token = await get_auth_token(client)
    forbidden_get = await client.get(
        f"/papers/{paper_id}/chat/conversations/{conv_id}/messages",
        headers={"Authorization": f"Bearer {other_token}"},
    )
    assert forbidden_get.status_code == 404

    # 7. Hapus percakapan
    del_res = await client.delete(
        f"/papers/{paper_id}/chat/conversations/{conv_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert del_res.status_code == 204

    # 8. Pastikan percakapan sudah terhapus
    list_res3 = await client.get(
        f"/papers/{paper_id}/chat/conversations",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert list_res3.json() == []

