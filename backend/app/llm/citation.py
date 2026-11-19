import re
from dataclasses import asdict, dataclass
from typing import Any

# Pola untuk mendeteksi sitasi seperti [1], [2], [1, 2], [1][2], [1-3]
CITATION_PATTERN = re.compile(r"\[([0-9,\s\-]+)\]")


@dataclass
class ValidatedCitation:
    citation_number: int
    chunk_id: str
    section: str | None
    page_start: int | None
    page_end: int | None
    bbox: dict[str, Any] | None
    snippet: str
    verified: bool


def parse_citation_numbers(text: str) -> list[int]:
    """Ekstrak semua nomor referensi unik dari teks (misal: '[1]', '[2, 3]', '[1][4]')."""
    numbers: set[int] = set()
    matches = CITATION_PATTERN.findall(text)

    for m in matches:
        # Pisahkan berdasarkan koma atau spasi
        parts = re.split(r"[,\s]+", m.strip())
        for part in parts:
            if "-" in part:
                # Rentang misal "1-3" -> 1, 2, 3
                range_parts = part.split("-")
                if len(range_parts) == 2 and range_parts[0].isdigit() and range_parts[1].isdigit():
                    start, end = int(range_parts[0]), int(range_parts[1])
                    if start <= end and (end - start) < 10:  # batas wajar
                        numbers.update(range(start, end + 1))
            elif part.isdigit():
                numbers.add(int(part))

    return sorted(numbers)


def validate_citations(
    answer_text: str,
    context_chunks: list[dict[str, Any]],
) -> tuple[str, list[dict[str, Any]]]:
    """
    Validasi sitasi bernomor pada teks jawaban terhadap daftar potongan konteks yang dikirim ke LLM.
    
    Langkah:
    1. Mengekstrak semua nomor sitasi [n] dari teks jawaban.
    2. Mencocokkan nomor n dengan indeks context_chunks (1-indexed).
    3. Jika n valid, petakan ke metadata chunk lengkap (ID, section, page, bbox).
    4. Jika n di luar rentang konteks (halusinasi nomor), tandai sebagai unverified.
    5. Membersihkan sitasi fiktif yang tidak valid dari teks jawaban jika diinginkan.
    """
    if not context_chunks:
        return answer_text, []

    # Map indeks 1-based ke data chunk
    chunk_by_index: dict[int, dict[str, Any]] = {
        c.get("index", idx): c for idx, c in enumerate(context_chunks, start=1)
    }

    found_numbers = parse_citation_numbers(answer_text)
    validated_list: list[dict[str, Any]] = []

    for num in found_numbers:
        if num in chunk_by_index:
            chunk = chunk_by_index[num]
            citation_item = ValidatedCitation(
                citation_number=num,
                chunk_id=str(chunk.get("chunk_id", "")),
                section=chunk.get("section"),
                page_start=chunk.get("page_start"),
                page_end=chunk.get("page_end"),
                bbox=chunk.get("bbox"),
                snippet=chunk.get("text", "")[:250].strip().replace("\n", " "),
                verified=True,
            )
            validated_list.append(asdict(citation_item))
        else:
            # Nomor di luar jangkauan potongan konteks
            citation_item = ValidatedCitation(
                citation_number=num,
                chunk_id="",
                section=None,
                page_start=None,
                page_end=None,
                bbox=None,
                snippet="",
                verified=False,
            )
            validated_list.append(asdict(citation_item))

    return answer_text, validated_list
