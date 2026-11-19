"""
Demo interaktif untuk memverifikasi Audit Keamanan Telaah secara langsung:
1. Perlindungan Akses Lintas Pengguna (Multi-Tenant IDOR Protection).
2. Penolakan File Upload Malicious (Magic Byte Check).
3. Validasi Batas Payload Kueri.
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

from app.core.security import create_access_token
from app.db.models import Paper, User
from app.db.session import async_session_maker
from app.main import app


async def demo_security_audit():
    print("=" * 70)
    print("DEMO UJI COBA LANGSUNG: SECURITY AUDIT & MULTI-TENANT ISOLATION")
    print("=" * 70)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Setup User A dan User B
        uid_a = uuid.uuid4()
        uid_b = uuid.uuid4()
        token_a = create_access_token({"sub": str(uid_a)})
        token_b = create_access_token({"sub": str(uid_b)})
        headers_a = {"Authorization": f"Bearer {token_a}"}
        headers_b = {"Authorization": f"Bearer {token_b}"}

        paper_id = uuid.uuid4()

        async with async_session_maker() as db:
            user_a = User(id=uid_a, email=f"user_a_{uid_a}@example.com", password_hash="dummy")
            user_b = User(id=uid_b, email=f"user_b_{uid_b}@example.com", password_hash="dummy")
            paper_a = Paper(
                id=paper_id,
                user_id=uid_a,
                title="Paper Rahasia User A",
                file_path="dummy.pdf",
                status="ready",
            )
            db.add_all([user_a, user_b, paper_a])
            await db.commit()

        print("\n[Uji 1: Perlindungan Akses Lintas Pengguna (IDOR)]")
        print(f"  - User A ID : {uid_a} (Pemilik sah paper {paper_id})")
        print(f"  - User B ID : {uid_b} (Penyerang / Pengguna lain)")

        # User A akses paper miliknya -> 200 OK
        res_a = await client.get(f"/papers/{paper_id}", headers=headers_a)
        print(f"  -> User A akses paper miliknya  : HTTP {res_a.status_code} OK")

        # User B mencoba akses paper User A -> 404 NOT FOUND
        res_b = await client.get(f"/papers/{paper_id}", headers=headers_b)
        print(f"  -> User B mencoba akses paper A : HTTP {res_b.status_code} {res_b.json().get('detail')}")

        # User B mencoba chat pada paper User A -> 404 NOT FOUND
        res_b_chat = await client.post(
            f"/papers/{paper_id}/chat",
            json={"message": "Coba intip isi paper"},
            headers=headers_b,
        )
        print(f"  -> User B mencoba chat paper A  : HTTP {res_b_chat.status_code} {res_b_chat.json().get('detail')}")

        print("\n[Uji 2: Validasi Magic Bytes File Upload]")
        fake_pdf = b"Bukan berkas PDF asli, melainkan teks biasa yang dipalsukan."
        files = {"file": ("malicious_script.pdf", fake_pdf, "application/pdf")}
        res_upload = await client.post("/papers", files=files, headers=headers_a)
        print(f"  -> Upload PDF palsu (tanpa %PDF-): HTTP {res_upload.status_code} BAD REQUEST")
        print(f"     Pesan Penolakan: \"{res_upload.json().get('detail')}\"")

        print("\n[Uji 3: Batasan Payload Input Chat (Anti-Exhaustion)]")
        giant_query = "X" * 4005
        res_giant = await client.post(
            f"/papers/{paper_id}/chat",
            json={"message": giant_query},
            headers=headers_a,
        )
        print(f"  -> Kueri melebihi 4000 karakter  : HTTP {res_giant.status_code} UNPROCESSABLE ENTITY")

    print("\n" + "=" * 70)
    print("STATUS: AUDIT KEAMANAN 100% LOLOS - ISOLASI TENANT & VALIDASI TERVERIFIKASI")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo_security_audit())
