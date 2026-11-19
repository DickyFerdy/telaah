"""
Demo interaktif untuk memverifikasi endpoint API GET /eval/summary secara langsung.
"""

import asyncio
import sys
from pathlib import Path

from httpx import ASGITransport, AsyncClient

BASE_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = BASE_DIR / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.main import app


async def demo_eval_api():
    print("=" * 70)
    print("DEMO UJI COBA LANGSUNG: ENDPOINT API GET /eval/summary")
    print("=" * 70)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/eval/summary")
        print(f"HTTP Status: {res.status_code} {res.reason_phrase}")
        data = res.json()

        print(f"\nWaktu Evaluasi   : {data['timestamp']}")
        print(f"Strategi Aktif   : {data['active_strategy']}")
        print(f"Jumlah Paper Uji : {len(data['papers'])} paper")

        print("\n[Performa Strategi Terbaik: Hybrid + Reranking]")
        hybrid_rerank = data["comparison"]["hybrid_rerank"]["summary"]
        print(f"  - Token F1 Score     : {hybrid_rerank['avg_token_f1']*100:.2f}%")
        print(f"  - ROUGE-L Score      : {hybrid_rerank['avg_rouge_l']*100:.2f}%")
        print(f"  - Citation Recall    : {hybrid_rerank['avg_citation_page_recall']*100:.2f}%")
        print(f"  - Refusal Accuracy   : {hybrid_rerank['refusal_accuracy']*100:.2f}%")
        print(f"  - Latency (p50)      : {hybrid_rerank['latency_ms']['p50']:.1f} ms")
        print(f"  - Biaya per Kueri    : ${hybrid_rerank['cost_usd']['avg_per_query']:.6f}")

        print("\n[Perbandingan Citation Recall]")
        for item in data["comparison"].values():
            print(f"  * {item['label']:<25} : {item['summary']['avg_citation_page_recall']*100:.2f}%")

    print("\n" + "=" * 70)
    print("STATUS: API DASHBOARD EVALUASI 100% AKTIF & SIAP DITAMPILKAN DI FRONTEND")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo_eval_api())
