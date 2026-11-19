import re
from dataclasses import dataclass
from typing import Any

from app.ingest.sections import SectionBlock, SectionSegment


@dataclass
class DocumentChunk:
    chunk_index: int
    section: str
    text: str
    page_start: int
    page_end: int
    bbox: dict[str, Any]  # {"boxes": [{"page": int, "bbox": [x0, y0, x1, y1]}], "bounds": [x0, y0, x1, y1]}
    token_count: int


def estimate_token_count(text: str) -> int:
    """Estimasi jumlah token: ~4 karakter per token atau 1.3 * kata."""
    # Menghitung estimasi token berdasarkan rasio kata dan karakter
    word_count = len(text.split())
    char_count = len(text)
    return max(word_count, char_count // 4)


def split_text_into_sentences(text: str) -> list[str]:
    """Pecah teks menjadi daftar kalimat dengan regex."""
    # Memisahkan berdasarkan tanda titik, tanda tanya, atau seru yang diikuti spasi/newline
    raw_sentences = re.split(r"(?<=[.!?])\s+", text)
    sentences = [s.strip() for s in raw_sentences if s.strip()]
    return sentences if sentences else [text]


def build_chunk_bbox(blocks: list[SectionBlock]) -> dict[str, Any]:
    """Bangun representasi bounding box gabungan dan per-blok."""
    if not blocks:
        return {"boxes": [], "bounds": [0.0, 0.0, 0.0, 0.0]}

    boxes = []
    min_x = float("inf")
    min_y = float("inf")
    max_x = float("-inf")
    max_y = float("-inf")

    for b in blocks:
        x0, y0, x1, y1 = b.block.bbox
        boxes.append(
            {
                "page": b.page_number,
                "bbox": [round(x0, 2), round(y0, 2), round(x1, 2), round(y1, 2)],
            }
        )
        min_x = min(min_x, x0)
        min_y = min(min_y, y0)
        max_x = max(max_x, x1)
        max_y = max(max_y, y1)

    return {
        "boxes": boxes,
        "bounds": [
            round(min_x, 2),
            round(min_y, 2),
            round(max_x, 2),
            round(max_y, 2),
        ],
    }


def chunk_document_sections(
    segments: list[SectionSegment],
    target_chars: int = 1200,
    max_chars: int = 1800,
) -> list[DocumentChunk]:
    """
    Memotong dokumen menjadi chunk-chunk teks dengan aturan sadar bagian (section-aware).
    
    Aturan:
    1. Chunk TIDAK PERNAH melintasi batas bagian (SectionSegment).
    2. Blok-blok teks dalam satu section digabungkan hingga mendekati `target_chars`.
    3. Jika satu blok melebihi `max_chars`, blok dipecah per kalimat.
    4. Setiap chunk mencatat `page_start`, `page_end`, dan metadata `bbox`.
    """
    chunks: list[DocumentChunk] = []
    chunk_index = 0

    for segment in segments:
        if not segment.blocks:
            continue

        section_name = segment.section.value

        current_blocks: list[SectionBlock] = []
        current_text_parts: list[str] = []
        current_len = 0

        for block in segment.blocks:
            block_text = block.block.text.strip()
            if not block_text:
                continue

            block_len = len(block_text)

            # Jika blok saat ini terlalu panjang melampaui max_chars, pecah per kalimat
            if block_len > max_chars:
                # Flush buffer yang ada terlebih dahulu
                if current_text_parts:
                    chunk_text = "\n\n".join(current_text_parts)
                    chunks.append(
                        DocumentChunk(
                            chunk_index=chunk_index,
                            section=section_name,
                            text=chunk_text,
                            page_start=current_blocks[0].page_number,
                            page_end=current_blocks[-1].page_number,
                            bbox=build_chunk_bbox(current_blocks),
                            token_count=estimate_token_count(chunk_text),
                        )
                    )
                    chunk_index += 1
                    current_blocks = []
                    current_text_parts = []
                    current_len = 0

                sentences = split_text_into_sentences(block_text)
                sub_sentences: list[str] = []
                sub_len = 0

                for s in sentences:
                    s_len = len(s)
                    if sub_len + s_len > target_chars and sub_sentences:
                        sub_text = " ".join(sub_sentences)
                        chunks.append(
                            DocumentChunk(
                                chunk_index=chunk_index,
                                section=section_name,
                                text=sub_text,
                                page_start=block.page_number,
                                page_end=block.page_number,
                                bbox=build_chunk_bbox([block]),
                                token_count=estimate_token_count(sub_text),
                            )
                        )
                        chunk_index += 1
                        sub_sentences = []
                        sub_len = 0

                    sub_sentences.append(s)
                    sub_len += s_len

                if sub_sentences:
                    sub_text = " ".join(sub_sentences)
                    chunks.append(
                        DocumentChunk(
                            chunk_index=chunk_index,
                            section=section_name,
                            text=sub_text,
                            page_start=block.page_number,
                            page_end=block.page_number,
                            bbox=build_chunk_bbox([block]),
                            token_count=estimate_token_count(sub_text),
                        )
                    )
                    chunk_index += 1
                continue

            # Jika penambahan blok melebihi target_chars, buat chunk baru
            if current_len + block_len > target_chars and current_text_parts:
                chunk_text = "\n\n".join(current_text_parts)
                chunks.append(
                    DocumentChunk(
                        chunk_index=chunk_index,
                        section=section_name,
                        text=chunk_text,
                        page_start=current_blocks[0].page_number,
                        page_end=current_blocks[-1].page_number,
                        bbox=build_chunk_bbox(current_blocks),
                        token_count=estimate_token_count(chunk_text),
                    )
                )
                chunk_index += 1
                current_blocks = [block]
                current_text_parts = [block_text]
                current_len = block_len
            else:
                current_blocks.append(block)
                current_text_parts.append(block_text)
                current_len += block_len

        # Flush sisa blok di section ini
        if current_text_parts:
            chunk_text = "\n\n".join(current_text_parts)
            chunks.append(
                DocumentChunk(
                    chunk_index=chunk_index,
                    section=section_name,
                    text=chunk_text,
                    page_start=current_blocks[0].page_number,
                    page_end=current_blocks[-1].page_number,
                    bbox=build_chunk_bbox(current_blocks),
                    token_count=estimate_token_count(chunk_text),
                )
            )
            chunk_index += 1

    return chunks
