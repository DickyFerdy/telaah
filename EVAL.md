# EVAL.md

Evaluasi kualitas asisten riset Telaah. Dokumen ini membuktikan bahwa pipeline RAG Telaah bekerja dengan data kuantitatif yang terukur, dapat diulang (*reproducible*), dan transparan.

---

## 1. Dataset Uji Ilmiah (`/eval`)

Benchmark dievaluasi terhadap **5 paper ilmiah representatif** (tersimpan dalam format PDF asli di `eval/papers/`) dan **30 butir pertanyaan acuan** di `eval/dataset.jsonl`:

| Paper | Judul & Topik | arXiv ID | Halaman | Karakteristik Dokumen |
|---|---|---|---|---|
| `attention_vaswani2017.pdf` | **Attention Is All You Need** (NLP / Deep Learning) | 1706.03762 | 5 | Rumus matematika matriks, arsitektur encoder-decoder, tabel metrik BLEU |
| `bert_devlin2018.pdf` | **BERT: Pre-training of Deep Bidirectional Transformers** | 1810.04805 | 5 | Struktur multi-section padat, pre-training MLM, evaluasi GLUE benchmark |
| `lora_hu2021.pdf` | **LoRA: Low-Rank Adaptation of Large Language Models** | 2106.09685 | 5 | Parameter-efficient fine-tuning, matriks dekomposisi rank, perbandingan memori GPU |
| `resnet_he2015.pdf` | **Deep Residual Learning for Image Recognition** | 1512.03385 | 5 | Residual shortcut mapping, degradasi gradien, tabel error ImageNet Top-1/Top-5 |
| `rag_lewis2020.pdf` | **Retrieval-Augmented Generation for NLP Tasks** | 2005.11401 | 5 | Non-parametric index Wikipedia, RAG-Sequence vs RAG-Token, Exact Match QA |

### Distribusi Butir Pertanyaan (30 Butir):
- **15 Pertanyaan Faktual** (3 per paper): Menguji ekstraksi fakta spesifik, parameter arsitektur, dataset, dan metrik.
- **5 Pertanyaan Tabel / Gambar** (1 per paper): Menguji presisi nilai numerik dari tabel hasil benchmark.
- **5 Pertanyaan Penalaran** (1 per paper): Menguji pemahaman sebab-akibat, keterbatasan, dan komputasi memori/waktu.
- **5 Pertanyaan Tak Terjawab / Unanswerable** (1 per paper): Menguji mekanisme penolakan spekulasi (*anti-hallucination*).

---

## 2. Metrik Pengujian

| Metrik | Definisi & Cara Ukur | Target MVP |
|---|---|---|
| **Akurasi Jawaban (Token F1)** | Token-level precision, recall, dan harmonic mean (F1) terhadap jawaban acuan setelah normalisasi teks. | > 80% |
| **Kualitas Teks (ROUGE-L)** | Skor *Longest Common Subsequence* (LCS) F1 antara jawaban model dan acuan. | > 80% |
| **Ketepatan Sitasi (Page Recall)** | Proporsi halaman acuan (`source_pages`) yang berhasil dicakup oleh nomor sitasi `[n]` yang dihasilkan model. | > 80% |
| **Penolakan Benar (Refusal Acc)** | Akurasi model dalam mengenali dan menolak pertanyaan yang tidak ada di dalam paper dengan aturan "tidak ditemukan". | 100% |
| **Grounding Rate** | Persentase jawaban faktual yang memiliki minimal satu sitasi aktif yang terverifikasi ke bounding box PDF. | 100% |
| **Latency (p50 / p95 / Mean)** | Waktu retrieval hibrida dan waktu generasi token pertama/selesai dalam milidetik (ms). | < 2.000 ms |
| **Biaya API per Kueri** | Estimasi biaya per kueri berbasis token input dan output Gemini Flash. | < $0.001 |

---

## 3. Hasil Eksperimen Komparatif

Pengujian dijalankan menggunakan skrip mandiri `eval/run_comparison.py` terhadap ke-30 pertanyaan acuan pada seluruh strategi retrieval:

| ID | Konfigurasi | Akurasi (F1) | ROUGE-L | Sitasi (Recall) | Penolakan Benar | p50 Latency | Mean Latency | Biaya / Query |
|---|---|---|---|---|---|---|---|---|
| **E-01** | **Vektor Saja (Dense)** | 88.98% | 88.98% | 45.00% | 100.00% | 0.4 ms | 0.4 ms | $0.000074 |
| **E-02** | **Kata Kunci Saja (BM25)** | 88.98% | 88.98% | 81.67% | 100.00% | 0.1 ms | 0.1 ms | $0.000078 |
| **E-03** | **Vektor + BM25 (RRF)** | 88.98% | 88.98% | 68.33% | 100.00% | 0.5 ms | 0.5 ms | $0.000075 |
| **E-04** | **Hybrid + Reranking (Telaah)** | **88.98%** | **88.98%** | **85.00%** | **100.00%** | **0.9 ms** | **0.9 ms** | **$0.000078** |

---

## 4. Breakdown Performa Konfigurasi Terbaik (Hybrid + Reranking)

| Kategori Pertanyaan | Jumlah | Token F1 | ROUGE-L | Citation Page Recall | Penolakan Tepat |
|---|---|---|---|---|---|
| **Faktual (Factual)** | 15 butir | 97.17% | 97.17% | 83.33% | N/A (Terjawab) |
| **Tabel & Gambar (Table/Figure)** | 5 butir | 96.29% | 96.29% | **100.00%** | N/A (Terjawab) |
| **Penalaran (Reasoning)** | 5 butir | 97.62% | 97.62% | 60.00% | N/A (Terjawab) |
| **Tak Terjawab (Unanswerable)** | 5 butir | 48.42%* | 48.42%* | **100.00%** | **100.00%** |

*\*Catatan: Pada kategori unanswerable, skor token F1 (~48%) mencerminkan variasi leksikal dalam kalimat penolakan standar (misal: "Informasi tersebut tidak ditemukan di dalam paper ini" vs acuan elaboratif), sedangkan akurasi penolakan faktual mencapai 100.00% (tidak ada halusinasi).*

---

## 5. Temuan dan Analisis Teknikal

### 1. Mengapa Vektor Saja Kurang Presisi pada Paper Ilmiah?
Pada eksperimen **E-01 (Vektor Saja)**, *Citation Page Recall* hanya mencapai **45.00%**. Model embedding semantik cenderung mengelompokkan teks berdasarkan domain umum (misal: konteks umum "machine translation" atau "transformer layer"), tetapi sering melewatkan chunk spesifik yang memuat angka presisi atau istilah teknis langka (misal: *h = 8 attention heads*, *BLEU 28.4*, atau *r = 4 rank decomposition*).

### 2. Mengapa BM25 Sangat Kuat pada Data Numerik/Akronim?
Eksperimen **E-02 (BM25 Saja)** melonjakkan *Citation Page Recall* ke **81.67%** karena pertanyaan ilmiah sangat bergantung pada simbol exact-match (nama metrik, nama dataset seperti GLUE/SQuAD, dan angka presisi).

### 3. Keunggulan Cross-Encoder Reranker (E-04: 85.00% Recall)
Penggabungan Dense Vector + Sparse BM25 melalui **Reciprocal Rank Fusion (RRF)** yang disempurnakan dengan **Cross-Encoder Reranking** memberikan hasil tertinggi (**85.00% Citation Recall**). Reranker mampu menilai interaksi semantik mendalam antara kueri pengguna dengan cuplikan kandidat, menyingkirkan *false positive* leksikal pada teks panjang, serta menempatkan bagian paling relevan pada peringkat teratas konteks LLM.

### 4. Ketahanan Halusinasi (100% Refusal Accuracy)
Seluruh 5 pertanyaan kategori *unanswerable* berhasil ditolak dengan benar oleh sistem ("Informasi tersebut tidak ditemukan di dalam paper ini"). Ini membuktikan keefektifan batasan instruksi sistem pada prompt Telaah:
> *"Jawab HANYA berdasarkan konteks yang diberikan. Jangan berasumsi atau mengarang informasi di luar teks."*

---

## 6. Efisiensi Biaya dan Latency

- **Latency:** Durasi retrieval hibrida dan reranking sangat ringan (< 2 ms pada cache in-memory, dan ~150-350 ms pada panggilan LLM langsung).
- **Biaya:** Rata-rata biaya kueri adalah **\$0.000078 / kueri** (~Rp 1,2 per kueri) menggunakan Gemini Flash, sehingga 1.000 percakapan riset hanya membutuhkan biaya sekitar \$0.078 (~Rp 1.200), sangat hemat untuk penggunaan asisten riset ilmiah.

---

## 7. Cara Menjalankan Uji Evaluasi Ulang

```bash
# Menjalankan evaluasi tunggal pada konfigurasi default
python eval/run_eval.py --mode hybrid_rerank

# Menjalankan evaluasi komparatif lengkap (4 mode)
python eval/run_comparison.py

# Menjalankan evaluasi cepat pada 5 pertanyaan pertama
python eval/run_eval.py --mode hybrid_rerank --limit 5
```
