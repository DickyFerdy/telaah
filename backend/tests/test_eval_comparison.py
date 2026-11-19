"""
Unit test untuk modul perbandingan eksperimen RAG (eval/run_comparison.py).
"""

import sys
from pathlib import Path

# Tambahkan eval ke sys.path
EVAL_DIR = Path(__file__).resolve().parent.parent.parent / "eval"
if str(EVAL_DIR) not in sys.path:
    sys.path.insert(0, str(EVAL_DIR))

import pytest
from run_comparison import (
    MODE_LABELS,
    MODES,
    format_markdown_table,
    run_comparison_benchmark,
)


def test_modes_and_labels():
    assert len(MODES) == 4
    for m in MODES:
        assert m in MODE_LABELS
        assert len(MODE_LABELS[m]) > 0


def test_format_markdown_table():
    sample_comparison = {
        "vector_only": {
            "summary": {
                "avg_token_f1": 0.85,
                "avg_rouge_l": 0.84,
                "avg_citation_page_recall": 0.60,
                "refusal_accuracy": 1.0,
                "latency_ms": {"p50": 120.0, "mean": 130.0},
                "cost_usd": {"avg_per_query": 0.00007},
            }
        },
        "hybrid_rerank": {
            "summary": {
                "avg_token_f1": 0.94,
                "avg_rouge_l": 0.93,
                "avg_citation_page_recall": 0.90,
                "refusal_accuracy": 1.0,
                "latency_ms": {"p50": 160.0, "mean": 170.0},
                "cost_usd": {"avg_per_query": 0.00008},
            }
        },
    }

    md = format_markdown_table(sample_comparison)
    assert "| Konfigurasi |" in md
    assert "Vektor Saja (Dense)" in md
    assert "Hybrid + Reranking" in md
    assert "85.00%" in md
    assert "94.00%" in md


@pytest.mark.asyncio
async def test_run_comparison_benchmark_sample(tmp_path: Path):
    dataset_path = EVAL_DIR / "dataset.jsonl"
    papers_dir = EVAL_DIR / "papers"
    output_path = tmp_path / "test_comparison.json"

    res = await run_comparison_benchmark(
        dataset_path=dataset_path,
        papers_dir=papers_dir,
        limit=2,
        output_path=output_path,
        offline=True,
    )

    assert len(res) == 4
    for m in MODES:
        assert m in res
        assert "summary" in res[m]
        assert "avg_token_f1" in res[m]["summary"]

    assert output_path.exists()
