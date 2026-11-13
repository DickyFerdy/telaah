import io
import os
import uuid

import pytest
from httpx import AsyncClient


async def get_authenticated_token(client: AsyncClient) -> str:
    unique_email = f"paper_user_{uuid.uuid4().hex[:8]}@example.com"
    password = "securepassword123"
    await client.post(
        "/auth/register",
        json={"email": unique_email, "password": password},
    )
    login_res = await client.post(
        "/auth/login",
        json={"email": unique_email, "password": password},
    )
    return login_res.json()["access_token"]


@pytest.mark.asyncio
async def test_upload_pdf_success(client: AsyncClient) -> None:
    token = await get_authenticated_token(client)
    pdf_content = b"%PDF-1.4\n1 0 obj\n<<\n>>\nendobj\ntrailer\n<<\n>>\n%%EOF"

    response = await client.post(
        "/papers",
        headers={"Authorization": f"Bearer {token}"},
        files={
            "file": ("test_paper.pdf", io.BytesIO(pdf_content), "application/pdf")
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["status"] == "uploaded"
    assert data["source_type"] == "upload"
    assert data["source_ref"] == "test_paper.pdf"
    assert os.path.exists(data["file_path"])

    # Clean up created file
    if os.path.exists(data["file_path"]):
        os.remove(data["file_path"])


@pytest.mark.asyncio
async def test_upload_unauthorized(client: AsyncClient) -> None:
    pdf_content = b"%PDF-1.4 sample content"
    response = await client.post(
        "/papers",
        files={
            "file": ("test_paper.pdf", io.BytesIO(pdf_content), "application/pdf")
        },
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_upload_invalid_extension(client: AsyncClient) -> None:
    token = await get_authenticated_token(client)
    content = b"%PDF-1.4 valid magic bytes but wrong ext"
    response = await client.post(
        "/papers",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("test.docx", io.BytesIO(content), "application/pdf")},
    )
    assert response.status_code == 400
    assert "ekstensi .pdf" in response.json()["detail"]


@pytest.mark.asyncio
async def test_upload_invalid_mime_type(client: AsyncClient) -> None:
    token = await get_authenticated_token(client)
    content = b"%PDF-1.4 valid magic bytes"
    response = await client.post(
        "/papers",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("test.pdf", io.BytesIO(content), "text/plain")},
    )
    assert response.status_code == 400
    assert "application/pdf" in response.json()["detail"]


@pytest.mark.asyncio
async def test_upload_invalid_magic_bytes(client: AsyncClient) -> None:
    token = await get_authenticated_token(client)
    content = b"THIS IS NOT A VALID PDF SIGNATURE"
    response = await client.post(
        "/papers",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("fake.pdf", io.BytesIO(content), "application/pdf")},
    )
    assert response.status_code == 400
    assert "magic bytes" in response.json()["detail"]


@pytest.mark.asyncio
async def test_upload_empty_file(client: AsyncClient) -> None:
    token = await get_authenticated_token(client)
    response = await client.post(
        "/papers",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("empty.pdf", io.BytesIO(b""), "application/pdf")},
    )
    assert response.status_code == 400
    assert "kosong" in response.json()["detail"]


@pytest.mark.asyncio
async def test_upload_file_exceeds_max_size(client: AsyncClient) -> None:
    token = await get_authenticated_token(client)
    # Create content slightly over 20 MB
    large_size = 20 * 1024 * 1024 + 1024  # 20 MB + 1 KB
    large_content = b"%PDF-" + b"0" * (large_size - 5)

    response = await client.post(
        "/papers",
        headers={"Authorization": f"Bearer {token}"},
        files={
            "file": (
                "huge_paper.pdf",
                io.BytesIO(large_content),
                "application/pdf",
            )
        },
    )
    assert response.status_code == 413
    assert "melebihi batas maksimal" in response.json()["detail"]

