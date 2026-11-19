"""
Unit test untuk endpoint GET /eval/summary (backend/app/api/eval.py).
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_get_eval_summary_endpoint(client: AsyncClient):
    response = await client.get("/eval/summary")
    assert response.status_code == 200

    data = response.json()
    assert "timestamp" in data
    assert "comparison" in data
    assert "papers" in data
    assert "active_strategy" in data
    assert data["active_strategy"] == "hybrid_rerank"

    # Verifikasi strategi utama tersedia
    comparison = data["comparison"]
    assert "hybrid_rerank" in comparison
    assert "vector_only" in comparison
    assert "bm25_only" in comparison
    assert "hybrid" in comparison

    hybrid_rerank = comparison["hybrid_rerank"]
    assert hybrid_rerank["label"] == "Hybrid + Reranking"
    summary = hybrid_rerank["summary"]
    assert summary["total_queries"] == 30
    assert summary["avg_token_f1"] > 0.8
    assert summary["refusal_accuracy"] == 1.0
    assert summary["avg_citation_page_recall"] >= 0.8

    # Verifikasi metadata paper
    papers = data["papers"]
    assert len(papers) == 5
    first_paper = papers[0]
    assert "title" in first_paper
    assert "filename" in first_paper
    assert "arxiv_id" in first_paper
    assert "domain" in first_paper
