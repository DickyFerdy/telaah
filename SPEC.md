# SPEC.md

## 1. Tujuan

Membantu mahasiswa dan peneliti memahami sebuah paper lebih cepat: bertanya dalam bahasa alami (Indonesia atau Inggris), mendapat jawaban yang bisa diverifikasi lewat sitasi ke teks asli, dan melihat ringkasan terstruktur.

## 2. Pengguna

- Mahasiswa yang membaca paper berbahasa Inggris dan butuh penjelasan dalam bahasa Indonesia.
- Peneliti yang ingin cepat mengekstrak metode, dataset, dan hasil utama.

## 3. Scope

### Termasuk (MVP)

- Registrasi dan login
- Upload PDF (dan impor via link arXiv)
- Parsing sadar struktur: abstrak, metode, hasil, diskusi, referensi
- Tanya jawab dengan streaming dan sitasi yang menyorot teks di PDF
- Mode "tidak ditemukan di paper"
- Ringkasan terstruktur otomatis
- Riwayat percakapan per paper
- Halaman evaluasi (akurasi, ketepatan sitasi, latency, biaya)

### Tidak termasuk (untuk sekarang)

- Koleksi multi-paper dan perbandingan antar paper
- Draft tinjauan pustaka
- Peta referensi dan impor otomatis paper yang dikutip
- Kolaborasi antar pengguna
- Aplikasi mobile
- OCR untuk PDF hasil scan (dicatat sebagai batasan)

### Fase berikutnya

Multi-paper, perbandingan metode, ekspor catatan ke Markdown / BibTeX.

## 4. User flow

1. Pengguna daftar / login.
2. Upload PDF atau tempel link arXiv.
3. Sistem memproses (status: `uploaded` → `parsing` → `embedding` → `ready` / `failed`).
4. Setelah `ready`, pengguna melihat PDF di kiri dan panel chat + ringkasan di kanan.
5. Pengguna bertanya; jawaban mengalir (streaming) dengan penanda sitasi `[1]`, `[2]`.
6. Klik sitasi: PDF melompat ke halaman dan menyorot teks sumber.
7. Jika info tidak ada di paper, AI menjawab bahwa informasinya tidak ditemukan.

## 5. Fitur dan kriteria penerimaan

| Fitur | Kriteria penerimaan |
|---|---|
| Upload PDF | Hanya PDF ≤ 20 MB; error jelas jika gagal; status proses terlihat |
| Parsing struktur | Minimal bagian abstrak, metode, hasil, referensi terdeteksi pada 8 dari 10 paper uji |
| Chat + streaming | Token pertama tampil < 3 detik pada kondisi normal |
| Sitasi | Setiap klaim faktual menyertakan ≥ 1 sitasi; klik membuka halaman yang benar |
| Tidak ditemukan | Untuk pertanyaan di luar isi paper, AI menolak menjawab dengan spekulasi |
| Ringkasan terstruktur | Berisi: pertanyaan penelitian, metode, dataset, metrik, hasil utama, keterbatasan |
| Riwayat | Percakapan tersimpan dan bisa dibuka lagi |
| Evaluasi | Skrip menghasilkan laporan akurasi, ketepatan sitasi, latency, biaya |

## 6. Skema database (draft)

```sql
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE users (
  id UUID PRIMARY KEY,
  email TEXT UNIQUE NOT NULL,
  password_hash TEXT,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE papers (
  id UUID PRIMARY KEY,
  user_id UUID REFERENCES users(id) ON DELETE CASCADE,
  title TEXT,
  authors TEXT[],
  source_type TEXT,            -- 'upload' | 'arxiv'
  source_ref TEXT,             -- nama file atau arXiv id
  file_path TEXT NOT NULL,
  status TEXT NOT NULL,        -- uploaded | parsing | embedding | ready | failed
  error_message TEXT,
  page_count INT,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE chunks (
  id UUID PRIMARY KEY,
  paper_id UUID REFERENCES papers(id) ON DELETE CASCADE,
  section TEXT,                -- abstract | method | results | discussion | references | other
  page_start INT,
  page_end INT,
  text TEXT NOT NULL,
  bbox JSONB,                  -- koordinat untuk highlight di PDF
  embedding VECTOR(768),       -- harus sama dengan outputDimensionality Gemini (768 / 1536 / 3072)
  tsv TSVECTOR,                -- untuk pencarian kata kunci
  token_count INT
);
CREATE INDEX ON chunks USING hnsw (embedding vector_cosine_ops);
CREATE INDEX ON chunks USING gin (tsv);

CREATE TABLE conversations (
  id UUID PRIMARY KEY,
  paper_id UUID REFERENCES papers(id) ON DELETE CASCADE,
  user_id UUID REFERENCES users(id) ON DELETE CASCADE,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE messages (
  id UUID PRIMARY KEY,
  conversation_id UUID REFERENCES conversations(id) ON DELETE CASCADE,
  role TEXT NOT NULL,          -- user | assistant
  content TEXT NOT NULL,
  citations JSONB,             -- [{chunk_id, page, quote}]
  input_tokens INT,
  output_tokens INT,
  latency_ms INT,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE summaries (
  id UUID PRIMARY KEY,
  paper_id UUID UNIQUE REFERENCES papers(id) ON DELETE CASCADE,
  content JSONB NOT NULL,      -- {research_question, method, dataset, metrics, results, limitations}
  prompt_version TEXT,
  created_at TIMESTAMPTZ DEFAULT now()
);
```

## 7. API (draft)

| Method | Path | Fungsi |
|---|---|---|
| POST | `/auth/register` | Daftar |
| POST | `/auth/login` | Login, kembalikan token |
| POST | `/papers` | Upload PDF |
| POST | `/papers/arxiv` | Impor dari link / id arXiv |
| GET | `/papers` | Daftar paper milik pengguna |
| GET | `/papers/{id}` | Detail + status proses |
| GET | `/papers/{id}/file` | Unduh / tampilkan PDF |
| DELETE | `/papers/{id}` | Hapus paper dan datanya |
| POST | `/papers/{id}/chat` | Kirim pertanyaan, respons SSE |
| GET | `/papers/{id}/conversations` | Riwayat percakapan |
| GET | `/papers/{id}/summary` | Ambil ringkasan terstruktur |
| POST | `/papers/{id}/summary/regenerate` | Buat ulang ringkasan |

## 8. Non-fungsional

- Keamanan: autentikasi, isolasi data per pengguna, validasi upload, rate limit.
- Biaya: catat token dan biaya per query; batasi panjang konteks.
- Rate limit API: ingest harus tahan terhadap limit tier gratis Gemini (batching, jeda, retry dengan backoff) dan menampilkan progres ke pengguna.
- Performa: ingest paper 15 halaman < 60 detik.
- Observabilitas: log terstruktur untuk waktu ingest, retrieval, dan generasi.

## 9. Definisi selesai (MVP)

- [ ] Semua fitur MVP lolos kriteria penerimaan
- [ ] Ter-deploy dan bisa diakses publik
- [ ] Ada akun demo dan 2-3 paper contoh
- [ ] Laporan evaluasi tersedia di `EVAL.md`
- [ ] README lengkap dengan demo, diagram, dan hasil evaluasi
