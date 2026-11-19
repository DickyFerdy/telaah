"""
Unit test untuk Rate Limiter (backend/app/core/rate_limit.py).
Menguji:
1. Logika sliding window limiter internal.
2. Respons HTTP 429 saat batas kueri terlampaui.
3. Header X-RateLimit dan Retry-After.
4. Isolasi batas per pengguna/kunci.
"""

import uuid

import pytest
from app.core.config import settings
from app.core.rate_limit import SlidingWindowRateLimiter, limiter
from app.core.security import create_access_token
from app.db.models import Paper, User
from app.db.session import async_session_maker
from httpx import AsyncClient


@pytest.fixture(autouse=True)
async def reset_limiter_state():
    """Selalu reset state rate limiter sebelum dan sesudah setiap test."""
    await limiter.reset()
    original_enabled = settings.rate_limit_enabled
    settings.rate_limit_enabled = True
    yield
    await limiter.reset()
    settings.rate_limit_enabled = original_enabled


@pytest.mark.asyncio
async def test_sliding_window_limiter_logic():
    sw = SlidingWindowRateLimiter()

    # Batas: 3 kueri per 2 detik
    allowed, rem, retry = await sw.check("test-user", max_requests=3, window_seconds=2)
    assert allowed is True
    assert rem == 2
    assert retry == 0

    allowed, rem, retry = await sw.check("test-user", max_requests=3, window_seconds=2)
    assert allowed is True
    assert rem == 1

    allowed, rem, retry = await sw.check("test-user", max_requests=3, window_seconds=2)
    assert allowed is True
    assert rem == 0

    # Kueri ke-4 harus ditolak
    allowed, rem, retry = await sw.check("test-user", max_requests=3, window_seconds=2)
    assert allowed is False
    assert rem == 0
    assert retry >= 1

    # Kunci pengguna lain tidak terpengaruh
    allowed_other, _, _ = await sw.check("other-user", max_requests=3, window_seconds=2)
    assert allowed_other is True


@pytest.mark.asyncio
async def test_chat_endpoint_rate_limit(client: AsyncClient):
    # Buat user dan paper uji
    user_id = uuid.uuid4()
    paper_id = uuid.uuid4()
    token = create_access_token({"sub": str(user_id)})
    headers = {"Authorization": f"Bearer {token}"}

    async with async_session_maker() as db:
        user = User(id=user_id, email=f"ratelimit_{user_id}@example.com", password_hash="dummy")
        paper = Paper(
            id=paper_id,
            user_id=user_id,
            title="Rate Limit Test Paper",
            file_path="dummy.pdf",
            status="ready",
        )
        db.add(user)
        db.add(paper)
        await db.commit()

    # Konfigurasi batas ketat untuk pengetesan: 2 kueri chat per window
    orig_chat_max = settings.rate_limit_chat_max
    settings.rate_limit_chat_max = 2
    settings.rate_limit_chat_window_seconds = 60

    try:
        # Request 1: Sukses 200
        res1 = await client.post(
            f"/papers/{paper_id}/chat",
            json={"message": "Halo test 1"},
            headers=headers,
        )
        assert res1.status_code == 200
        assert res1.headers.get("X-RateLimit-Limit") == "2"
        assert res1.headers.get("X-RateLimit-Remaining") == "1"

        # Request 2: Sukses 200
        res2 = await client.post(
            f"/papers/{paper_id}/chat",
            json={"message": "Halo test 2"},
            headers=headers,
        )
        assert res2.status_code == 200
        assert res2.headers.get("X-RateLimit-Remaining") == "0"

        # Request 3: Ditolak 429 Too Many Requests
        res3 = await client.post(
            f"/papers/{paper_id}/chat",
            json={"message": "Halo test 3"},
            headers=headers,
        )
        assert res3.status_code == 429
        assert "Retry-After" in res3.headers
        assert "Terlalu banyak permintaan" in res3.json()["detail"]

    finally:
        settings.rate_limit_chat_max = orig_chat_max


@pytest.mark.asyncio
async def test_upload_endpoint_rate_limit(client: AsyncClient):
    user_id = uuid.uuid4()
    token = create_access_token({"sub": str(user_id)})
    headers = {"Authorization": f"Bearer {token}"}

    async with async_session_maker() as db:
        user = User(id=user_id, email=f"upload_limit_{user_id}@example.com", password_hash="dummy")
        db.add(user)
        await db.commit()

    orig_upload_max = settings.rate_limit_upload_max
    settings.rate_limit_upload_max = 2
    settings.rate_limit_upload_window_seconds = 60

    try:
        dummy_pdf = b"%PDF-1.4 dummy valid pdf content"
        files = {"file": ("test1.pdf", dummy_pdf, "application/pdf")}

        # Upload 1: 201 Created
        r1 = await client.post("/papers", files=files, headers=headers)
        assert r1.status_code == 201
        assert r1.headers.get("X-RateLimit-Limit") == "2"
        assert r1.headers.get("X-RateLimit-Remaining") == "1"

        # Upload 2: 201 Created
        files2 = {"file": ("test2.pdf", dummy_pdf, "application/pdf")}
        r2 = await client.post("/papers", files=files2, headers=headers)
        assert r2.status_code == 201
        assert r2.headers.get("X-RateLimit-Remaining") == "0"

        # Upload 3: 429 Too Many Requests
        files3 = {"file": ("test3.pdf", dummy_pdf, "application/pdf")}
        r3 = await client.post("/papers", files=files3, headers=headers)
        assert r3.status_code == 429
        assert "Retry-After" in r3.headers
        assert "Terlalu banyak permintaan mengunggah paper" in r3.json()["detail"]

    finally:
        settings.rate_limit_upload_max = orig_upload_max
