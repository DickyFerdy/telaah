import uuid

import pytest
from sqlalchemy import func

from app.ingest.chunker import DocumentChunk
from app.ingest.storage import save_chunks_to_db


def test_chunk_tsv_expression_construction() -> None:
    """Memvalidasi pembuatan ekspresi to_tsvector untuk kolom tsv."""
    sample_text = (
        "We evaluate hybrid retrieval combining dense embeddings and sparse BM25."
    )
    tsv_expr = func.to_tsvector("english", sample_text)

    # Memastikan objek ekspresi fungsi SQL terkonstruksi dengan benar
    assert tsv_expr.name == "to_tsvector"
    args = [arg.value for arg in tsv_expr.clauses]
    assert args == ["english", sample_text]


@pytest.mark.asyncio
async def test_save_chunks_mismatched_lengths() -> None:
    """Memvalidasi proteksi error saat jumlah chunks tidak sama dengan embeddings."""
    paper_id = uuid.uuid4()
    chunks = [
        DocumentChunk(
            chunk_index=0,
            section="abstract",
            text="sample text",
            page_start=1,
            page_end=1,
            bbox={},
            token_count=2,
        )
    ]
    embeddings: list[list[float]] = []  # Kosong (mismatch)

    with pytest.raises(
        ValueError, match="Jumlah chunks .* dan embeddings .* harus sama"
    ):
        await save_chunks_to_db(paper_id, chunks, embeddings, db=None)  # type: ignore
