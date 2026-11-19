import uuid

import pytest
from app.core.security import create_access_token, hash_password
from app.db.models import Chunk, Paper, User
from app.db.session import async_session_maker
from httpx import AsyncClient


@pytest.fixture
async def summary_test_setup():
    async with async_session_maker() as db_session:
        # 1. User A (Owner)
        user_a = User(
            id=uuid.uuid4(),
            email=f"user_a_{uuid.uuid4().hex[:6]}@example.com",
            password_hash=hash_password("password123"),
        )
        # 2. User B (Stranger)
        user_b = User(
            id=uuid.uuid4(),
            email=f"user_b_{uuid.uuid4().hex[:6]}@example.com",
            password_hash=hash_password("password123"),
        )
        db_session.add_all([user_a, user_b])
        await db_session.commit()

        token_a = create_access_token(data={"sub": str(user_a.id)})
        token_b = create_access_token(data={"sub": str(user_b.id)})

        headers_a = {"Authorization": f"Bearer {token_a}"}
        headers_b = {"Authorization": f"Bearer {token_b}"}

        # 3. Paper ready with chunks
        paper = Paper(
            id=uuid.uuid4(),
            user_id=user_a.id,
            title="Attention Is All You Need",
            source_type="arxiv",
            source_ref="1706.03762",
            file_path="/mock/attention.pdf",
            status="ready",
            page_count=15,
        )
        db_session.add(paper)
        await db_session.commit()

        chunk1 = Chunk(
            id=uuid.uuid4(),
            paper_id=paper.id,
            section="abstract",
            page_start=1,
            page_end=1,
            text="The dominant sequence transduction models are based on complex recurrent or convolutional neural networks. We propose the Transformer, a model architecture eschewing recurrence and entirely relying on an attention mechanism.",
        )
        chunk2 = Chunk(
            id=uuid.uuid4(),
            paper_id=paper.id,
            section="methodology",
            page_start=3,
            page_end=3,
            text="The Transformer follows an encoder-decoder structure using stacked self-attention and point-wise, fully connected layers for both the encoder and decoder.",
        )
        chunk3 = Chunk(
            id=uuid.uuid4(),
            paper_id=paper.id,
            section="experiments_results",
            page_start=7,
            page_end=8,
            text="On the WMT 2014 English-to-German translation task, the big transformer model achieves a state-of-the-art BLEU score of 28.4.",
        )
        db_session.add_all([chunk1, chunk2, chunk3])
        await db_session.commit()

    return {
        "user_a": user_a,
        "user_b": user_b,
        "headers_a": headers_a,
        "headers_b": headers_b,
        "paper": paper,
    }


@pytest.mark.asyncio
async def test_get_summary_not_found(client: AsyncClient, summary_test_setup: dict):
    paper = summary_test_setup["paper"]
    headers_a = summary_test_setup["headers_a"]

    res = await client.get(f"/papers/{paper.id}/summary", headers=headers_a)
    assert res.status_code == 404
    assert "Ringkasan belum dibuat" in res.json()["detail"]


@pytest.mark.asyncio
async def test_generate_summary_paper_not_ready(
    client: AsyncClient, summary_test_setup: dict
):
    user_a = summary_test_setup["user_a"]
    headers_a = summary_test_setup["headers_a"]

    async with async_session_maker() as db_session:
        unready_paper = Paper(
            id=uuid.uuid4(),
            user_id=user_a.id,
            title="Draft Paper",
            file_path="/mock/draft.pdf",
            status="parsing",
        )
        db_session.add(unready_paper)
        await db_session.commit()

    res = await client.post(f"/papers/{unready_paper.id}/summary", headers=headers_a)
    assert res.status_code == 400
    assert "Paper belum selesai diproses" in res.json()["detail"]


@pytest.mark.asyncio
async def test_generate_and_get_summary_lifecycle(
    client: AsyncClient, summary_test_setup: dict
):
    paper = summary_test_setup["paper"]
    headers_a = summary_test_setup["headers_a"]

    # 1. Generate summary
    res_post = await client.post(f"/papers/{paper.id}/summary", headers=headers_a)
    assert res_post.status_code == 200
    data = res_post.json()

    assert data["paper_id"] == str(paper.id)
    assert "content" in data
    content = data["content"]
    assert "research_question" in content
    assert "method" in content
    assert "dataset" in content
    assert "metrics" in content
    assert "results" in content
    assert "limitations" in content
    assert data["prompt_version"] == "summary-v1"

    # 2. Get saved summary
    res_get = await client.get(f"/papers/{paper.id}/summary", headers=headers_a)
    assert res_get.status_code == 200
    saved_data = res_get.json()
    assert saved_data["id"] == data["id"]
    assert saved_data["content"]["method"] == content["method"]

    # 3. Regenerate summary (updates existing row without violating unique constraint)
    res_regen = await client.post(
        f"/papers/{paper.id}/summary/regenerate", headers=headers_a
    )
    assert res_regen.status_code == 200
    regen_data = res_regen.json()
    assert regen_data["id"] == data["id"]


@pytest.mark.asyncio
async def test_summary_user_isolation(client: AsyncClient, summary_test_setup: dict):
    paper = summary_test_setup["paper"]
    headers_b = summary_test_setup["headers_b"]  # Different user

    # User B cannot get summary
    res_get = await client.get(f"/papers/{paper.id}/summary", headers=headers_b)
    assert res_get.status_code == 404

    # User B cannot generate summary
    res_post = await client.post(f"/papers/{paper.id}/summary", headers=headers_b)
    assert res_post.status_code == 404
