import uuid

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_user_success(client: AsyncClient) -> None:
    unique_email = f"user_{uuid.uuid4().hex[:8]}@example.com"
    response = await client.post(
        "/auth/register",
        json={"email": unique_email, "password": "securepassword123"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == unique_email
    assert "id" in data
    assert "created_at" in data


@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient) -> None:
    unique_email = f"user_{uuid.uuid4().hex[:8]}@example.com"
    first_res = await client.post(
        "/auth/register",
        json={"email": unique_email, "password": "securepassword123"},
    )
    assert first_res.status_code == 201

    second_res = await client.post(
        "/auth/register",
        json={"email": unique_email, "password": "anotherpassword123"},
    )
    assert second_res.status_code == 400
    assert second_res.json()["detail"] == "Email already registered"


@pytest.mark.asyncio
async def test_register_invalid_password(client: AsyncClient) -> None:
    unique_email = f"user_{uuid.uuid4().hex[:8]}@example.com"
    response = await client.post(
        "/auth/register",
        json={"email": unique_email, "password": "short"},  # < 8 chars
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient) -> None:
    unique_email = f"user_{uuid.uuid4().hex[:8]}@example.com"
    password = "mypassword123"
    reg_res = await client.post(
        "/auth/register",
        json={"email": unique_email, "password": password},
    )
    assert reg_res.status_code == 201

    login_res = await client.post(
        "/auth/login",
        json={"email": unique_email, "password": password},
    )
    assert login_res.status_code == 200
    data = login_res.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient) -> None:
    unique_email = f"user_{uuid.uuid4().hex[:8]}@example.com"
    await client.post(
        "/auth/register",
        json={"email": unique_email, "password": "correctpassword123"},
    )

    login_res = await client.post(
        "/auth/login",
        json={"email": unique_email, "password": "wrongpassword999"},
    )
    assert login_res.status_code == 401
    assert login_res.json()["detail"] == "Invalid email or password"


@pytest.mark.asyncio
async def test_login_nonexistent_user(client: AsyncClient) -> None:
    login_res = await client.post(
        "/auth/login",
        json={
            "email": "nonexistent_404@example.com",
            "password": "password123",
        },
    )
    assert login_res.status_code == 401
    assert login_res.json()["detail"] == "Invalid email or password"


@pytest.mark.asyncio
async def test_get_me_success(client: AsyncClient) -> None:
    unique_email = f"user_{uuid.uuid4().hex[:8]}@example.com"
    password = "secretpassword123"
    await client.post(
        "/auth/register",
        json={"email": unique_email, "password": password},
    )

    login_res = await client.post(
        "/auth/login",
        json={"email": unique_email, "password": password},
    )
    token = login_res.json()["access_token"]

    me_res = await client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert me_res.status_code == 200
    data = me_res.json()
    assert data["email"] == unique_email
    assert "id" in data


@pytest.mark.asyncio
async def test_get_me_unauthorized(client: AsyncClient) -> None:
    no_token_res = await client.get("/auth/me")
    assert no_token_res.status_code == 401

    invalid_token_res = await client.get(
        "/auth/me",
        headers={"Authorization": "Bearer invalid.fake.token"},
    )
    assert invalid_token_res.status_code == 401
