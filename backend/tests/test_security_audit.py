"""
Security Audit Test Suite (backend/tests/test_security_audit.py).
Menguji:
1. Akses Lintas Pengguna (Multi-tenant isolation & IDOR prevention).
2. Validasi File Upload (Magic bytes, MIME, size, extension).
3. Validasi Batas Input Payload (Anti-exhaustion).
4. Otentikasi dan Integritas Token JWT.
"""

import uuid
from pathlib import Path

import pytest
from app.core.security import create_access_token
from app.db.models import Paper, User
from app.db.session import async_session_maker
from httpx import AsyncClient


@pytest.fixture
async def user_a():
    uid = uuid.uuid4()
    async with async_session_maker() as db:
        user = User(id=uid, email=f"usera_{uid}@example.com", password_hash="dummy")
        db.add(user)
        await db.commit()
    token = create_access_token({"sub": str(uid)})
    return {"id": uid, "token": token, "headers": {"Authorization": f"Bearer {token}"}}


@pytest.fixture
async def user_b():
    uid = uuid.uuid4()
    async with async_session_maker() as db:
        user = User(id=uid, email=f"userb_{uid}@example.com", password_hash="dummy")
        db.add(user)
        await db.commit()
    token = create_access_token({"sub": str(uid)})
    return {"id": uid, "token": token, "headers": {"Authorization": f"Bearer {token}"}}


@pytest.fixture
async def paper_a(user_a, tmp_path: Path):
    paper_id = uuid.uuid4()
    pdf_file = tmp_path / f"{paper_id}.pdf"
    pdf_file.write_bytes(b"%PDF-1.4 dummy valid content")

    async with async_session_maker() as db:
        p = Paper(
            id=paper_id,
            user_id=user_a["id"],
            title="Paper Milik User A",
            file_path=str(pdf_file),
            status="ready",
        )
        db.add(p)
        await db.commit()
    return {"id": paper_id, "path": pdf_file}


# ==============================================================================
# 1. UJI ISOLASI AKSES LINTAS PENGGUNA (MULTI-TENANT / IDOR PROTECTION)
# ==============================================================================


@pytest.mark.asyncio
async def test_cross_tenant_read_paper(client: AsyncClient, user_a, user_b, paper_a):
    """User B tidak boleh dapat membaca metadata paper milik User A."""
    # User A bisa baca
    res_a = await client.get(f"/papers/{paper_a['id']}", headers=user_a["headers"])
    assert res_a.status_code == 200

    # User B ditolak (404 Not Found)
    res_b = await client.get(f"/papers/{paper_a['id']}", headers=user_b["headers"])
    assert res_b.status_code == 404
    assert res_b.json()["detail"] == "Paper tidak ditemukan"


@pytest.mark.asyncio
async def test_cross_tenant_download_pdf(client: AsyncClient, user_a, user_b, paper_a):
    """User B tidak boleh dapat mengunduh berkas PDF milik User A."""
    # User A bisa download
    res_a = await client.get(f"/papers/{paper_a['id']}/pdf", headers=user_a["headers"])
    assert res_a.status_code == 200

    # User B ditolak
    res_b = await client.get(f"/papers/{paper_a['id']}/pdf", headers=user_b["headers"])
    assert res_b.status_code == 404


@pytest.mark.asyncio
async def test_cross_tenant_delete_paper(client: AsyncClient, user_a, user_b, paper_a):
    """User B tidak boleh dapat menghapus paper milik User A."""
    # User B mencoba hapus -> ditolak 404
    res_b = await client.delete(f"/papers/{paper_a['id']}", headers=user_b["headers"])
    assert res_b.status_code == 404

    # Paper A masih harus tetap ada di database
    res_a = await client.get(f"/papers/{paper_a['id']}", headers=user_a["headers"])
    assert res_a.status_code == 200


@pytest.mark.asyncio
async def test_cross_tenant_chat(client: AsyncClient, user_a, user_b, paper_a):
    """User B tidak boleh dapat mengirim pesan chat pada paper milik User A."""
    res_b = await client.post(
        f"/papers/{paper_a['id']}/chat",
        json={"message": "Pertanyaan terlarang dari User B"},
        headers=user_b["headers"],
    )
    assert res_b.status_code == 404


@pytest.mark.asyncio
async def test_cross_tenant_summary_and_explain(client: AsyncClient, user_b, paper_a):
    """User B tidak boleh dapat meminta ringkasan atau penjelasan istilah pada paper User A."""
    res_sum = await client.get(f"/papers/{paper_a['id']}/summary", headers=user_b["headers"])
    assert res_sum.status_code == 404

    res_exp = await client.post(
        f"/papers/{paper_a['id']}/explain-term",
        json={"term": "Transformer"},
        headers=user_b["headers"],
    )
    assert res_exp.status_code == 404


# ==============================================================================
# 2. UJI VALIDASI KEAMANAN FILE UPLOAD
# ==============================================================================


@pytest.mark.asyncio
async def test_upload_rejection_fake_magic_bytes(client: AsyncClient, user_a):
    """Upload berkas ber-ekstensi .pdf tetapi tidak memuat magic bytes %PDF- harus ditolak."""
    fake_pdf = b"Ini adalah teks biasa yang diubah namanya menjadi paper.pdf"
    files = {"file": ("malicious.pdf", fake_pdf, "application/pdf")}

    res = await client.post("/papers", files=files, headers=user_a["headers"])
    assert res.status_code == 400
    assert "magic bytes" in res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_upload_rejection_wrong_extension(client: AsyncClient, user_a):
    """Upload file ber-ekstensi non-pdf (.exe) harus ditolak."""
    files = {"file": ("malicious.exe", b"%PDF-1.4 dummy", "application/pdf")}
    res = await client.post("/papers", files=files, headers=user_a["headers"])
    assert res.status_code == 400
    assert "ekstensi .pdf" in res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_upload_rejection_empty_file(client: AsyncClient, user_a):
    """Upload berkas kosong 0 bytes harus ditolak."""
    files = {"file": ("empty.pdf", b"", "application/pdf")}
    res = await client.post("/papers", files=files, headers=user_a["headers"])
    assert res.status_code == 400
    assert "kosong" in res.json()["detail"].lower()


# ==============================================================================
# 3. UJI VALIDASI INPUT & BATASAN PAYLOAD
# ==============================================================================


@pytest.mark.asyncio
async def test_chat_payload_length_limits(client: AsyncClient, user_a, paper_a):
    """Kueri chat kosong atau melebihi 4000 karakter harus ditolak (422 Unprocessable Entity)."""
    # Kueri kosong
    res_empty = await client.post(
        f"/papers/{paper_a['id']}/chat",
        json={"message": ""},
        headers=user_a["headers"],
    )
    assert res_empty.status_code == 422

    # Kueri raksasa (> 4000 karakter)
    giant_msg = "A" * 4005
    res_giant = await client.post(
        f"/papers/{paper_a['id']}/chat",
        json={"message": giant_msg},
        headers=user_a["headers"],
    )
    assert res_giant.status_code == 422


@pytest.mark.asyncio
async def test_auth_token_security(client: AsyncClient, paper_a):
    """Endpoint yang dilindungi harus menolak kueri tanpa token atau dengan token cacat (401)."""
    # Tanpa token sama sekali
    res_no_token = await client.get(f"/papers/{paper_a['id']}")
    assert res_no_token.status_code == 401

    # Token cacat
    res_bad_token = await client.get(
        f"/papers/{paper_a['id']}",
        headers={"Authorization": "Bearer invalid.fake.token"},
    )
    assert res_bad_token.status_code == 401
