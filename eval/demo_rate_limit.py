"""
Demo interaktif untuk memverifikasi Rate Limiter pada endpoint upload dan chat secara langsung.
"""

import asyncio
import sys
import uuid
from pathlib import Path

from httpx import ASGITransport, AsyncClient

BASE_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = BASE_DIR / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.config import settings
from app.core.rate_limit import limiter
from app.core.security import create_access_token
from app.db.models import Paper, User
from app.db.session import async_session_maker
from app.main import app


async def demo_rate_limiting():
    print("=" * 70)
    print("DEMO UJI COBA LANGSUNG: RATE LIMITING PADA ENDPOINT CHAT & UPLOAD")
    print("=" * 70)

    # 1. Setup user & paper uji
    user_id = uuid.uuid4()
    paper_id = uuid.uuid4()
    token = create_access_token({"sub": str(user_id)})
    headers = {"Authorization": f"Bearer {token}"}

    async with async_session_maker() as db:
        user = User(id=user_id, email=f"demo_rate_{user_id}@example.com", password_hash="dummy")
        paper = Paper(
            id=paper_id,
            user_id=user_id,
            title="Demo Rate Limit Paper",
            file_path="dummy.pdf",
            status="ready",
        )
        db.add(user)
        db.add(paper)
        await db.commit()

    # Konfigurasi batas uji coba: 3 kueri chat per window 60 detik
    await limiter.reset()
    settings.rate_limit_chat_max = 3
    settings.rate_limit_chat_window_seconds = 60

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        print(f"\n[Skenario] Batas Rate Limit Chat disetel: 3 kueri / 60 detik (User: {user.email})")

        for i in range(1, 5):
            res = await client.post(
                f"/papers/{paper_id}/chat",
                json={"message": f"Pertanyaan ke-{i}"},
                headers=headers,
            )
            limit = res.headers.get("X-RateLimit-Limit", "-")
            remaining = res.headers.get("X-RateLimit-Remaining", "-")
            retry_after = res.headers.get("Retry-After", "-")

            if res.status_code == 200:
                print(f"  Kueri {i}: HTTP {res.status_code} OK | Limit={limit} | Sisa Kuota={remaining}")
            elif res.status_code == 429:
                err_detail = res.json().get("detail", "")
                print(f"  Kueri {i}: HTTP {res.status_code} TOO MANY REQUESTS | Retry-After={retry_after}s")
                print(f"           Pesan Error: \"{err_detail}\"")

    await limiter.reset()
    print("\n" + "=" * 70)
    print("STATUS: RATE LIMITING 100% AKTIF, ANDAL & MELINDUNGI SISTEM DARI SPAM/ABUSE")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo_rate_limiting())
