"""
Unit test untuk dataset evaluasi di /eval.
Memvalidasi kelengkapan 5 paper, 30 butir pertanyaan uji,
serta format dan konsistensi skema dataset.jsonl.
"""

import json
from collections import Counter
from pathlib import Path

import pymupdf

EVAL_DIR = Path(__file__).resolve().parent.parent.parent / "eval"
DATASET_PATH = EVAL_DIR / "dataset.jsonl"
METADATA_PATH = EVAL_DIR / "papers_metadata.json"
PAPERS_DIR = EVAL_DIR / "papers"


def test_eval_files_exist():
    assert DATASET_PATH.exists(), f"File {DATASET_PATH} tidak ditemukan"
    assert METADATA_PATH.exists(), f"File {METADATA_PATH} tidak ditemukan"
    assert PAPERS_DIR.is_dir(), f"Folder {PAPERS_DIR} tidak ditemukan"


def test_metadata_consistency():
    with open(METADATA_PATH, encoding="utf-8") as f:
        metadata = json.load(f)

    assert isinstance(metadata, dict)
    assert len(metadata) == 5, f"Jumlah paper di metadata harus 5, ditemukan {len(metadata)}"

    for filename, item in metadata.items():
        assert "title" in item
        assert "authors" in item
        assert "arxiv_id" in item
        assert "domain" in item
        assert "character" in item
        assert "page_count" in item

        pdf_path = PAPERS_DIR / filename
        assert pdf_path.exists(), f"File PDF {filename} tidak ada di {PAPERS_DIR}"

        doc = pymupdf.open(str(pdf_path))
        assert len(doc) >= 4, f"Halaman paper {filename} kurang dari 4"
        assert len(doc) == item["page_count"]
        doc.close()


def test_dataset_jsonl_structure_and_categories():
    assert DATASET_PATH.exists()
    records = []
    with open(DATASET_PATH, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))

    assert len(records) == 30, f"Jumlah pertanyaan harus tepat 30, ditemukan {len(records)}"

    categories = Counter(r["category"] for r in records)
    assert categories["factual"] == 15, f"Kategori factual harus 15, dapat {categories['factual']}"
    assert categories["table_figure"] == 5, f"Kategori table_figure harus 5, dapat {categories['table_figure']}"
    assert categories["reasoning"] == 5, f"Kategori reasoning harus 5, dapat {categories['reasoning']}"
    assert categories["unanswerable"] == 5, f"Kategori unanswerable harus 5, dapat {categories['unanswerable']}"

    # Cek sebaran paper: 5 paper masing-masing punya 6 pertanyaan (3 factual + 1 table_figure + 1 reasoning + 1 unanswerable)
    by_paper = Counter(r["paper"] for r in records)
    assert len(by_paper) == 5, f"Harus ada 5 paper berbeda, ditemukan {len(by_paper)}"
    for paper_file, count in by_paper.items():
        assert count == 6, f"Paper {paper_file} harus memiliki 6 pertanyaan uji, ditemukan {count}"
        pdf_path = PAPERS_DIR / paper_file
        assert pdf_path.exists(), f"Paper {paper_file} tidak ditemukan di {PAPERS_DIR}"

    # Cek skema setiap record
    required_fields = {
        "id",
        "paper",
        "category",
        "question",
        "reference_answer",
        "source_pages",
        "should_refuse",
    }
    for rec in records:
        assert required_fields.issubset(rec.keys()), f"Field hilang di record {rec.get('id')}"
        assert isinstance(rec["source_pages"], list)
        assert isinstance(rec["should_refuse"], bool)

        if rec["should_refuse"]:
            assert rec["category"] == "unanswerable"
            assert len(rec["source_pages"]) == 0
        else:
            assert len(rec["source_pages"]) > 0
            assert len(rec["reference_answer"]) > 10
