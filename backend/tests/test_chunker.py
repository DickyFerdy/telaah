from app.ingest.chunker import (
    chunk_document_sections,
    estimate_token_count,
    split_text_into_sentences,
)
from app.ingest.parser import TextBlock
from app.ingest.sections import SectionBlock, SectionSegment, SectionType


def test_split_text_into_sentences() -> None:
    text = "First sentence here. Second sentence follows! Is this the third sentence? Yes it is."
    sentences = split_text_into_sentences(text)
    assert len(sentences) == 4
    assert sentences[0] == "First sentence here."
    assert sentences[1] == "Second sentence follows!"
    assert sentences[2] == "Is this the third sentence?"
    assert sentences[3] == "Yes it is."


def test_estimate_token_count() -> None:
    text = "Artificial intelligence and scientific paper analysis."
    tokens = estimate_token_count(text)
    assert tokens > 0
    assert tokens >= len(text.split())


def test_chunk_document_sections_preserves_boundaries() -> None:
    # Buat 2 section berbeda: Abstract dan Methodology
    abstract_block = SectionBlock(
        section=SectionType.ABSTRACT,
        page_number=1,
        block=TextBlock(
            text="This is the abstract content of the paper.",
            bbox=(50, 100, 400, 150),
            block_no=0,
        ),
    )
    method_block = SectionBlock(
        section=SectionType.METHODOLOGY,
        page_number=2,
        block=TextBlock(
            text="This is the methodology content describing our algorithm.",
            bbox=(50, 120, 400, 180),
            block_no=1,
        ),
    )

    segments = [
        SectionSegment(
            section=SectionType.ABSTRACT,
            title="Abstract",
            blocks=[abstract_block],
        ),
        SectionSegment(
            section=SectionType.METHODOLOGY,
            title="Methodology",
            blocks=[method_block],
        ),
    ]

    chunks = chunk_document_sections(segments)

    # Harus ada tepat 2 chunk terpisah karena section berbeda
    assert len(chunks) == 2
    assert chunks[0].section == "abstract"
    assert "abstract content" in chunks[0].text
    assert chunks[0].page_start == 1
    assert chunks[0].page_end == 1
    assert "boxes" in chunks[0].bbox
    assert chunks[0].bbox["bounds"] == [50.0, 100.0, 400.0, 150.0]

    assert chunks[1].section == "methodology"
    assert "methodology content" in chunks[1].text
    assert chunks[1].page_start == 2
    assert chunks[1].page_end == 2


def test_chunk_document_sections_splits_long_block() -> None:
    # Satu blok teks sangat panjang melampaui max_chars
    long_sentences = [
        f"This is sentence number {i} containing important scientific findings and discussion details."
        for i in range(30)
    ]
    long_text = " ".join(long_sentences)

    block = SectionBlock(
        section=SectionType.EXPERIMENTS_RESULTS,
        page_number=3,
        block=TextBlock(
            text=long_text,
            bbox=(50, 50, 500, 600),
            block_no=0,
        ),
    )
    segment = SectionSegment(
        section=SectionType.EXPERIMENTS_RESULTS,
        title="Results",
        blocks=[block],
    )

    chunks = chunk_document_sections([segment], target_chars=500, max_chars=800)

    # Panjang teks ~2700 chars dengan target 500 chars -> terpecah menjadi beberapa chunk
    assert len(chunks) > 1
    for c in chunks:
        assert c.section == "experiments_results"
        assert c.page_start == 3
        assert c.page_end == 3
        assert len(c.text) > 0
