# EVAL.md

Evaluasi kualitas asisten riset. Tujuannya membuktikan sistem bekerja dengan angka, bukan hanya "terlihat jalan".

## Dataset uji

- 5 paper dengan karakter berbeda (misal: ML, medis, sosial, paper dua kolom padat tabel, paper dengan banyak persamaan).
- 30 pertanyaan total, dengan komposisi:
  - 15 pertanyaan faktual (metode, dataset, angka hasil)
  - 5 pertanyaan tabel / gambar
  - 5 pertanyaan penalaran ringan (perbandingan, keterbatasan)
  - 5 pertanyaan **tidak terjawab** oleh paper (untuk menguji mode "tidak ditemukan")
- Setiap pertanyaan punya: jawaban acuan, halaman sumber, dan label kategori.

Format file (`/eval/dataset.jsonl`):

```json
{"id": "q001", "paper": "paper1.pdf", "question": "...", "reference_answer": "...", "source_pages": [4], "category": "factual"}
```

## Metrik

| Metrik | Cara ukur |
|---|---|
| Akurasi jawaban | Skor 0 / 0.5 / 1 terhadap jawaban acuan (penilaian manual atau LLM-as-judge yang divalidasi manual pada sampel) |
| Ketepatan sitasi | Persentase sitasi yang halamannya cocok dengan `source_pages` |
| Recall retrieval | Apakah chunk sumber masuk top-k |
| Penolakan benar | Persentase pertanyaan tak terjawab yang ditolak dengan benar |
| Halusinasi | Jumlah klaim yang tidak didukung konteks |
| Latency | Token pertama dan total (p50, p95) |
| Biaya | Rata-rata token dan biaya per query |

## Eksperimen

| ID | Konfigurasi | Akurasi | Sitasi | Recall@k | Penolakan | p50 latency | Biaya/query | Catatan |
|---|---|---|---|---|---|---|---|---|
| E-01 | Vektor saja | | | | | | | baseline |
| E-02 | Vektor + kata kunci (RRF) | | | | | | | |
| E-03 | E-02 + reranking | | | | | | | |
| E-04 | E-03 + chunking per bagian | | | | | | | |

## Temuan dan analisis

_Isi setelah eksperimen: kategori pertanyaan mana yang paling sering gagal, penyebabnya (parsing, retrieval, atau prompt), dan perbaikan yang dicoba._

## Keterbatasan yang diketahui

_Contoh: persamaan, tabel kompleks, PDF scan._
