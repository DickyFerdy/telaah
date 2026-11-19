from pathlib import Path

import pymupdf
import pytest
from app.ingest.parser import parse_pdf


@pytest.fixture
def sample_pdf(tmp_path: Path) -> Path:
    """Buat file PDF 2 halaman dengan PyMuPDF untuk pengujian."""
    pdf_path = tmp_path / "test_sample.pdf"
    doc = pymupdf.open()

    # Halaman 1
    page1 = doc.new_page(width=595.0, height=842.0)  # A4
    page1.insert_text(
        pymupdf.Point(50, 100),
        "Judul Paper Ilmiah: Evaluasi RAG",
        fontsize=16,
    )
    page1.insert_text(
        pymupdf.Point(50, 150),
        "Abstrak\nPenelitian ini mengevaluasi kinerja retrieval berbasis sitasi.",
        fontsize=11,
    )

    # Halaman 2
    page2 = doc.new_page(width=595.0, height=842.0)
    page2.insert_text(
        pymupdf.Point(50, 100),
        "Metode Penelitian\nKami menggunakan PyMuPDF untuk ekstraksi bounding box.",
        fontsize=11,
    )

    doc.save(str(pdf_path))
    doc.close()
    return pdf_path


def test_parse_pdf_success(sample_pdf: Path) -> None:
    parsed = parse_pdf(sample_pdf)

    # 1. Verifikasi jumlah halaman
    assert parsed.total_pages == 2
    assert len(parsed.pages) == 2

    # 2. Verifikasi halaman 1
    p1 = parsed.pages[0]
    assert p1.page_number == 1
    assert p1.width == 595.0
    assert p1.height == 842.0
    assert "Evaluasi RAG" in p1.text
    assert "Abstrak" in p1.text

    # Verifikasi bounding box halaman 1
    assert len(p1.blocks) >= 2
    for b in p1.blocks:
        x0, y0, x1, y1 = b.bbox
        assert x0 < x1, "Koordinat x0 harus lebih kecil dari x1"
        assert y0 < y1, "Koordinat y0 harus lebih kecil dari y1"
        assert len(b.text) > 0

    # 3. Verifikasi halaman 2
    p2 = parsed.pages[1]
    assert p2.page_number == 2
    assert "Metode Penelitian" in p2.text
    assert len(p2.blocks) >= 1


def test_parse_pdf_nonexistent_file(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        parse_pdf(tmp_path / "tidak_ada.pdf")


def test_parse_pdf_invalid_file(tmp_path: Path) -> None:
    corrupt_file = tmp_path / "corrupt.pdf"
    corrupt_file.write_bytes(b"Bukan konten PDF")
    with pytest.raises(ValueError, match="Gagal membuka dokumen PDF"):
        parse_pdf(corrupt_file)
