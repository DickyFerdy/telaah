"""
Unit test untuk modul metrik evaluasi ilmiah Telaah (eval/metrics.py & eval/run_eval.py).
"""

import sys
from pathlib import Path

# Tambahkan eval ke sys.path
EVAL_DIR = Path(__file__).resolve().parent.parent.parent / "eval"
if str(EVAL_DIR) not in sys.path:
    sys.path.insert(0, str(EVAL_DIR))

import pytest
from metrics import (
    aggregate_metrics,
    compute_citation_metrics,
    compute_rouge_l,
    compute_token_f1,
    estimate_cost_usd,
    estimate_tokens,
    evaluate_refusal,
    is_refusal_response,
    normalize_text,
    percentile,
    tokenize,
)
from run_eval import PaperCache, evaluate_single_question


def test_normalize_and_tokenize():
    text = "Transformer: Attention Is All You Need! (Vaswani et al., 2017)"
    normalized = normalize_text(text)
    assert "!" not in normalized
    assert ":" not in normalized
    tokens = tokenize(text)
    assert "transformer" in tokens
    assert "attention" in tokens
    assert "vaswani" in tokens


def test_token_f1_metrics():
    # Exact match
    res = compute_token_f1("arsitektur transformer 6 layer", "arsitektur transformer 6 layer")
    assert res["f1"] == 1.0
    assert res["precision"] == 1.0
    assert res["recall"] == 1.0

    # Partial match
    res_partial = compute_token_f1("model transformer 6 layer", "arsitektur transformer 6 layer")
    assert 0.0 < res_partial["f1"] < 1.0
    assert res_partial["precision"] > 0
    assert res_partial["recall"] > 0

    # No overlap
    res_zero = compute_token_f1("kucing melompat tinggi", "arsitektur transformer 6 layer")
    assert res_zero["f1"] == 0.0

    # Both empty
    res_empty = compute_token_f1("", "")
    assert res_empty["f1"] == 1.0


def test_rouge_l_metric():
    ref = "arsitektur transformer menggunakan self-attention tanpa rnn"
    pred = "arsitektur transformer menggunakan self-attention"
    score = compute_rouge_l(pred, ref)
    assert score > 0.6

    # Exact match
    assert compute_rouge_l(ref, ref) == 1.0

    # Completely different
    assert compute_rouge_l("apel jeruk pisang", ref) == 0.0


def test_refusal_detection():
    refusal_answers = [
        "Informasi tersebut tidak ditemukan di dalam paper ini.",
        "Hal ini tidak disebutkan dalam paper.",
        "Paper tidak membahas mengenai topik tersebut.",
        "Not found in the paper.",
    ]
    for ans in refusal_answers:
        assert is_refusal_response(ans) is True

    valid_answers = [
        "Model ini memiliki 6 lapisan encoder dan 6 lapisan decoder.",
        "Skor BLEU yang diraih adalah 28.4 pada WMT 2014.",
    ]
    for ans in valid_answers:
        assert is_refusal_response(ans) is False

    assert evaluate_refusal("Informasi tidak ditemukan di dalam paper.", should_refuse=True) is True
    assert evaluate_refusal("Model memiliki 6 layer.", should_refuse=False) is True
    assert evaluate_refusal("Model memiliki 6 layer.", should_refuse=True) is False


def test_citation_metrics():
    # Factual question: ground truth halaman 2 & 3
    citations = [
        {"page_start": 2, "page_end": 2, "citation_number": 1},
        {"page_start": 3, "page_end": 3, "citation_number": 2},
    ]
    cit_res = compute_citation_metrics(citations, ground_truth_pages=[2, 3], should_refuse=False)
    assert cit_res["page_recall"] == 1.0
    assert cit_res["grounding_rate"] == 1.0
    assert cit_res["citation_count"] == 2
    assert cit_res["cited_pages"] == [2, 3]

    # Partial recall (hanya halaman 2)
    citations_partial = [{"page_start": 2, "page_end": 2}]
    cit_partial = compute_citation_metrics(citations_partial, ground_truth_pages=[2, 3], should_refuse=False)
    assert cit_partial["page_recall"] == 0.5
    assert cit_partial["grounding_rate"] == 1.0

    # Unanswerable question: sitasi seharusnya 0
    cit_unanswerable = compute_citation_metrics([], ground_truth_pages=[], should_refuse=True)
    assert cit_unanswerable["page_recall"] == 1.0
    assert cit_unanswerable["grounding_rate"] == 1.0


def test_token_and_cost_estimation():
    text = "Ini adalah contoh prompt dengan beberapa token untuk diestimasi."
    tokens = estimate_tokens(text)
    assert tokens > 5

    # Cost Gemini 1.5/2.5 Flash
    cost = estimate_cost_usd(input_tokens=1000, output_tokens=500)
    assert cost > 0.0
    assert cost == pytest.approx(0.000225, rel=1e-3)


def test_percentile():
    data = [10.0, 20.0, 30.0, 40.0, 50.0]
    assert percentile(data, 50) == 30.0
    assert percentile(data, 100) == 50.0
    assert percentile(data, 0) == 10.0


def test_aggregate_metrics():
    sample_results = [
        {
            "category": "factual",
            "token_f1": 0.85,
            "rouge_l": 0.80,
            "citation_page_recall": 1.0,
            "grounding_rate": 1.0,
            "total_latency_ms": 150.0,
            "retrieval_latency_ms": 50.0,
            "generation_latency_ms": 100.0,
            "input_tokens": 500,
            "output_tokens": 80,
            "cost_usd": 0.00006,
            "should_refuse": False,
            "refusal_correct": True,
        },
        {
            "category": "unanswerable",
            "token_f1": 1.0,
            "rouge_l": 1.0,
            "citation_page_recall": 1.0,
            "grounding_rate": 1.0,
            "total_latency_ms": 60.0,
            "retrieval_latency_ms": 30.0,
            "generation_latency_ms": 30.0,
            "input_tokens": 400,
            "output_tokens": 20,
            "cost_usd": 0.00003,
            "should_refuse": True,
            "refusal_correct": True,
        },
    ]

    agg = aggregate_metrics(sample_results)
    assert agg["total_queries"] == 2
    assert agg["refusal_accuracy"] == 1.0
    assert agg["avg_token_f1"] == pytest.approx(0.925, abs=0.01)
    assert agg["latency_ms"]["mean"] == 105.0
    assert "factual" in agg["by_category"]
    assert "unanswerable" in agg["by_category"]


@pytest.mark.asyncio
async def test_evaluate_single_question_offline():
    papers_dir = EVAL_DIR / "papers"
    cache = PaperCache(papers_dir)

    dummy_item = {
        "id": "q001",
        "paper": "attention_vaswani2017.pdf",
        "category": "factual",
        "question": "Berapa banyak lapisan encoder dan decoder yang digunakan?",
        "reference_answer": "Arsitektur Transformer menggunakan tumpukan N = 6 lapisan untuk encoder dan N = 6 lapisan untuk decoder.",
        "source_pages": [2],
        "should_refuse": False,
    }

    result = await evaluate_single_question(dummy_item, cache, mode="hybrid_rerank", offline=True)
    assert result["id"] == "q001"
    assert result["token_f1"] > 0.0
    assert result["total_latency_ms"] > 0.0
    assert result["input_tokens"] > 0
    assert result["output_tokens"] > 0
    assert result["cost_usd"] > 0.0
