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
- Status: diusulkan
- Opsi: PyMuPDF, Marker, GROBID
- Bukti: _isi hasil perbandingan pada 10 paper (struktur, tabel, persamaan, kecepatan)_

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
- Status: diusulkan
- Bukti: _isi tabel baseline vs hybrid vs hybrid + rerank dari `EVAL.md`_

## D-007: Model generasi (Gemini)
- Status: diusulkan
- Konteks: jawaban harus patuh pada konteks, menyertakan sitasi `[n]`, dan menolak saat info tidak ada.
- Keputusan sementara: pakai model Gemini dari satu penyedia yang sama dengan embedding. Nama model final dicek di dokumentasi resmi.
- Bukti: _isi perbandingan akurasi, sitasi, penolakan, latency, dan biaya dari `EVAL.md`; catat penyesuaian prompt di `PROMPTS.md`_
- Konsekuensi: prompt perlu diuji ulang jika model diganti.
