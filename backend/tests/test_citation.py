from app.llm.citation import parse_citation_numbers, validate_citations


def test_parse_citation_numbers() -> None:
    text = "Metode ini menggunakan transformer [1] dan dievaluasi pada dataset X [2, 3] serta referensi terkait [4][5] dan [6-8]."
    numbers = parse_citation_numbers(text)
    assert numbers == [1, 2, 3, 4, 5, 6, 7, 8]


def test_parse_citation_numbers_empty() -> None:
    text = "Tidak ada sitasi di kalimat ini sama sekali."
    assert parse_citation_numbers(text) == []


def test_validate_citations_success() -> None:
    context_chunks = [
        {
            "index": 1,
            "chunk_id": "chunk-uuid-1",
            "section": "Introduction",
            "page_start": 1,
            "page_end": 1,
            "text": "Attention is all you need for sequence modeling.",
            "bbox": {"x": 50, "y": 100, "w": 400, "h": 20},
        },
        {
            "index": 2,
            "chunk_id": "chunk-uuid-2",
            "section": "Architecture",
            "page_start": 2,
            "page_end": 3,
            "text": "The model uses multi-head self-attention mechanisms.",
            "bbox": {"x": 60, "y": 200, "w": 350, "h": 25},
        },
    ]

    answer = "Paper ini menggunakan multi-head self-attention [2] yang terbukti lebih efektif dibanding RNN [1]."
    _, validated = validate_citations(answer, context_chunks)

    assert len(validated) == 2
    # [1] and [2] in sorted order
    c1 = next(c for c in validated if c["citation_number"] == 1)
    assert c1["verified"] is True
    assert c1["chunk_id"] == "chunk-uuid-1"
    assert c1["section"] == "Introduction"
    assert c1["page_start"] == 1
    assert c1["bbox"] == {"x": 50, "y": 100, "w": 400, "h": 20}

    c2 = next(c for c in validated if c["citation_number"] == 2)
    assert c2["verified"] is True
    assert c2["chunk_id"] == "chunk-uuid-2"
    assert c2["page_start"] == 2
    assert c2["page_end"] == 3


def test_validate_citations_hallucinated_number() -> None:
    context_chunks = [
        {
            "index": 1,
            "chunk_id": "chunk-uuid-1",
            "section": "Abstract",
            "page_start": 1,
            "page_end": 1,
            "text": "Teks konteks nomor satu.",
            "bbox": None,
        }
    ]

    # Model mengutip nomor [1] dan [99] yang tidak ada di konteks
    answer = "Fakta pertama [1] didukung fakta imajiner [99]."
    _, validated = validate_citations(answer, context_chunks)

    assert len(validated) == 2
    c1 = next(c for c in validated if c["citation_number"] == 1)
    assert c1["verified"] is True

    c99 = next(c for c in validated if c["citation_number"] == 99)
    assert c99["verified"] is False
    assert c99["chunk_id"] == ""
    assert c99["section"] is None
