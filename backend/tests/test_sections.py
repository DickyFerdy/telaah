import pytest
from app.ingest.parser import PageData, ParsedDocument, TextBlock
from app.ingest.sections import (
    SectionType,
    identify_document_sections,
    match_section_heading,
)


@pytest.mark.parametrize(
    "heading_text,expected_section",
    [
        ("Abstract", SectionType.ABSTRACT),
        ("ABSTRACT", SectionType.ABSTRACT),
        ("1. Introduction", SectionType.INTRODUCTION),
        ("I. INTRODUCTION", SectionType.INTRODUCTION),
        ("2. Related Work", SectionType.RELATED_WORK),
        ("3. Methodology and Architecture", SectionType.METHODOLOGY),
        ("III. MATERIALS AND METHODS", SectionType.METHODOLOGY),
        ("4. Experimental Results and Analysis", SectionType.EXPERIMENTS_RESULTS),
        ("5. Discussion", SectionType.DISCUSSION),
        ("6. Conclusions", SectionType.CONCLUSION),
        ("References", SectionType.REFERENCES),
        ("REFERENCES", SectionType.REFERENCES),
        ("Appendix A: Proofs", SectionType.APPENDIX),
    ],
)
def test_match_section_heading_valid(
    heading_text: str, expected_section: SectionType
) -> None:
    assert match_section_heading(heading_text) == expected_section


def test_match_section_heading_paragraph_not_matched() -> None:
    # Paragraf biasa yang kebetulan mengandung kata "introduction" tidak boleh dianggap heading
    paragraph = (
        "In this paper, we provide an extensive introduction to the field "
        "of large language models and their application in scientific research."
    )
    assert match_section_heading(paragraph) is None


def test_identify_document_sections_flow() -> None:
    # Dokumen tiruan dengan beberapa bagian
    page1 = PageData(
        page_number=1,
        width=595.0,
        height=842.0,
        blocks=[
            TextBlock(
                text="Deep Residual Learning for Image Recognition\nKaiming He et al.",
                bbox=(50, 50, 400, 90),
                block_no=0,
            ),
            TextBlock(
                text="Abstract\nDeeper neural networks are more difficult to train.",
                bbox=(50, 100, 400, 150),
                block_no=1,
            ),
            TextBlock(
                text="1. Introduction\nDeep convolutional neural networks have led to a series of breakthroughs.",
                bbox=(50, 160, 400, 220),
                block_no=2,
            ),
        ],
        text="",
    )

    page2 = PageData(
        page_number=2,
        width=595.0,
        height=842.0,
        blocks=[
            TextBlock(
                text="3. Proposed Methodology\nWe adopt residual mapping across weight layers.",
                bbox=(50, 50, 400, 100),
                block_no=0,
            ),
            TextBlock(
                text="References\n[1] Y. LeCun, Nature 2015.",
                bbox=(50, 120, 400, 180),
                block_no=1,
            ),
        ],
        text="",
    )

    doc = ParsedDocument(total_pages=2, pages=[page1, page2])
    segments = identify_document_sections(doc)

    # Verifikasi segmen yang dihasilkan
    assert len(segments) == 5
    assert segments[0].section == SectionType.TITLE_AUTHORS
    assert "Kaiming He" in segments[0].full_text

    assert segments[1].section == SectionType.ABSTRACT
    assert "Deeper neural networks" in segments[1].full_text

    assert segments[2].section == SectionType.INTRODUCTION
    assert "breakthroughs" in segments[2].full_text

    assert segments[3].section == SectionType.METHODOLOGY
    assert "residual mapping" in segments[3].full_text

    assert segments[4].section == SectionType.REFERENCES
    assert "LeCun" in segments[4].full_text
