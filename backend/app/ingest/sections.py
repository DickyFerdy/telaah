import re
from dataclasses import dataclass
from enum import Enum

from app.ingest.parser import ParsedDocument, TextBlock


class SectionType(str, Enum):
    TITLE_AUTHORS = "title_authors"
    ABSTRACT = "abstract"
    INTRODUCTION = "introduction"
    RELATED_WORK = "related_work"
    METHODOLOGY = "methodology"
    EXPERIMENTS_RESULTS = "experiments_results"
    DISCUSSION = "discussion"
    CONCLUSION = "conclusion"
    REFERENCES = "references"
    APPENDIX = "appendix"
    OTHER = "other"


# Daftar regex pola heading ilmiah standar
SECTION_PATTERNS: list[tuple[SectionType, re.Pattern[str]]] = [
    # References / Daftar Pustaka
    (
        SectionType.REFERENCES,
        re.compile(
            r"^(?:\d+[\.\s]+)?(?:references|bibliography|works cited|literature cited)\b",
            re.IGNORECASE,
        ),
    ),
    # Appendix / Lampiran
    (
        SectionType.APPENDIX,
        re.compile(
            r"^(?:appendix|supplementary material|supplementary information)\b",
            re.IGNORECASE,
        ),
    ),
    # Abstract
    (
        SectionType.ABSTRACT,
        re.compile(r"^(?:abstract|summary|ringkasan)\b", re.IGNORECASE),
    ),
    # Conclusion
    (
        SectionType.CONCLUSION,
        re.compile(
            r"^(?:\d+[\.\s]+)?(?:conclusion|conclusions|concluding remarks|summary and conclusion)\b",
            re.IGNORECASE,
        ),
    ),
    # Discussion
    (
        SectionType.DISCUSSION,
        re.compile(
            r"^(?:\d+[\.\s]+)?(?:discussion|discussions)\b",
            re.IGNORECASE,
        ),
    ),
    # Results / Experiments / Findings
    (
        SectionType.EXPERIMENTS_RESULTS,
        re.compile(
            r"^(?:\d+[\.\s]+)?(?:results|experimental results|experiments|evaluation|findings|results and discussion)\b",
            re.IGNORECASE,
        ),
    ),
    # Methodology / Materials and Methods / Proposed Approach
    (
        SectionType.METHODOLOGY,
        re.compile(
            r"^(?:\d+[\.\s]+)?(?:proposed\s+)?(?:methodology|methods|materials and methods|method|model architecture|approach|system design|implementation)\b",
            re.IGNORECASE,
        ),
    ),
    # Related Work / Background
    (
        SectionType.RELATED_WORK,
        re.compile(
            r"^(?:\d+[\.\s]+)?(?:related work|related works|background|literature review|prior work)\b",
            re.IGNORECASE,
        ),
    ),
    # Introduction
    (
        SectionType.INTRODUCTION,
        re.compile(
            r"^(?:\d+[\.\s]+)?(?:introduction|overview|pendahuluan)\b",
            re.IGNORECASE,
        ),
    ),
]


def match_section_heading(text: str) -> SectionType | None:
    """
    Mengecek apakah suatu baris/blok teks merupakan heading bagian paper.
    Syarat umum heading: teks tidak terlalu panjang dan cocok dengan pola regex.
    """
    first_line = text.strip().splitlines()[0].strip()
    # Heading umumnya pendek (< 80 karakter)
    if len(first_line) > 80:
        return None

    # Hapus penomoran romawi atau angka di depan (misal: "I. INTRODUCTION", "1.1 Related Work")
    cleaned = re.sub(r"^(?:[0-9IVXLCDM]+[\.\s\)]+|[A-Z]\.[\s]+)", "", first_line).strip()

    # Periksa kecocokan dengan pola section
    for section_type, pattern in SECTION_PATTERNS:
        if pattern.search(first_line) or pattern.search(cleaned):
            return section_type

    return None


@dataclass
class SectionBlock:
    section: SectionType
    page_number: int
    block: TextBlock


@dataclass
class SectionSegment:
    section: SectionType
    title: str
    blocks: list[SectionBlock]

    @property
    def full_text(self) -> str:
        return "\n\n".join(b.block.text for b in self.blocks)


def identify_document_sections(parsed_doc: ParsedDocument) -> list[SectionSegment]:
    """
    Menelusuri seluruh blok teks dokumen dari awal hingga akhir,
    mengelompokkan blok-blok teks ke dalam segmen-segmen bagian (sections).
    """
    segments: list[SectionSegment] = []
    current_section = SectionType.TITLE_AUTHORS
    current_title = "Title & Authors"
    current_blocks: list[SectionBlock] = []

    for page in parsed_doc.pages:
        for block in page.blocks:
            detected = match_section_heading(block.text)

            # Jika terdeteksi heading baru dan sudah ada blok yang terkumpul
            if detected is not None:
                if current_blocks:
                    segments.append(
                        SectionSegment(
                            section=current_section,
                            title=current_title,
                            blocks=current_blocks,
                        )
                    )
                    current_blocks = []

                current_section = detected
                current_title = block.text.splitlines()[0].strip()

            current_blocks.append(
                SectionBlock(
                    section=current_section,
                    page_number=page.page_number,
                    block=block,
                )
            )

    # Tambahkan segmen terakhir yang tersisa
    if current_blocks:
        segments.append(
            SectionSegment(
                section=current_section,
                title=current_title,
                blocks=current_blocks,
            )
        )

    return segments
