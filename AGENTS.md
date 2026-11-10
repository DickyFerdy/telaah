# AGENTS.md

Aturan kerja untuk AI coding agent di repo ini. Baca file ini, `SPEC.md`, `ARCHITECTURE.md`, dan `TASKS.md` sebelum mengubah apa pun.

## Ringkasan proyek

PaperLens (nama sementara): asisten riset untuk paper ilmiah. Pengguna mengunggah satu paper (PDF atau link arXiv), lalu bertanya dan mendapat jawaban dengan sitasi yang menyorot teks asli di PDF. Fokus MVP: **satu paper**. Multi-paper adalah fase berikutnya.

## Stack

- Frontend: Next.js (App Router), TypeScript, Tailwind, react-pdf / PDF.js
- Backend: FastAPI (Python 3.11+), SQLAlchemy, Alembic
- Database: PostgreSQL + pgvector (+ full-text search untuk BM25-style)
- AI: Gemini API untuk embedding dan generasi (nama model final dicatat di `DECISIONS.md`, cek dokumentasi resmi `ai.google.dev` sebelum menulis kode)
- Deploy: Vercel (frontend), Railway / Fly.io (backend + DB)

## Struktur folder

```
/frontend        Next.js app
/backend
  /app
    /api         route FastAPI
    /core        config, security, dependensi
    /db          model, sesi, migrasi
    /ingest      parsing PDF, chunking, embedding
    /retrieval   hybrid search, reranking
    /llm         klien Gemini, prompt, streaming
  /tests
/eval            dataset dan skrip evaluasi
/docs            diagram, screenshot
```

## Perintah

> Isi ulang bagian ini setelah setup selesai, supaya agent tidak menebak.

- Jalankan backend: `cd backend && uvicorn app.main:app --reload`
- Jalankan frontend: `cd frontend && npm run dev`
- Test backend: `cd backend && pytest`
- Lint backend: `ruff check .`
- Migrasi: `alembic upgrade head`
- Evaluasi: `python eval/run_eval.py`

## Cara kerja per sesi

1. Baca `TASKS.md`, ambil **satu** item belum selesai teratas.
2. Jelaskan rencana singkat sebelum menulis kode.
3. Kerjakan item itu saja. Jangan menambah fitur di luar `SPEC.md`.
4. Jalankan test / lint, pastikan lolos.
5. Centang item di `TASKS.md`, lalu usulkan pesan commit (satu fitur, satu commit).
6. Jika membuat keputusan desain penting, tambahkan entri di `DECISIONS.md`.

## Konvensi kode

- Python: type hints wajib, format dengan `ruff`, fungsi pendek dan teruji.
- TypeScript: strict mode, tanpa `any` kecuali dijelaskan.
- Nama variabel dan fungsi dalam bahasa Inggris; komentar dan dokumentasi boleh bahasa Indonesia.
- Semua endpoint punya skema request/response (Pydantic).
- Jangan menaruh logika bisnis di route handler; pindahkan ke modul `ingest`, `retrieval`, atau `llm`.
- Semua pemanggilan embedding lewat satu antarmuka `embed(texts, task) -> vectors` di `/ingest/embedder.py`, supaya model mudah diganti saat eksperimen.
- Embedding chunk memakai task type `RETRIEVAL_DOCUMENT`; embedding pertanyaan memakai `RETRIEVAL_QUERY`.
- Dimensi embedding harus sama dengan kolom `chunks.embedding` (default 768). Mengubahnya butuh migrasi dan re-embed semua chunk.
- Tier gratis Gemini punya rate limit ketat: proses embedding dalam batch dengan jeda dan retry (exponential backoff), jangan memanggil API dalam loop tanpa kendali.

## Aturan tegas (jangan dilanggar)

- **Jangan** mengubah skema database tanpa bertanya dan tanpa migrasi Alembic.
- **Jangan** menambah dependensi besar tanpa menjelaskan alasannya.
- **Jangan** menaruh API key atau rahasia di kode. Pakai `.env` dan sediakan `.env.example`.
- **Jangan** menghapus atau menulis ulang test agar lolos; perbaiki kodenya.
- **Jangan** mengubah prompt sistem di `backend/app/llm/prompts.py` tanpa mencatat versi di `PROMPTS.md`.
- Jika instruksi ambigu, **tanya dulu**, jangan menebak.

## Keamanan

- Validasi upload: hanya PDF, batas ukuran (default 20 MB), cek MIME dan magic bytes.
- Setiap query data harus difilter berdasarkan `user_id` (tidak ada akses lintas pengguna).
- Rate limit pada endpoint chat dan upload.
- Jangan log isi dokumen pengguna atau API key.

## Bagian yang harus dipahami pemilik proyek

Pemilik proyek perlu bisa menjelaskan bagian berikut. Saat mengerjakannya, **jelaskan kode dan alasan desainnya**, bukan sekadar menulis:

- Parsing dan chunking (`/ingest`)
- Retrieval dan reranking (`/retrieval`)
- Prompt dan aturan "tidak ditemukan di paper" (`/llm`)
- Skrip evaluasi (`/eval`)
