# Telaah 🔍

> **Asisten Riset Cerdas untuk Paper Ilmiah**: Ajukan pertanyaan apa saja tentang paper Anda, dapatkan jawaban akurat berbasis konteks yang dilengkapi sitasi interaktif dan sorotan teks asli di PDF.

[![CI Status](https://github.com/DickyFerdy/telaah/actions/workflows/ci.yml/badge.svg)](https://github.com/DickyFerdy/telaah/actions)
![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.11%20%7C%203.12%20%7C%203.14-blue)
![Next.js](https://img.shields.io/badge/next.js-16.4-black)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16%20%2B%20pgvector-336791)

---

## 📌 Masalah yang Diselesaikan

Membaca dan membedah paper ilmiah berbahasa Inggris seringkali memakan waktu berjam-jam, terutama bagi akademisi, peneliti, dan mahasiswa. Penggunaan LLM biasa sering kali menimbulkan masalah:
1. **Halusinasi**: Model mengarang klaim atau kutipan yang sebenarnya tidak ada di dalam paper.
2. **Sulit Diverifikasi**: Jawaban AI tidak menunjukkan di halaman atau paragraf mana klaim tersebut bersumber.
3. **Pencampuran Konteks**: Chunking konvensional memotong teks secara kaku sehingga teks *Abstrak*, *Metodologi*, dan *Referensi* saling bercampur.

**Telaah** hadir untuk memecahkan masalah ini dengan pendekatan **Section-Aware Ingestion Pipeline** dan **Interactive Citation Grounding**: setiap klaim jawaban wajib menyertakan nomor sitasi yang dapat diklik untuk langsung melompat ke halaman PDF dan menyorot teks aslinya (*bounding box highlight*).

---

## ✨ Fitur Utama

- 📄 **Upload & Impor Fleksibel**: Unggah dokumen PDF lokal (validasi magic bytes, batas 20 MB) atau impor langsung dari link/ID arXiv lengkap dengan metadata resmi (judul & daftar pengarang).
- 🧩 **Parser & Bounding Box Presisi**: Menggunakan PyMuPDF untuk ekstraksi teks instan (>400 halaman/detik) sekaligus menyimpan koordinat piksel `(x0, y0, x1, y1)` per blok teks.
- 🏷️ **Deteksi Bagian Cerdas (*Section-Aware*)**: Heuristik regex IMRaD mengenali bagian *Abstract*, *Introduction*, *Methodology*, *Experiments/Results*, *Discussion*, hingga *References*.
- ✂️ **Chunking Sadar Bagian**: Teks tidak pernah dipotong melintasi batas bab; pemotongan terjadi secara alami per kalimat dengan estimasi token yang akurat.
- ⚡ **Background Processing Asinkron**: Pipeline ingest berjalan di latar belakang (status: `uploaded` → `parsing` → `embedding` → `ready`) tanpa membuat koneksi HTTP pengguna macet.
- 🔍 **Hybrid Retrieval Ready**: Dukungan ganda vektor semantik dense (`pgvector` 768-dimensi dengan indeks HNSW) dan pencarian kata kunci sparse (PostgreSQL `to_tsvector` English dengan indeks GIN).
- 🛡️ **Keamanan & Isolasi Penuh**: Autentikasi JWT, validasi kepemilikan dokumen lintas pengguna, serta cascading cleanup otomatis saat paper dihapus.

---

## 🏗️ Arsitektur Sistem

```
┌────────────────────────────────────────────────────────────────────────┐
│                        Frontend: Next.js 16 (App Router)               │
│               Tailwind CSS · React-PDF · Live Status Polling           │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ REST API / SSE
┌───────────────────────────────────▼────────────────────────────────────┐
│                        Backend: FastAPI (Python 3.11+)                 │
│                                                                        │
│  ┌─────────────────────── Pipeline Ingest ──────────────────────────┐  │
│  │ 1. Validator: Ekstensi, MIME application/pdf, Magic Bytes %PDF- │  │
│  │ 2. PyMuPDF Parser: Ekstrak teks & koordinat bbox (x0,y0,x1,y1)   │  │
│  │ 3. Section Classifier: Deteksi IMRaD & Hierarki Heading          │  │
│  │ 4. Section-Aware Chunker: Potong per kalimat (overlap context)   │  │
│  │ 5. Batch Embedder: Gemini text-embedding-004 (768 dimensi)       │  │
│  └─────────────────────────────────┬────────────────────────────────┘  │
└────────────────────────────────────┼───────────────────────────────────┘
                                     │ Async SQLAlchemy + asyncpg
┌────────────────────────────────────▼───────────────────────────────────┐
│                 PostgreSQL 16 + pgvector Database                      │
│                                                                        │
│  • chunks.embedding : Vektor 768 dimensi (HNSW Cosine Ops)             │
│  • chunks.tsv       : to_tsvector('english') (GIN Index)               │
│  • chunks.bbox      : JSONB koordinat kotak sorotan PDF                │
│  • users & papers   : Relasi kepemilikan aman & Cascade Deletion       │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 📊 Keputusan Desain & Hasil Pengujian

Kami mencatat alasan teknis dan bukti kuantitatif setiap keputusan arsitektur di [`DECISIONS.md`](./DECISIONS.md):

| Keputusan | Opsi Terpilih | Alasan & Bukti Kuantitatif |
| :--- | :--- | :--- |
| **PDF Parser** | **PyMuPDF (`pymupdf`)** | Kecepatan **~2.5 ms/halaman** (>400 hal/detik) dengan **100% presisi koordinat bounding box**. Menghemat resource (RAM <50 MB, tanpa GPU) dibanding GROBID (Java JVM) dan Marker (Deep Learning multi-GB). |
| **Chunking** | **Section-Aware Chunking** | Menjaga 100% isolasi bagian teks paper. Mencegah sitasi bias dan menjaga integritas konteks per topik ilmiah. |
| **Model Vektor** | **Gemini text-embedding-004** | Dimensi 768, terintegrasi mulus dengan pgvector HNSW, dilengkapi retry otomatis dengan *exponential backoff* saat rate limit. |
| **Search Engine** | **Hybrid Search (Dense + Sparse)** | Menggabungkan pemahaman semantik embedding dengan ketepatan istilah teknis/akronim via PostgreSQL Full-Text Search. |

---

## 🛠️ Tech Stack

- **Frontend**: Next.js 16 (App Router), TypeScript (Strict Mode), Tailwind CSS, Lucide Icons
- **Backend**: FastAPI, Pydantic v2, PyMuPDF, SQLAlchemy 2.0 (Async), Alembic, HTTPX
- **Database**: PostgreSQL 16 dengan ekstensi `pgvector`
- **AI & ML**: Google Gemini API (`text-embedding-004` & Gemini generative models)
- **Tooling & CI/CD**: Ruff (Linter/Formatter), Pytest Asyncio, Docker Compose, GitHub Actions

---

## 🚀 Menjalankan Secara Lokal

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

---

## 🧪 Menjalankan Pengujian

```bash
# Test & Lint Backend
cd backend
python -m ruff check .
python -m pytest -v

# Lint & Build Frontend
cd frontend
npm run lint
npm run build
```

---

## 🗺️ Roadmap Pengembangan

- [x] **Fase 0**: Setup repositori, Docker Compose pgvector, skema database, CI/CD.
- [x] **Fase 1**: Otentikasi JWT, Upload PDF dengan validasi biner, Impor via arXiv API, Manajemen paper.
- [x] **Fase 2**: Pipeline Ingest asinkron, PyMuPDF parser, deteksi bagian IMRaD, chunking sadar bagian, embedding batch pgvector, indeks TSV.
- [ ] **Fase 3**: Retrieval hibrida (RRF), Reranker, UI Chat streaming dengan sitasi bernomor & sorotan visual PDF.
- [ ] **Fase 4**: Ringkasan terstruktur otomatis & skrip evaluasi retrieval (`EVAL.md`).

---

## 📄 Lisensi & Kontribusi

Dilisensikan di bawah [MIT License](./LICENSE). Kontribusi dan saran perbaikan sangat dipersilakan melalui Pull Request atau Issue.
