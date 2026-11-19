"""
Skrip perbandingan eksperimen RAG Telaah (eval/run_comparison.py).
Menjalankan evaluasi komparatif 4 konfigurasi:
1. vector_only (Dense retrieval baseline)
2. bm25_only (Sparse keyword baseline)
3. hybrid (Dense + Sparse via RRF)
4. hybrid_rerank (Hybrid + Cross-Encoder Reranker)

Menghasilkan tabel ringkasan perbandingan dan berkas eval/comparison_results.json.
"""

import argparse
import asyncio
import json
import logging
import sys
import time
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = BASE_DIR / "backend"
EVAL_DIR = BASE_DIR / "eval"

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
if str(EVAL_DIR) not in sys.path:
    sys.path.insert(0, str(EVAL_DIR))

from run_eval import run_evaluation

logger = logging.getLogger("eval_comparison")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


MODES = ["vector_only", "bm25_only", "hybrid", "hybrid_rerank"]

MODE_LABELS = {
    "vector_only": "Vektor Saja (Dense)",
    "bm25_only": "Kata Kunci Saja (BM25)",
    "hybrid": "Vektor + BM25 (RRF)",
    "hybrid_rerank": "Hybrid + Reranking",
}


def format_markdown_table(comparison: dict[str, Any]) -> str:
    """Format hasil perbandingan ke dalam tabel Markdown untuk EVAL.md dan DECISIONS.md."""
    lines = [
        "| Konfigurasi | Akurasi (F1) | ROUGE-L | Sitasi (Recall) | Penolakan Benar | p50 Latency | Mean Latency | Biaya / Query |",
        "|---|---|---|---|---|---|---|---|",
    ]

    for mode in MODES:
        if mode not in comparison:
            continue
        data = comparison[mode]["summary"]
        label = MODE_LABELS.get(mode, mode)
        f1 = f"{data['avg_token_f1'] * 100:.2f}%"
        rouge = f"{data['avg_rouge_l'] * 100:.2f}%"
        cit = f"{data['avg_citation_page_recall'] * 100:.2f}%"
        refusal = f"{data['refusal_accuracy'] * 100:.2f}%"
        p50 = f"{data['latency_ms']['p50']:.1f} ms"
        mean_lat = f"{data['latency_ms']['mean']:.1f} ms"
        cost = f"${data['cost_usd']['avg_per_query']:.6f}"
        lines.append(f"| **{label}** | {f1} | {rouge} | {cit} | {refusal} | {p50} | {mean_lat} | {cost} |")

    return "\n".join(lines)


def print_comparison_matrix(comparison: dict[str, Any]) -> None:
    """Mencetak matriks perbandingan 4 mode di konsol."""
    print("\n" + "=" * 90)
    print("  MATRIKS PERBANDINGAN STRATEGI RETRIEVAL TELAAH (30 PERTANYAAN UJI)")
    print("=" * 90)
    header = f"{'Konfigurasi':<25} | {'Token F1':<10} | {'ROUGE-L':<10} | {'Cit Recall':<12} | {'Refusal':<10} | {'p50 Lat':<10}"
    print(header)
    print("-" * 90)

    for mode in MODES:
        if mode not in comparison:
            continue
        data = comparison[mode]["summary"]
        label = MODE_LABELS.get(mode, mode)
        f1 = f"{data['avg_token_f1'] * 100:.2f}%"
        rouge = f"{data['avg_rouge_l'] * 100:.2f}%"
        cit = f"{data['avg_citation_page_recall'] * 100:.2f}%"
        refusal = f"{data['refusal_accuracy'] * 100:.2f}%"
        p50 = f"{data['latency_ms']['p50']:.1f} ms"
        print(f"{label:<25} | {f1:<10} | {rouge:<10} | {cit:<12} | {refusal:<10} | {p50:<10}")

    print("=" * 90 + "\n")


def save_comparison_output(output_path: Path, final_data: dict[str, Any]) -> None:
    """Menyimpan berkas ringkasan perbandingan komparatif."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(final_data, f, indent=2, ensure_ascii=False)


async def run_comparison_benchmark(
    dataset_path: Path,
    papers_dir: Path,
    limit: int | None = None,
    output_path: Path | None = None,
    offline: bool = False,
) -> dict[str, Any]:
    """Mengeksekusi benchmark komparatif penuh pada seluruh mode."""
    comparison: dict[str, Any] = {}

    for mode in MODES:
        print(f"\n>>> MENJALANKAN EVALUASI MODE: {MODE_LABELS[mode]} [{mode}] <<<")
        result = await run_evaluation(
            dataset_path=dataset_path,
            papers_dir=papers_dir,
            mode=mode,
            limit=limit,
            output_path=None,  # Jangan timpa file tunggal
            offline=offline,
        )
        comparison[mode] = {
            "label": MODE_LABELS[mode],
            "summary": result["summary"],
        }

    print_comparison_matrix(comparison)
    md_table = format_markdown_table(comparison)
    print("REPRESENTASI MARKDOWN TABEL:\n")
    print(md_table)
    print()

    if output_path:
        final_data = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "comparison": comparison,
            "markdown_table": md_table,
        }
        save_comparison_output(output_path, final_data)
        print(f"[INFO] Hasil perbandingan komparatif disimpan di: {output_path}")

    return comparison


def main():
    parser = argparse.ArgumentParser(description="Telaah Retrieval Comparison Benchmark")
    parser.add_argument("--dataset", type=Path, default=EVAL_DIR / "dataset.jsonl", help="Path ke dataset.jsonl")
    parser.add_argument("--papers-dir", type=Path, default=EVAL_DIR / "papers", help="Direktori PDF paper")
    parser.add_argument("--limit", type=int, default=None, help="Batasi jumlah butir per mode (untuk tes cepat)")
    parser.add_argument(
        "--output",
        type=Path,
        default=EVAL_DIR / "comparison_results.json",
        help="Path file JSON output perbandingan",
    )
    parser.add_argument("--offline", action="store_true", help="Paksa mode simulasi offline")

    args = parser.parse_args()

    asyncio.run(
        run_comparison_benchmark(
            dataset_path=args.dataset,
            papers_dir=args.papers_dir,
            limit=args.limit,
            output_path=args.output,
            offline=args.offline,
        )
    )


if __name__ == "__main__":
    main()
