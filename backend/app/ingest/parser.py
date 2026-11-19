from dataclasses import dataclass
from pathlib import Path

import pymupdf


@dataclass
class TextBlock:
    text: str
    bbox: tuple[float, float, float, float]  # (x0, y0, x1, y1)
    block_no: int


@dataclass
class PageData:
    page_number: int  # 1-indexed
    width: float
    height: float
    blocks: list[TextBlock]
    text: str


@dataclass
class ParsedDocument:
    total_pages: int
    pages: list[PageData]


def clean_text(text: str) -> str:
    """Bersihkan spasi berlebih dan sambungan kata terputus tanda hubung."""
    # Dehyphenation sederhana: misal "seg- \nment" -> "segment"
    lines = text.splitlines()
    cleaned_lines = []
    for line in lines:
        cleaned_lines.append(line.strip())
    joined = "\n".join(line for line in cleaned_lines if line)
    return joined


def parse_pdf(file_path: str | Path) -> ParsedDocument:
    """
    Ekstrak teks dan bounding box per halaman dari file PDF menggunakan PyMuPDF.
    
    Menghasilkan `ParsedDocument` yang berisi daftar halaman, ukuran halaman,
    blok-blok teks dengan koordinatnya, serta teks gabungan per halaman.
    """
    path_obj = Path(file_path)
    if not path_obj.exists():
        raise FileNotFoundError(f"File PDF tidak ditemukan: {file_path}")

    try:
        doc = pymupdf.open(str(path_obj))
    except Exception as exc:
        raise ValueError(f"Gagal membuka dokumen PDF: {exc!s}") from exc

    pages: list[PageData] = []

    for page_idx in range(len(doc)):
        page = doc[page_idx]
        rect = page.rect
        width = float(rect.width)
        height = float(rect.height)

        # page.get_text("blocks") returns tuples:
        # (x0, y0, x1, y1, "text", block_no, block_type)
        # block_type == 0 untuk teks, 1 untuk gambar
        raw_blocks = page.get_text("blocks")
        text_blocks: list[TextBlock] = []
        page_text_parts: list[str] = []

        for b in raw_blocks:
            if len(b) >= 7 and b[6] == 0:  # Text block
                block_text = b[4].strip()
                if block_text:
                    bbox = (float(b[0]), float(b[1]), float(b[2]), float(b[3]))
                    text_blocks.append(
                        TextBlock(
                            text=block_text,
                            bbox=bbox,
                            block_no=int(b[5]),
                        )
                    )
                    page_text_parts.append(block_text)

        full_page_text = "\n\n".join(page_text_parts)
        pages.append(
            PageData(
                page_number=page_idx + 1,
                width=width,
                height=height,
                blocks=text_blocks,
                text=full_page_text,
            )
        )

    doc.close()

    return ParsedDocument(
        total_pages=len(pages),
        pages=pages,
    )
