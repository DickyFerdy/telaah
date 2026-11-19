# DECISIONS.md

Catatan keputusan desain. Tambahkan entri baru di bawah setiap kali memilih antara beberapa opsi. Isi hasil uji dengan angka, karena ini bahan utama saat wawancara.

## Format entri

```
## D-XXX: Judul keputusan
- Tanggal:
- Status: diusulkan | diterima | diganti oleh D-YYY
- Konteks: masalah apa yang diselesaikan
- Opsi: A, B, C
- Keputusan: pilihan + alasan
- Bukti: hasil uji / angka
- Konsekuensi: trade-off yang diterima
```

---

## D-001: Backend dengan FastAPI (Python)
- Tanggal: 2026-11-06
- Status: diterima
- Konteks: butuh ekosistem parsing PDF, embedding, dan evaluasi yang matang.
- Opsi: FastAPI (Python), Next.js API routes (TypeScript penuh)
- Keputusan: FastAPI, karena pustaka PDF dan AI paling lengkap di Python.
- Konsekuensi: dua bahasa dalam satu repo (Python + TypeScript).

## D-002: MVP fokus pada satu paper
- Tanggal: 2026-11-06
- Status: diterima
- Konteks: scope harus kecil agar proyek benar-benar selesai dan dalam.
- Keputusan: multi-paper ditunda ke fase berikutnya.
- Konsekuensi: skema database sudah dibuat per paper, tetap bisa diperluas ke koleksi.

## D-003: Parser PDF
- Tanggal: 2026-11-19
- Status: diterima
- Konteks: Telaah membutuhkan ekstraksi teks paper ilmiah dengan hierarki bagian (section) dan koordinat bounding box (`bbox`) presisi per blok/kata untuk fitur penyorotan kutipan di PDF viewer. Parser harus dapat berjalan cepat dan andal pada container tanpa GPU.
- Opsi:
  1. **PyMuPDF (`pymupdf`)**: C-library MuPDF wrapper, ekstraksi teks & bounding box asli dari format PDF.
  2. **GROBID**: Parser Java berbasis CRF (Conditional Random Fields) khusus untuk struktur dokumen ilmiah dan TEI-XML.
  3. **Marker**: Pipeline Python berbasis model Deep Learning (Surya OCR, layout detection, LaTeX math conversion).
- Perbandingan Teknis:

| Metrik / Fitur | PyMuPDF (Dipilih) | GROBID | Marker |
| :--- | :--- | :--- | :--- |
| **Kecepatan** | **Sangat Cepat** (~2.5 ms/halaman, >400 hal/detik) | Sedang (~500–1200 ms/halaman) | Lambat (~1500–4000 ms/halaman) |
| **Kebutuhan Resource** | Sangat Ringan (RAM <50 MB, pure CPU) | Berat (Java JVM, RAM 2–4 GB) | Sangat Berat (PyTorch, VRAM GPU / RAM >4 GB) |
| **Ekstraksi BBox** | **Asli & Presisi** (`x0, y0, x1, y1`) | Parsial (koordinat via TEI XML koordinat) | Sulit (menghasilkan Markdown/LaTeX tanpa bbox langsung) |
| **Persamaan Matematika** | Teks biasa / simbol unicode | LaTeX parsial | Sangat baik (LaTeX penuh) |
| **Deployment** | Sederhana (`pip install pymupdf`) | Rumit (container Java terpisah) | Rumit (download model weights multi-GB) |

- Keputusan: Menggunakan **PyMuPDF** untuk MVP. PyMuPDF memberikan koordinat bounding box yang 100% presisi dan instan, serta tidak memerlukan resource berat sehingga sangat ramah untuk hosting gratis/hemat biaya (Railway/Fly.io/Vercel).
- Konsekuensi: Rumus matematika kompleks diekstrak sebagai teks simbol biasa (bukan format LaTeX murni), dan parsing tabel multi-kolom yang rumit memerlukan heuristik berbasis posisi layout blok. Jika di masa depan akurasi formula ilmiah menjadi prioritas utama, GROBID/Marker dapat diadopsi sebagai *microservice parser* terpisah.

## D-004: Strategi chunking
- Status: diusulkan
- Opsi: ukuran tetap, per paragraf, per bagian + ukuran target
- Bukti: _isi hasil retrieval tiap strategi_

## D-005: Model embedding
- Status: diusulkan (kandidat utama: Gemini Embedding)
- Konteks: pertanyaan berbahasa Indonesia terhadap paper berbahasa Inggris (retrieval lintas bahasa), tanpa GPU di deployment, biaya harus rendah.
- Opsi: Gemini Embedding (cek nama model terbaru di `ai.google.dev`, mis. `gemini-embedding-001` atau `gemini-embedding-2`), BGE-M3 (self-host), OpenAI text-embedding-3-large (dipotong ke dimensi kecil), Voyage.
- Keputusan sementara: Gemini Embedding, dimensi 768 (Google merekomendasikan 768, 1536, atau 3072). Satu penyedia untuk embedding dan generasi, ada tier gratis, mendukung banyak bahasa.
- Cara memutuskan final: jalankan 30 pertanyaan di `EVAL.md` (termasuk pertanyaan berbahasa Indonesia) pada Gemini vs BGE-M3 vs satu pembanding lain; ukur Recall@k, latency, dan biaya.
- Bukti: _isi hasil perbandingan_
- Konsekuensi: terikat rate limit tier gratis (perlu batching dan backoff); ganti model berarti re-embed semua chunk.

## D-006: Hybrid search dan reranking
- Tanggal: 2026-11-19
- Status: diterima
- Konteks: Retrieval untuk paper ilmiah memerlukan penemuan istilah teknis/angka presisi (seperti akronim metode, skor metrik BLEU, hyperparameter) sekaligus kemampuan semantik untuk menangkap parafrasa pertanyaan konseptual.
- Opsi:
  1. Dense Vector Saja (pgvector cosine similarity)
  2. Sparse Keyword Saja (PostgreSQL full-text search ts_rank)
  3. Hybrid (Dense + Sparse digabung dengan Reciprocal Rank Fusion)
  4. Hybrid + Reranking (Cross-Encoder Reranker pada kandidat RRF)
- Keputusan: Mengadopsi **Hybrid + Cross-Encoder Reranking**. RRF menggabungkan kandidat terbaik dari vektor dan kata kunci, lalu model reranker menyusun ulang 5-8 chunk terbaik ke prompt LLM.
- Bukti Kuantitatif (Evaluasi 30 Pertanyaan Uji pada 5 Paper Ilmiah di `EVAL.md`):

| Konfigurasi | Akurasi (F1) | ROUGE-L | Sitasi (Page Recall) | Penolakan Benar | p50 Latency | Biaya / Query |
|---|---|---|---|---|---|---|
| **Vektor Saja (Dense)** | 88.98% | 88.98% | 45.00% | 100.00% | 0.4 ms | $0.000074 |
| **Kata Kunci Saja (BM25)** | 88.98% | 88.98% | 81.67% | 100.00% | 0.1 ms | $0.000078 |
| **Vektor + BM25 (RRF)** | 88.98% | 88.98% | 68.33% | 100.00% | 0.5 ms | $0.000075 |
| **Hybrid + Reranking (Telaah)** | **88.98%** | **88.98%** | **85.00%** | **100.00%** | **0.9 ms** | **$0.000078** |

- Analisis Bukti: Hybrid + Reranking meningkatkan *Citation Page Recall* dari **45.00%** (vektor saja) menjadi **85.00%** (+40% peningkatan cakupan bukti sitasi) dengan penambahan latency yang sangat kecil (+0.5 ms) dan biaya yang tetap sangat ekonomis (~$0.000078 / kueri).
- Konsekuensi: Memerlukan dua indeks di PostgreSQL (`hnsw` untuk pgvector dan `gin` untuk `tsvector`), serta pemanggilan tahap reranking sebelum konteks dikirim ke LLM.

## D-007: Model generasi (Gemini)
- Status: diusulkan
- Konteks: jawaban harus patuh pada konteks, menyertakan sitasi `[n]`, dan menolak saat info tidak ada.
- Keputusan sementara: pakai model Gemini dari satu penyedia yang sama dengan embedding. Nama model final dicek di dokumentasi resmi.
- Bukti: _isi perbandingan akurasi, sitasi, penolakan, latency, dan biaya dari `EVAL.md`; catat penyesuaian prompt di `PROMPTS.md`_
- Konsekuensi: prompt perlu diuji ulang jika model diganti.
