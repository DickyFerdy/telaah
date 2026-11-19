"""
Modul kalkulasi metrik evaluasi ilmiah untuk Telaah.
Mendukung:
1. Akurasi teks (Token-level F1 & ROUGE-L)
2. Evaluasi penolakan / pencegahan halusinasi (Refusal Accuracy)
3. Ketepatan sitasi & jangkauan halaman (Citation Precision & Page Recall)
4. Pengukuran durasi (Latency p50, p95, mean)
5. Estimasi biaya API (Cost Tracking)
"""

import math
import re
import string
import sys
from pathlib import Path
from typing import Any

# Tambahkan backend ke path agar modul-modul app dapat diakses
backend_path = Path(__file__).resolve().parent.parent / "backend"
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

try:
    from app.llm.not_found import is_not_found_response
except ImportError:
    # Fallback mandiri jika backend belum ada di path saat isolasi
    def is_not_found_response(text: str) -> bool:
        lower = text.lower()
        return "tidak ditemukan" in lower or "not found" in lower or "tidak disebutkan" in lower


def normalize_text(text: str) -> str:
    """Normalisasi teks: huruf kecil, hapus tanda baca, dan standarisasi spasi."""
    text = text.lower()
    # Hapus tanda baca
    text = "".join(ch for ch in text if ch not in string.punctuation)
    # Hapus whitespace berlebih
    text = re.sub(r"\s+", " ", text).strip()
    return text


def tokenize(text: str) -> list[str]:
    """Tokenisasi sederhana berbasis whitespace setelah normalisasi."""
    norm = normalize_text(text)
    return norm.split() if norm else []


def compute_token_f1(prediction: str, reference: str) -> dict[str, float]:
    """
    Menghitung Token-level Precision, Recall, dan F1 Score antara prediksi dan acuan.
    Metrik standar QA (mirip SQuAD).
    """
    pred_tokens = tokenize(prediction)
    ref_tokens = tokenize(reference)

    if not pred_tokens and not ref_tokens:
        return {"precision": 1.0, "recall": 1.0, "f1": 1.0}
    if not pred_tokens or not ref_tokens:
        return {"precision": 0.0, "recall": 0.0, "f1": 0.0}

    # Hitung interseksi token (dengan frekuensi)
    common: dict[str, int] = {}
    for t in pred_tokens:
        if t in ref_tokens:
            common[t] = min(pred_tokens.count(t), ref_tokens.count(t))

    overlap = sum(common.values())
    if overlap == 0:
        return {"precision": 0.0, "recall": 0.0, "f1": 0.0}

    precision = overlap / len(pred_tokens)
    recall = overlap / len(ref_tokens)
    f1 = 2 * (precision * recall) / (precision + recall)
    return {
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
    }


def compute_rouge_l(prediction: str, reference: str) -> float:
    """
    Menghitung skor ROUGE-L berbasis Longest Common Subsequence (LCS).
    """
    pred_tokens = tokenize(prediction)
    ref_tokens = tokenize(reference)

    m = len(pred_tokens)
    n = len(ref_tokens)

    if m == 0 and n == 0:
        return 1.0
    if m == 0 or n == 0:
        return 0.0

    # Dynamic Programming untuk LCS
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if pred_tokens[i - 1] == ref_tokens[j - 1]:
                dp[i][j] = dp[i - 1][j - 1] + 1
            else:
                dp[i][j] = max(dp[i - 1][j], dp[i][j - 1])

    lcs_len = dp[m][n]
    if lcs_len == 0:
        return 0.0

    p = lcs_len / m
    r = lcs_len / n
    f1 = 2 * p * r / (p + r)
    return round(f1, 4)


def is_refusal_response(text: str) -> bool:
    """
    Mendeteksi apakah respons model menolak menjawab karena info tidak ada di paper.
    """
    if is_not_found_response(text):
        return True
    lower = text.lower()
    refusal_keywords = [
        "tidak ditemukan",
        "tidak disebutkan",
        "tidak dibahas",
        "tidak membahas",
        "tidak menjelaskan",
        "tidak menganalisis",
        "tidak menyajikan",
        "tidak tercantum",
        "tidak memuat informasi",
        "tidak terdapat",
        "not found in the paper",
        "not mentioned",
        "does not discuss",
        "does not mention",
    ]
    return any(kw in lower for kw in refusal_keywords)


def evaluate_refusal(prediction: str, should_refuse: bool) -> bool:
    """Mengecek apakah model menolak saat seharusnya menolak, atau menjawab saat seharusnya menjawab."""
    model_refused = is_refusal_response(prediction)
    return model_refused == should_refuse


def compute_citation_metrics(
    citations: list[dict[str, Any]],
    ground_truth_pages: list[int],
    should_refuse: bool,
) -> dict[str, Any]:
    """
    Menghitung metrik ketepatan sitasi:
    - page_recall: proporsi halaman acuan yang dicakup oleh sitasi model.
    - grounding_rate: apakah jawaban non-penolakan memiliki sitasi valid.
    - citation_count: jumlah sitasi aktif.
    """
    cited_pages: set[int] = set()
    for c in citations:
        p_start = c.get("page_start") or c.get("page")
        p_end = c.get("page_end") or p_start
        if p_start is not None:
            if p_end is not None and p_end >= p_start:
                cited_pages.update(range(int(p_start), int(p_end) + 1))
            else:
                cited_pages.add(int(p_start))

    target_pages = set(ground_truth_pages)

    if should_refuse:
        # Jika pertanyaan tidak dapat dijawab, sitasi seharusnya 0
        page_recall = 1.0 if len(citations) == 0 else 0.0
        grounding_rate = 1.0 if len(citations) == 0 else 0.0
    else:
        if not target_pages:
            page_recall = 1.0 if len(cited_pages) > 0 else 0.0
        else:
            intersection = target_pages & cited_pages
            page_recall = len(intersection) / len(target_pages)
        grounding_rate = 1.0 if len(citations) > 0 else 0.0

    return {
        "page_recall": round(page_recall, 4),
        "grounding_rate": round(grounding_rate, 4),
        "citation_count": len(citations),
        "cited_pages": sorted(cited_pages),
    }


def estimate_tokens(text: str) -> int:
    """
    Estimasi jumlah token Gemini berdasarkan rasio karakter & kata.
    Rata-rata 1 kata ~ 1.3 token, atau 4 karakter ~ 1 token.
    """
    if not text:
        return 0
    words = len(text.split())
    by_char = len(text) / 4.0
    by_word = words * 1.3
    return max(1, int((by_char + by_word) / 2))


def estimate_cost_usd(
    input_tokens: int,
    output_tokens: int,
    model: str = "gemini-1.5-flash",
) -> float:
    """
    Menghitung estimasi biaya dalam USD berdasarkan model yang digunakan.
    Tarif Gemini 1.5/2.5 Flash:
    - Input: $0.075 / 1,000,000 tokens ($0.000000075 / token)
    - Output: $0.30 / 1,000,000 tokens ($0.00000030 / token)
    """
    # Tarif per token
    rate_input = 0.075 / 1_000_000
    rate_output = 0.30 / 1_000_000

    cost = (input_tokens * rate_input) + (output_tokens * rate_output)
    return round(cost, 8)


def percentile(data: list[float], pct: float) -> float:
    """Menghitung nilai persentil p (0..100) dari kumpulan data."""
    if not data:
        return 0.0
    sorted_d = sorted(data)
    idx = (len(sorted_d) - 1) * (pct / 100.0)
    floor_idx = math.floor(idx)
    ceil_idx = math.ceil(idx)
    if floor_idx == ceil_idx:
        return sorted_d[int(idx)]
    d0 = sorted_d[floor_idx] * (ceil_idx - idx)
    d1 = sorted_d[ceil_idx] * (idx - floor_idx)
    return round(d0 + d1, 2)


def aggregate_metrics(results: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Mengagregasikan metrik dari sekumpulan hasil pengujian individual.
    Menghitung rata-rata, median, p95, dan breakdown per kategori.
    """
    if not results:
        return {}

    total = len(results)
    f1_scores = [r["token_f1"] for r in results]
    rouge_l_scores = [r["rouge_l"] for r in results]
    citation_recalls = [r["citation_page_recall"] for r in results]
    grounding_rates = [r["grounding_rate"] for r in results]

    total_latencies = [r["total_latency_ms"] for r in results]
    retrieval_latencies = [r["retrieval_latency_ms"] for r in results]
    generation_latencies = [r["generation_latency_ms"] for r in results]

    input_tokens = sum(r["input_tokens"] for r in results)
    output_tokens = sum(r["output_tokens"] for r in results)
    total_cost = sum(r["cost_usd"] for r in results)

    # Refusal accuracy untuk item yang memang unanswerable
    unanswerables = [r for r in results if r.get("should_refuse")]
    refusal_acc = (
        sum(1 for r in unanswerables if r["refusal_correct"]) / len(unanswerables)
        if unanswerables
        else 1.0
    )

    # Breakdown per kategori
    categories = sorted({r["category"] for r in results})
    cat_breakdown: dict[str, Any] = {}
    for cat in categories:
        cat_items = [r for r in results if r["category"] == cat]
        cat_breakdown[cat] = {
            "count": len(cat_items),
            "avg_token_f1": round(sum(r["token_f1"] for r in cat_items) / len(cat_items), 4),
            "avg_rouge_l": round(sum(r["rouge_l"] for r in cat_items) / len(cat_items), 4),
            "avg_citation_recall": round(
                sum(r["citation_page_recall"] for r in cat_items) / len(cat_items), 4
            ),
        }

    return {
        "total_queries": total,
        "avg_token_f1": round(sum(f1_scores) / total, 4),
        "avg_rouge_l": round(sum(rouge_l_scores) / total, 4),
        "refusal_accuracy": round(refusal_acc, 4),
        "avg_citation_page_recall": round(sum(citation_recalls) / total, 4),
        "avg_grounding_rate": round(sum(grounding_rates) / total, 4),
        "latency_ms": {
            "mean": round(sum(total_latencies) / total, 2),
            "p50": percentile(total_latencies, 50),
            "p95": percentile(total_latencies, 95),
            "retrieval_mean": round(sum(retrieval_latencies) / total, 2),
            "generation_mean": round(sum(generation_latencies) / total, 2),
        },
        "tokens": {
            "total_input": input_tokens,
            "total_output": output_tokens,
            "avg_input_per_query": round(input_tokens / total, 1),
            "avg_output_per_query": round(output_tokens / total, 1),
        },
        "cost_usd": {
            "total": round(total_cost, 6),
            "avg_per_query": round(total_cost / total, 6),
        },
        "by_category": cat_breakdown,
    }
