# PaperLens

> Asisten riset untuk paper ilmiah: tanya apa saja, jawaban disertai sitasi yang menyorot teks asli di PDF.

**Demo:** _link deploy_ · **Video singkat:** _link_

## Masalah yang diselesaikan

Membaca paper berbahasa Inggris itu lambat, terutama untuk mahasiswa. PaperLens membantu memahami isi paper lebih cepat tanpa mengorbankan keandalan: setiap jawaban bisa diverifikasi lewat sitasi, dan sistem menolak menjawab saat informasinya tidak ada di paper.

## Fitur

- Upload PDF atau impor dari arXiv
- Parsing sadar struktur (abstrak, metode, hasil, referensi)
- Tanya jawab dengan streaming dan sitasi yang menyorot teks di PDF
- Mode "tidak ditemukan di paper" untuk menekan halusinasi
- Ringkasan terstruktur otomatis
- Halaman evaluasi kualitas

_Tambahkan screenshot / GIF di sini._

## Arsitektur

_Tempel diagram dari `ARCHITECTURE.md`._

Ringkasnya: upload → parsing → chunking sadar bagian → embedding (pgvector) → retrieval hibrida (vektor + kata kunci) → reranking → generasi dengan Gemini → sitasi tervalidasi.

## Hasil evaluasi

_Ringkas tabel dari `EVAL.md`: akurasi, ketepatan sitasi, latency, biaya per query._

## Keputusan desain penting

_Pilih 3-4 dari `DECISIONS.md`, masing-masing dengan angka pendukung._

## Menjalankan secara lokal

```bash
# 1. Salin variabel lingkungan
cp .env.example .env

# 2. Jalankan database
docker compose up -d

# 3. Backend
cd backend
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload

# 4. Frontend
cd frontend
npm install
npm run dev
```

## Stack

Next.js · TypeScript · Tailwind · FastAPI · PostgreSQL + pgvector · Gemini API

## Keterbatasan

_Contoh: PDF hasil scan belum didukung; persamaan kompleks dan tabel bisa terekstrak kurang rapi._

## Rencana ke depan

Koleksi multi-paper, perbandingan metode, ekspor ke BibTeX.

## Catatan pemakaian AI

Proyek ini dikerjakan dengan bantuan AI coding tool. Arsitektur, strategi retrieval, prompt, dan evaluasi dirancang dan diverifikasi oleh saya; keputusan dan hasil ujinya tercatat di `DECISIONS.md` dan `EVAL.md`.
