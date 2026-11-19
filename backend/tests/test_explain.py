import uuid

import pytest
from app.core.security import create_access_token, hash_password
from app.db.models import Paper, User
from app.db.session import async_session_maker
from httpx import AsyncClient


@pytest.fixture
async def explain_test_setup():
    async with async_session_maker() as db_session:
        user_a = User(
            id=uuid.uuid4(),
            email=f"expl_user_{uuid.uuid4().hex[:6]}@example.com",
            password_hash=hash_password("password123"),
        )
        user_b = User(
            id=uuid.uuid4(),
            email=f"expl_stranger_{uuid.uuid4().hex[:6]}@example.com",
            password_hash=hash_password("password123"),
        )
        db_session.add_all([user_a, user_b])
        await db_session.commit()

        token_a = create_access_token(data={"sub": str(user_a.id)})
        token_b = create_access_token(data={"sub": str(user_b.id)})

        headers_a = {"Authorization": f"Bearer {token_a}"}
        headers_b = {"Authorization": f"Bearer {token_b}"}

        paper = Paper(
            id=uuid.uuid4(),
            user_id=user_a.id,
            title="Attention Is All You Need",
            source_type="arxiv",
            source_ref="1706.03762",
            file_path="/mock/paper.pdf",
            status="ready",
        )
        db_session.add(paper)
        await db_session.commit()

    return {
        "user_a": user_a,
        "user_b": user_b,
        "headers_a": headers_a,
        "headers_b": headers_b,
        "paper": paper,
    }


@pytest.mark.asyncio
async def test_explain_term_success(
    client: AsyncClient, explain_test_setup: dict
):
    paper = explain_test_setup["paper"]
    headers_a = explain_test_setup["headers_a"]

    res = await client.post(
        f"/papers/{paper.id}/explain-term",
        headers=headers_a,
        json={
            "term": "Scaled Dot-Product Attention",
            "context": "We compute the attention function on a set of queries simultaneously.",
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["term"] == "Scaled Dot-Product Attention"
    assert "explanation" in data
    assert len(data["explanation"]) > 10
    assert (
        data["context"]
        == "We compute the attention function on a set of queries simultaneously."
    )


@pytest.mark.asyncio
async def test_explain_term_empty(
    client: AsyncClient, explain_test_setup: dict
):
    paper = explain_test_setup["paper"]
    headers_a = explain_test_setup["headers_a"]

    res = await client.post(
        f"/papers/{paper.id}/explain-term",
        headers=headers_a,
        json={"term": "   "},
    )
    assert res.status_code == 400
    assert "tidak boleh kosong" in res.json()["detail"]


@pytest.mark.asyncio
async def test_explain_term_paper_not_found(
    client: AsyncClient, explain_test_setup: dict
):
    headers_a = explain_test_setup["headers_a"]
    random_id = uuid.uuid4()

    res = await client.post(
        f"/papers/{random_id}/explain-term",
        headers=headers_a,
        json={"term": "Transformer"},
    )
    assert res.status_code == 404
    assert "Paper tidak ditemukan" in res.json()["detail"]


@pytest.mark.asyncio
async def test_explain_term_user_isolation(
    client: AsyncClient, explain_test_setup: dict
):
    paper = explain_test_setup["paper"]
    headers_b = explain_test_setup["headers_b"]  # Different user

    res = await client.post(
        f"/papers/{paper.id}/explain-term",
        headers=headers_b,
        json={"term": "Multi-Head Attention"},
    )
    assert res.status_code == 404
