# TASKS.md

Kerjakan dari atas ke bawah, satu item per sesi. Centang setelah test lolos dan sudah di-commit.

## Fase 0: Setup

- [x] Inisialisasi repo, struktur folder, `.gitignore`, `.env.example`
- [ ] Setup backend FastAPI + endpoint `/health`
- [ ] Setup frontend Next.js + Tailwind
- [ ] Docker Compose untuk Postgres + pgvector
- [ ] Setup Alembic + migrasi pertama (skema dari `SPEC.md`)
- [ ] CI sederhana (lint + test) di GitHub Actions

## Fase 1: Auth dan upload

- [ ] Register / login (JWT) + test
- [ ] Halaman login dan register
- [ ] Endpoint upload PDF dengan validasi (tipe, ukuran, magic bytes)
- [ ] Halaman daftar paper + status proses
- [ ] Impor via link arXiv
- [ ] Hapus paper beserta datanya

## Fase 2: Pipeline ingest

- [ ] Parser PDF dasar (teks per halaman + bbox) dengan PyMuPDF
- [ ] Deteksi bagian (abstrak, metode, hasil, diskusi, referensi)
- [ ] Chunking sadar bagian + test
- [ ] Embedding batch + simpan ke pgvector
- [ ] Isi kolom `tsv` untuk pencarian kata kunci
- [ ] Background task ingest + update status + penanganan error
- [ ] Bandingkan parser lain (Marker / GROBID), catat di `DECISIONS.md`

## Fase 3: Tanya jawab

- [ ] Retrieval vektor sederhana
- [ ] Tambah pencarian kata kunci + Reciprocal Rank Fusion
- [ ] Reranking
- [ ] Prompt v1 + endpoint chat dengan SSE
- [ ] Sitasi bernomor + validasi kutipan server-side
- [ ] Mode "tidak ditemukan di paper"
- [ ] UI chat dengan streaming
- [ ] PDF viewer + lompat ke halaman dan sorot teks dari sitasi
- [ ] Riwayat percakapan

## Fase 4: Ringkasan terstruktur

- [ ] Prompt ringkasan terstruktur (JSON) + simpan di `summaries`
- [ ] Kartu ringkasan di UI + tombol buat ulang
- [ ] Penjelasan istilah dari teks yang diblok (opsional)

## Fase 5: Evaluasi

- [ ] Kumpulkan 5 paper dan tulis 30 pertanyaan uji + jawaban acuan di `/eval`
- [ ] Skrip evaluasi: akurasi jawaban, ketepatan sitasi, latency, biaya
- [ ] Jalankan baseline vs hybrid vs hybrid + rerank, catat hasil di `EVAL.md`
- [ ] Halaman evaluasi sederhana di aplikasi (opsional)

## Fase 6: Hardening dan deploy

- [ ] Rate limit endpoint chat dan upload
- [ ] Review keamanan (akses lintas pengguna, validasi, rahasia)
- [ ] Deploy backend + database
- [ ] Deploy frontend
- [ ] Akun demo + paper contoh
- [ ] Tulis README akhir (demo, screenshot, diagram, hasil evaluasi)

## Backlog (fase berikutnya)

- [ ] Koleksi multi-paper
- [ ] Tabel perbandingan beberapa paper
- [ ] Peta referensi
- [ ] Ekspor catatan ke Markdown / BibTeX
- [ ] Dukungan PDF hasil scan (OCR)
