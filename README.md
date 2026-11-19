# Telaah 🔍

> **Asisten Riset Cerdas untuk Paper Ilmiah**: Ajukan pertanyaan apa saja tentang paper Anda, dapatkan jawaban akurat berbasis konteks yang dilengkapi sitasi interaktif dan sorotan teks asli di PDF.

[![CI Status](https://github.com/DickyFerdy/telaah/actions/workflows/ci.yml/badge.svg)](https://github.com/DickyFerdy/telaah/actions)
![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.11%20%7C%203.12-blue)
![Next.js](https://img.shields.io/badge/next.js-16.4-black)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16%20%2B%20pgvector-336791)

---

## 📌 Masalah yang Diselesaikan

Membaca dan membedah paper ilmiah berbahasa Inggris seringkali memakan waktu berjam-jam, terutama bagi akademisi, peneliti, dan mahasiswa. Penggunaan AI/LLM konvensional sering menimbulkan masalah:
1. **Halusinasi**: Model mengarang klaim angka atau kutipan yang tidak tercantum dalam paper.
2. **Sulit Diverifikasi**: Jawaban AI tidak menunjukkan di halaman atau kalimat mana klaim tersebut bersumber.
3. **Pencampuran Konteks**: Chunking teks biasa memotong teks secara kaku sehingga bagian *Abstrak*, *Metode*, dan *Daftar Pustaka* saling bercampur.

**Telaah** memecahkan masalah ini dengan pendekatan **Section-Aware Ingestion Pipeline**, **Hybrid Retrieval + Cross-Encoder Reranking**, dan **Interactive Citation Grounding**: setiap klaim jawaban wajib menyertakan nomor sitasi `[1]`, `[2]` yang dapat diklik untuk langsung melompat ke halaman PDF dan menyorot teks aslinya (*bounding box highlight*).

---

## ✨ Fitur Utama

- 📄 **Upload & Impor Fleksibel**: Unggah dokumen PDF lokal (validasi biner *magic bytes* `%PDF-`, batas 20 MB) atau impor langsung dari link/ID arXiv lengkap dengan metadata resmi (judul & daftar penulis).
- 🧩 **Parser & Bounding Box Presisi**: Menggunakan PyMuPDF untuk ekstraksi teks instan (>400 halaman/detik) sekaligus menyimpan koordinat piksel `(x0, y0, x1, y1)` per blok teks.
- 🏷️ **Deteksi Bagian Cerdas (*Section-Aware*)**: Heuristik regex IMRaD mengenali bagian *Abstract*, *Introduction*, *Methodology*, *Experiments/Results*, *Discussion*, hingga *References*.
- ✂️ **Chunking Sadar Bagian**: Teks tidak pernah dipotong melintasi batas bab; pemotongan terjadi secara alami per kalimat dengan batas token adaptif.
- 🔍 **Hybrid Retrieval + Reranking**: Menggabungkan pencarian semantik dense (`pgvector` HNSW 768-dimensi) dan pencarian kata kunci sparse (PostgreSQL `to_tsvector` English GIN) via **Reciprocal Rank Fusion (RRF)**, lalu diskor ulang menggunakan **Cross-Encoder Reranker**.
- 💬 **Streaming Chat dengan Sitasi Interaktif**: Jawaban dihasilkan secara streaming via Server-Sent Events (SSE). Klik sitasi `[1]` pada jawaban untuk langsung menggulir PDF dan menggambar sorotan kotak (*bounding box*) di posisi teks aslinya.
- 📋 **Structured Summary Cards**: Ekstraksi otomatis 7 elemen kunci paper ilmiah: *Research Question*, *Methodology*, *Dataset*, *Metrics*, *Results*, *Limitations*, dan *TL;DR*.
- 💡 **Penjelas Istilah Teks (*Explain Selection*)**: Sorot istilah teknis atau rumus apa pun pada viewer PDF untuk mendapatkan penjelasan kontekstual instan dari LLM.
- 🗂️ **Manajemen Sesi Obrolan**: Simpan riwayat percakapan dalam beberapa sesi obrolan mandiri per paper (*multi-session conversations*).
- 📊 **Dashboard Evaluasi Ilmiah (`/eval`)**: Evaluasi kualitas jawaban dan retrieval bawaan yang mengukur Token F1, ROUGE-L, Refusal Accuracy, Citation Recall, Latensi p50/p95, dan estimasi biaya per query.
- 🛡️ **Keamanan & Rate Limiting**: Proteksi multi-tenant penuh (tiap query difilter berdasarkan `user_id`), otentikasi JWT, validasi ekstensi/MIME/magic bytes, pembatasan ukuran payload, dan sliding-window rate limiting pada endpoint upload & chat.

---

## 🏗️ Arsitektur Sistem

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│                         Frontend: Next.js 16 (App Router)                        │
│     Split-View Layout · React-PDF · Bounding Box Canvas · SSE Streaming Chat    │
└────────────────────────────────────────┬─────────────────────────────────────────┘
                                         │ REST API / SSE
┌────────────────────────────────────────▼─────────────────────────────────────────┐
│                          Backend: FastAPI (Python 3.11+)                         │
│                                                                                  │
│  ┌─────────────────────────── Ingestion Pipeline ─────────────────────────────┐  │
│  │ 1. Validator: Cek MIME application/pdf & Magic Bytes %PDF-                 │  │
│  │ 2. PyMuPDF Parser: Ekstrak teks & koordinat bounding box (x0, y0, x1, y1)  │  │
│  │ 3. Section Classifier: Deteksi IMRaD & hierarki heading                    │  │
│  │ 4. Section-Aware Chunker: Potong per kalimat dengan batas overlap token    │  │
│  │ 5. Batch Embedder: Gemini text-embedding-004 (768 dimensi)                 │  │
│  └─────────────────────────────────────┬──────────────────────────────────────┘  │
│                                        │                                         │
│  ┌─────────────────────────── Retrieval & Generation ─────────────────────────┐  │
│  │ 1. Query Embedder: Embedding pertanyaan pengguna (RETRIEVAL_QUERY)         │  │
│  │ 2. Hybrid Search: Vector Cosine Similarity (pgvector) + BM25 (tsvector)    │  │
│  │ 3. RRF (Reciprocal Rank Fusion): Gabungkan skor dense + sparse             │  │
│  │ 4. Cross-Encoder Reranker: Skor ulang top-K kandidat chunk teks            │  │
│  │ 5. Grounded Prompt & SSE Streamer: Gemini 2.5 Flash / 1.5 Pro              │  │
│  └─────────────────────────────────────┬──────────────────────────────────────┘  │
└────────────────────────────────────────┼─────────────────────────────────────────┘
                                         │ Async SQLAlchemy + asyncpg
┌────────────────────────────────────────▼─────────────────────────────────────────┐
│                    PostgreSQL 16 + pgvector Database                             │
│                                                                                  │
│  • chunks.embedding : Vektor 768 dimensi (HNSW Cosine Distance Index)            │
│  • chunks.tsv       : to_tsvector('english') (PostgreSQL GIN Index)              │
│  • chunks.bbox      : JSONB koordinat kotak sorotan PDF                          │
│  • users, papers, conversations, messages, summaries : Multi-tenant isolated     │
└──────────────────────────────────────────────────────────────────────────────────┘
```

---

## 📊 Hasil Evaluasi & Benchmark Ilmiah

Berdasarkan pengujian pada benchmark dataset ilmiah di [`eval/dataset.jsonl`](./eval/dataset.jsonl) (5 paper representatif: *Attention Is All You Need*, *BERT*, *LoRA*, *ResNet*, *Diffusion Models* dengan 30 pertanyaan acuan beranotasi sitasi), berikut perbandingan mode retrieval yang dicatat di [`EVAL.md`](./EVAL.md):

| Mode Retrieval | Token F1 | ROUGE-L | Refusal Acc (Anti-Halusinasi) | Citation Page Recall | Latency p50 | Latency p95 | Cost / Query |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Vector Saja** (Dense Cosine) | 0.4485 | 0.3802 | 100.00% | 45.00% | **0.5 ms** | 1.8 ms | $0.000078 |
| **BM25 Saja** (PostgreSQL FTS) | 0.5401 | 0.4728 | 100.00% | 81.67% | 0.8 ms | 2.1 ms | $0.000078 |
| **Hybrid RRF** (Dense + Sparse) | 0.5186 | 0.4560 | 100.00% | 68.33% | 0.7 ms | 2.4 ms | $0.000078 |
| **Hybrid + Reranker** *(Default)* | **0.5594** | **0.4901** | **100.00%** | **85.00%** | 0.9 ms | **2.6 ms** | **$0.000078** |

### Temuan Kunci:
1. **Peningkatan Recall Sitasi drastis**: Mode *Hybrid + Reranking* mencapai **85.00%** Citation Recall (+40.00% dibandingkan Vector saja), sangat unggul dalam menemukan angka spesifik, akronim, dan tabel metrik.
2. **Nol Halusinasi (*100% Refusal Accuracy*)**: Pada pertanyaan yang sengaja dibuat tidak relevan atau tidak terdapat di paper, model secara konsisten menolak menjawab (*"Informasi tidak ditemukan dalam paper ini"*).
3. **Latensi Sub-Milidetik**: Eksekusi ranking di PostgreSQL dan Cross-Encoder reranker lokal memiliki p50 latensi hanya **0.9 ms**, sangat responsif untuk kebutuhan streaming interaktif.

---

## 👤 Akun Demo & Data Sampel

Untuk mencoba langsung tanpa perlu mendaftar dari nol atau mengunduh paper manual, jalankan skrip seeding demo:

```bash
cd backend
python scripts/seed_demo.py
```

Skrip ini akan otomatis menyiapkan:
- **Email**: `demo@telaah.app`
- **Password**: `password123`
- **3 Paper Klasik Siap Tanya & Ringkas**:
  1. *Attention Is All You Need* (Vaswani et al., 2017)
  2. *BERT: Pre-training of Deep Bidirectional Transformers* (Devlin et al., 2018)
  3. *LoRA: Low-Rank Adaptation of Large Language Models* (Hu et al., 2021)

---

## 🛠️ Tech Stack

- **Frontend**: Next.js 16 (App Router), TypeScript (Strict Mode), Tailwind CSS, React-PDF, Lucide Icons.
- **Backend**: FastAPI 0.115, Pydantic v2, PyMuPDF (Fitz), SQLAlchemy 2.0 (Async), Alembic, HTTPX.
- **Database**: PostgreSQL 16 dengan ekstensi `pgvector` & Full-Text Search GIN.
- **AI & Reranker**: Google Gemini API (`text-embedding-004` & Gemini LLM), Cross-Encoder similarity reranker.
- **Evaluasi & Pengujian**: Custom evaluation suite (`eval/run_eval.py`), Pytest Asyncio, Ruff.

---

## 🚀 Panduan Menjalankan Secara Lokal

### Prasyarat
- [Docker Desktop](https://www.docker.com/) (untuk PostgreSQL + pgvector)
- [Python 3.11+](https://www.python.org/)
- [Node.js 20+](https://nodejs.org/)

### 1. Klon Repositori & Persiapan Environment
```bash
git clone https://github.com/DickyFerdy/telaah.git
cd telaah

# Salin berkas konfigurasi environment
cp .env.example .env
```
> Pastikan mengisi `GEMINI_API_KEY` di berkas `.env` jika ingin menggunakan model live Gemini.

### 2. Jalankan Database (Docker)
```bash
docker compose up -d
```
Container `telaah-db` akan aktif di port `localhost:5432` dengan ekstensi pgvector terinisialisasi.

### 3. Jalankan Backend (FastAPI)
```bash
cd backend

# Buat virtual environment & install dependensi
python -m venv .venv
# Windows:
.\.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

pip install -r requirements.txt

# Jalankan migrasi database
alembic upgrade head

# (Opsional) Seeding akun demo & paper contoh
python scripts/seed_demo.py

# Jalankan server API
uvicorn app.main:app --reload --port 8000
```
Swagger UI interaktif dapat diakses di: [http://localhost:8000/docs](http://localhost:8000/docs)

### 4. Jalankan Frontend (Next.js)
Buka terminal baru di direktori root:
```bash
cd frontend
npm install
npm run dev
```
Aplikasi web siap digunakan di: [http://localhost:3000](http://localhost:3000)
- Login demo: `demo@telaah.app` / `password123`
- Dashboard Evaluasi Ilmiah: [http://localhost:3000/eval](http://localhost:3000/eval)

---

## 🧪 Menjalankan Pengujian & Evaluasi

### 1. Pengujian & Linting Backend
```bash
cd backend
python -m ruff check .
python -m pytest -v
```

### 2. Linting & Build Frontend
```bash
cd frontend
npm run lint
npm run build
```

### 3. Menjalankan Pipeline Benchmark Evaluasi
```bash
python eval/run_eval.py --mode hybrid_rerank --output eval/results/eval_results.json
```

---

## 🗺️ Roadmap Pengembangan

- [x] **Fase 0: Setup dasar** (Next.js, FastAPI, PostgreSQL + pgvector Docker, Alembic, CI/CD).
- [x] **Fase 1: Auth & Paper Management** (JWT auth, upload PDF magic bytes, import arXiv API, isolasi multi-tenant).
- [x] **Fase 2: Ingestion Pipeline** (PyMuPDF parser, IMRaD section detection, sentence chunking, Gemini embeddings, PostgreSQL GIN full-text index).
- [x] **Fase 3: Retrieval & Chat MVP** (Hybrid search RRF, Cross-encoder reranking, SSE streaming chat, sitasi interaktif `[1]` dengan sorotan bounding box PDF, multi-session chat).
- [x] **Fase 4: Fitur Ekstraksi & Pendukung** (Structured summary cards 7 elemen ilmiah, seleksi teks "jelaskan istilah").
- [x] **Fase 5: Evaluasi & Benchmark** (Dataset 5 paper & 30 Q&A, skrip evaluasi otomatis, perbandingan 4 mode retrieval di `EVAL.md`, dashboard visual `/eval`).
- [x] **Fase 6: Hardening & Finalisasi** (Sliding-window rate limiter, security audit & input sanitization, akun demo + seed script, README akhir).
- [ ] **Deploy Production** *(Opsional / Fase Berikutnya)*: Deploy backend + pgvector di Railway/Fly.io dan frontend di Vercel.

---

## 📄 Lisensi & Kontribusi

Dilisensikan di bawah [MIT License](./LICENSE). Kontribusi dan saran perbaikan sangat dipersilakan melalui Pull Request atau Issue.
