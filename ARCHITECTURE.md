# ARCHITECTURE.md

## Gambaran umum

```
[Browser: Next.js + PDF viewer]
        │  HTTPS (REST + SSE)
        ▼
[FastAPI]──────────────┐
   │                   │
   │ ingest (async)    │ chat
   ▼                   ▼
[Parsing → Chunking → Embedding]   [Retrieval → Reranking → LLM]
   │                                   │
   └──────────► [PostgreSQL + pgvector] ◄┘
        │
   [File storage: PDF]
```

## Alur ingest (upload → siap ditanya)

1. **Upload**: validasi tipe, ukuran, magic bytes; simpan file; buat record `papers` berstatus `uploaded`.
2. **Parsing** (`/ingest/parser.py`): ekstrak teks per halaman beserta koordinat (bbox). Kandidat: PyMuPDF (cepat), Marker atau GROBID (lebih paham struktur). Bandingkan dan catat hasil di `DECISIONS.md`.
3. **Deteksi struktur** (`/ingest/sections.py`): kenali judul bagian (Abstract, Method, Results, Discussion, References) lewat heuristik font/format, dengan LLM sebagai cadangan.
4. **Chunking** (`/ingest/chunker.py`): potong per bagian, ukuran target 300-500 token, overlap kecil, jangan memotong tabel atau persamaan di tengah. Simpan `section`, halaman, dan bbox.
5. **Embedding** (`/ingest/embedder.py`): panggil Gemini Embedding dengan task type `RETRIEVAL_DOCUMENT`, dimensi 768, dalam batch dengan jeda dan retry (menghormati rate limit). Simpan ke `chunks.embedding`; isi `tsv` untuk pencarian kata kunci. Perhatikan batas panjang input model dan pastikan chunk di bawahnya.
6. **Ringkasan**: generate ringkasan terstruktur dan simpan di `summaries`.
7. Status berubah ke `ready`; jika gagal, `failed` + `error_message`.

## Alur chat

1. Terima pertanyaan, ambil beberapa pesan terakhir sebagai konteks.
2. **Query rewriting** (opsional): jadikan pertanyaan lanjutan mandiri.
3. **Retrieval hibrida** (`/retrieval/hybrid.py`): embed pertanyaan dengan task type `RETRIEVAL_QUERY`, ambil top-k dari vektor + top-k dari kata kunci, gabungkan dengan Reciprocal Rank Fusion.
4. **Reranking** (`/retrieval/rerank.py`): urutkan ulang kandidat; ambil 5-8 terbaik.
5. **Generasi** (`/llm/answer.py`): kirim konteks bernomor + pertanyaan ke Gemini; instruksikan sitasi `[n]` dan aturan "tidak ditemukan".
6. **Streaming** via SSE; di akhir kirim daftar sitasi (chunk_id, halaman, kutipan, bbox).
7. Simpan pesan, sitasi, token, dan latency.

## Sitasi dan highlight

Setiap chunk membawa halaman dan bbox. Frontend menerima daftar sitasi, lalu PDF viewer melompat ke halaman dan menggambar sorotan dari bbox. Validasi server-side: kutipan yang diklaim harus benar-benar ada di chunk yang dirujuk.

## Keputusan desain yang perlu dicatat

Lihat `DECISIONS.md`. Topik utama: pilihan parser, strategi chunking, model embedding, bobot hybrid search, reranker, dan format prompt.

## Deployment

- Frontend di Vercel; backend dan Postgres di Railway / Fly.io.
- Variabel lingkungan: `DATABASE_URL`, `GEMINI_API_KEY`, `JWT_SECRET`, `STORAGE_PATH`, `CORS_ORIGINS`.
- Migrasi dijalankan saat deploy (`alembic upgrade head`).
- Ingest berjalan sebagai background task; naik ke antrean (misal Redis + worker) hanya jika perlu.

## Batasan yang diketahui

- PDF hasil scan (tanpa teks) belum didukung.
- Persamaan kompleks dan tabel bisa terekstrak kurang rapi; dicatat sebagai keterbatasan dan diuji di `EVAL.md`.
