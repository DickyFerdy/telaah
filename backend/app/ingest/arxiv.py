import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass

import httpx
from fastapi import HTTPException, status

from app.ingest.validator import MAX_FILE_SIZE_BYTES, PDF_MAGIC_BYTES

ARXIV_ID_PATTERN = re.compile(
    r"(?:arxiv\.org/(?:abs|pdf)/)?([0-9]{4}\.[0-9]{4,5}(?:v[0-9]+)?|[a-z\-]+(?:\.[a-z]{2})?/[0-9]{7})",
    re.IGNORECASE,
)
ARXIV_API_BASE = "https://export.arxiv.org/api/query"
ARXIV_PDF_BASE = "https://arxiv.org/pdf"


@dataclass
class ArxivMetadata:
    arxiv_id: str
    title: str
    authors: list[str]


def parse_arxiv_id(input_str: str) -> str:
    cleaned = input_str.strip()
    # Strip trailing .pdf if present
    if cleaned.lower().endswith(".pdf"):
        cleaned = cleaned[:-4]

    match = ARXIV_ID_PATTERN.search(cleaned)
    if not match:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Identifier atau URL arXiv tidak valid",
        )
    return match.group(1)


async def fetch_arxiv_metadata(arxiv_id: str) -> ArxivMetadata:
    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            resp = await client.get(
                ARXIV_API_BASE, params={"id_list": arxiv_id}
            )
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Gagal menghubungi arXiv API: {exc!s}",
            ) from exc

    # Parse Atom XML
    # Namespaces usually: {http://www.w3.org/2005/Atom}
    try:
        root = ET.fromstring(resp.text)
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        entry = root.find("atom:entry", ns)
        if entry is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Paper arXiv dengan ID '{arxiv_id}' tidak ditemukan",
            )

        title_elem = entry.find("atom:title", ns)
        title = (
            " ".join(title_elem.text.split())
            if title_elem is not None and title_elem.text
            else arxiv_id
        )

        author_elems = entry.findall("atom:author/atom:name", ns)
        authors = [
            a.text.strip() for a in author_elems if a.text and a.text.strip()
        ]

        return ArxivMetadata(
            arxiv_id=arxiv_id,
            title=title,
            authors=authors,
        )
    except ET.ParseError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Gagal membaca respon dari arXiv API",
        ) from exc


async def download_arxiv_pdf(
    arxiv_id: str,
    max_size_bytes: int = MAX_FILE_SIZE_BYTES,
) -> bytes:
    pdf_url = f"{ARXIV_PDF_BASE}/{arxiv_id}.pdf"
    headers = {"User-Agent": "Telaah-Research-Assistant/1.0"}

    async with httpx.AsyncClient(
        timeout=30.0, follow_redirects=True
    ) as client:
        try:
            resp = await client.get(pdf_url, headers=headers)
            resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"PDF arXiv dengan ID '{arxiv_id}' tidak ditemukan",
                ) from exc
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Gagal mengunduh PDF dari arXiv: {exc!s}",
            ) from exc
        except httpx.HTTPError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Gagal menghubungi server arXiv: {exc!s}",
            ) from exc

    content = resp.content

    if len(content) > max_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=f"Ukuran file melebihi batas maksimal {max_size_bytes // (1024 * 1024)} MB",
        )

    if len(content) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File PDF dari arXiv kosong",
        )

    if not content.startswith(PDF_MAGIC_BYTES):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File yang diunduh dari arXiv bukan dokumen PDF yang valid",
        )

    return content

