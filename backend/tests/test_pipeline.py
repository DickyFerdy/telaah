import uuid
from pathlib import Path
from unittest.mock import AsyncMock

import pymupdf
import pytest
from app.db.models import Paper
from app.ingest.pipeline import run_ingest_pipeline


@pytest.fixture
def test_pdf_file(tmp_path: Path) -> Path:
    pdf_path = tmp_path / "pipeline_test.pdf"
    doc = pymupdf.open()
    p1 = doc.new_page(width=595, height=842)
    p1.insert_text((50, 100), "Title of Pipeline Paper", fontsize=14)
    p1.insert_text((50, 150), "Abstract\nThis tests the end-to-end ingestion pipeline.", fontsize=11)
    p1.insert_text((50, 200), "1. Introduction\nIntroduction details for testing.", fontsize=11)
    doc.save(str(pdf_path))
    doc.close()
    return pdf_path


@pytest.mark.asyncio
async def test_run_ingest_pipeline_success(test_pdf_file: Path) -> None:
    paper_id = uuid.uuid4()
    mock_paper = Paper(
        id=paper_id,
        user_id=uuid.uuid4(),
        file_path=str(test_pdf_file),
        status="uploaded",
        source_type="upload",
    )

    # Buat mock database session
    mock_db = AsyncMock()
    mock_db.add = lambda obj: None
    mock_db.scalar = AsyncMock(return_value=mock_paper)

    await run_ingest_pipeline(paper_id=paper_id, session=mock_db)

    # Verifikasi status akhir berubah menjadi ready
    assert mock_paper.status == "ready"
    assert mock_paper.page_count == 1
    assert mock_paper.error_message is None
    # Verifikasi db.commit dipanggil
    assert mock_db.commit.called


@pytest.mark.asyncio
async def test_run_ingest_pipeline_error_handling(tmp_path: Path) -> None:
    paper_id = uuid.uuid4()
    # Path file tidak ada
    nonexistent_file = tmp_path / "not_found.pdf"
    mock_paper = Paper(
        id=paper_id,
        user_id=uuid.uuid4(),
        file_path=str(nonexistent_file),
        status="uploaded",
        source_type="upload",
    )

    mock_db = AsyncMock()
    mock_db.scalar = AsyncMock(return_value=mock_paper)

    await run_ingest_pipeline(paper_id=paper_id, session=mock_db)

    # Verifikasi status berubah menjadi failed dan mencatat error_message
    assert mock_paper.status == "failed"
    assert mock_paper.error_message is not None
    assert "tidak ditemukan" in mock_paper.error_message.lower()
