"""
Script seeding akun demo dan paper contoh untuk Telaah (backend/scripts/seed_demo.py).
Membuat:
1. Akun demo: demo@telaah.app / password123
2. Mengunggah & memproses 3 paper benchmark contoh:
   - Attention Is All You Need (Vaswani et al.)
   - BERT: Pre-training of Deep Bidirectional Transformers (Devlin et al.)
   - LoRA: Low-Rank Adaptation of Large Language Models (Hu et al.)
3. Menghasilkan ringkasan terstruktur dan chunks yang siap ditanya.
"""

import asyncio
import shutil
import sys
import uuid
from pathlib import Path

from sqlalchemy import select

BASE_DIR = Path(__file__).resolve().parent.parent.parent
BACKEND_DIR = BASE_DIR / "backend"
EVAL_PAPERS_DIR = BASE_DIR / "eval" / "papers"

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.config import settings
from app.core.security import hash_password
from app.db.models import Paper, Summary, User
from app.db.session import async_session_maker
from app.ingest.pipeline import run_ingest_pipeline
from app.llm.prompts import SUMMARY_PROMPT_VERSION

DEMO_EMAIL = "demo@telaah.app"
DEMO_PASSWORD = "password123"

SAMPLE_PAPERS = [
    {
        "filename": "attention_vaswani2017.pdf",
        "title": "Attention Is All You Need",
        "authors": ["Ashish Vaswani", "Noam Shazeer", "Niki Parmar", "Jakob Uszkoreit"],
        "arxiv_id": "1706.03762",
        "summary": {
            "research_question": "Bagaimana merancang arsitektur sequence transduction tanpa recurrent atau convolutional network?",
            "method": "Arsitektur Transformer berbasis murni Multi-Head Self-Attention dan feed-forward networks (6 encoder & 6 decoder layers).",
            "dataset": "WMT 2014 English-to-German (4.5M pasang kalimat) dan WMT 2014 English-to-French (36M pasang kalimat).",
            "metrics": "BLEU score dan estimasi training FLOPs.",
            "results": "Mencapai skor BLEU 28.4 pada English-to-German dan 41.8 pada English-to-French dengan waktu training 3.5 hari di 8 GPU.",
            "limitations": "Kompleksitas komputasi dan memori kuadratik O(n^2) terhadap panjang teks input n.",
            "tldr": "Transformer menggantikan RNN/CNN dengan Multi-Head Self-Attention, menghasilkan model penerjemahan bahasa yang lebih cepat dilatih dan lebih akurat.",
        },
    },
    {
        "filename": "bert_devlin2018.pdf",
        "title": "BERT: Pre-training of Deep Bidirectional Transformers for Language Understanding",
        "authors": ["Jacob Devlin", "Ming-Wei Chang", "Kenton Lee", "Kristina Toutanova"],
        "arxiv_id": "1810.04805",
        "summary": {
            "research_question": "Bagaimana melatih representasi bahasa bidirectional dua arah secara deep tanpa batasan left-to-right?",
            "method": "Pre-training Transformer encoder menggunakan dua tugas unsupervised: Masked Language Model (MLM 15%) dan Next Sentence Prediction (NSP).",
            "dataset": "BooksCorpus (800M kata) dan English Wikipedia (2,500M kata).",
            "metrics": "Skor GLUE benchmark, akurasi MultiNLI, SQuAD v1.1/v2.0 F1.",
            "results": "BERT-Large meraih skor GLUE 80.5% (+7.7 poin absolut) dan SQuAD v1.1 F1 93.2, melampaui kemampuan rata-rata manusia.",
            "limitations": "Biaya komputasi pre-training tinggi (membutuhkan 64 TPU chip selama 4 hari) dan diskrepansi masking token [MASK] saat fine-tuning.",
            "tldr": "BERT memperkenalkan representasi bahasa dua arah secara murni melalui MLM dan NSP, menetapkan standar baru pada 11 tugas NLP.",
        },
    },
    {
        "filename": "lora_hu2021.pdf",
        "title": "LoRA: Low-Rank Adaptation of Large Language Models",
        "authors": ["Edward J. Hu", "Yelong Shen", "Phillip Wallis", "Zeyuan Allen-Zhu"],
        "arxiv_id": "2106.09685",
        "summary": {
            "research_question": "Bagaimana melakukan fine-tuning efisien pada Large Language Model tanpa melatih ulang seluruh miliaran parameter?",
            "method": "Membekukan bobot model pra-latih (W_0) dan menambahkan matriks dekomposisi rank rendah (B * A) pada lapisan perhatian diri (rank r << d).",
            "dataset": "GLUE benchmark, E2E NLG Challenge, DART, dan WebNLG pada GPT-2, RoBERTa, DeBERTa, dan GPT-3 175B.",
            "metrics": "Akurasi GLUE, BLEU/ROUGE-L NLG, penggunaan VRAM GPU, dan latensi inferensi.",
            "results": "Mengurangi parameter yang dapat dilatih hingga 10.000 kali lipat dan kebutuhan VRAM GPU hingga 3 kali lipat dengan performa setara atau lebih baik dari full fine-tuning.",
            "limitations": "Tidak mudah menggabungkan multiple adaptasi batch secara bersamaan jika input berasal dari domain kueri yang berbeda dalam satu batch inferensi.",
            "tldr": "LoRA membekukan bobot model dasar dan hanya melatih matriks rank rendah tambahan, memangkas kebutuhan memori GPU secara drastis saat fine-tuning LLM.",
        },
    },
]


async def seed_demo():
    print("=" * 70)
    print("SEEDING AKUN DEMO DAN PAPER CONTOH TELAAH")
    print("=" * 70)

    async with async_session_maker() as db:
        # 1. Cek atau buat user demo
        user = await db.scalar(select(User).where(User.email == DEMO_EMAIL))
        if not user:
            user = User(
                id=uuid.uuid4(),
                email=DEMO_EMAIL,
                password_hash=hash_password(DEMO_PASSWORD),
            )
            db.add(user)
            await db.commit()
            await db.refresh(user)
            print(f"[+] Akun demo berhasil dibuat: {DEMO_EMAIL} (Password: {DEMO_PASSWORD})")
        else:
            print(f"[*] Akun demo sudah ada: {DEMO_EMAIL}")

        user_storage = Path(settings.storage_path) / str(user.id)
        user_storage.mkdir(parents=True, exist_ok=True)

        # 2. Proses tiap paper contoh
        for info in SAMPLE_PAPERS:
            src_pdf = EVAL_PAPERS_DIR / info["filename"]
            if not src_pdf.exists():
                print(f"[!] File sumber {src_pdf} tidak ditemukan. Melewati...")
                continue

            existing_paper = await db.scalar(
                select(Paper).where(
                    Paper.user_id == user.id,
                    Paper.title == info["title"],
                )
            )

            if existing_paper:
                print(f"[*] Paper '{info['title']}' sudah ada di akun demo.")
                continue

            paper_id = uuid.uuid4()
            dest_pdf = user_storage / f"{paper_id}.pdf"
            shutil.copy2(src_pdf, dest_pdf)

            paper = Paper(
                id=paper_id,
                user_id=user.id,
                title=info["title"],
                authors=info["authors"],
                source_type="arxiv",
                source_ref=info["arxiv_id"],
                file_path=str(dest_pdf),
                status="ready",
                page_count=5,
            )
            db.add(paper)
            await db.commit()
            await db.refresh(paper)

            # Jalankan ingest pipeline untuk menghasilkan chunks dan embeddings
            print(f"[+] Memproses ingest pipeline untuk: '{info['title']}'...")
            await run_ingest_pipeline(paper.id, session=db)

            # Simpan ringkasan terstruktur
            summary = Summary(
                id=uuid.uuid4(),
                paper_id=paper.id,
                content=info["summary"],
                prompt_version=SUMMARY_PROMPT_VERSION,
            )
            db.add(summary)
            await db.commit()
            print(f"[✓] Paper '{info['title']}' siap ditanya jawab dan diringkas.")

    print("\n" + "=" * 70)
    print("STATUS SEEDING BERHASIL 100%!")
    print("Login URL: http://localhost:3000/login")
    print(f"Email    : {DEMO_EMAIL}")
    print(f"Password : {DEMO_PASSWORD}")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(seed_demo())
