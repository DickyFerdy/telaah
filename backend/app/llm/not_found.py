import re

NOT_FOUND_DEFAULT_MESSAGE = "Informasi tersebut tidak ditemukan di dalam paper ini."

# Pola regex untuk mendeteksi penolakan spekulasi dan respons "tidak ditemukan di paper"
NOT_FOUND_PATTERNS = [
    r"tidak\s+ditemukan\s+(?:di\s+|dalam\s+|di\s+dalam\s+)?(?:paper|dokumen|teks)",
    r"tidak\s+(?:disebutkan|dibahas|terdapat|tercantum|dijelaskan)\s+(?:di\s+|dalam\s+|di\s+dalam\s+)?(?:paper|dokumen|teks)",
    r"tidak\s+memuat\s+informasi",
    r"informasi\s+tersebut\s+tidak\s+(?:tersedia|ada|ditemukan)",
    r"not\s+found\s+in\s+(?:the\s+|this\s+)?(?:paper|document|text)",
    r"not\s+(?:mentioned|discussed|stated|covered)\s+in\s+(?:the\s+|this\s+)?(?:paper|document|text)",
    r"(?:paper|document)\s+does\s+not\s+(?:mention|contain|discuss|provide)",
    r"no\s+information\s+(?:is\s+)?found\s+in\s+(?:the\s+|this\s+)?(?:paper|document)",
]

COMPILED_NOT_FOUND_RE = [
    re.compile(pattern, re.IGNORECASE) for pattern in NOT_FOUND_PATTERNS
]


def is_not_found_response(text: str) -> bool:
    """
    Mendeteksi apakah teks jawaban model merupakan penolakan spekulasi
    atau menyatakan bahwa informasi yang ditanyakan tidak ditemukan di dalam paper.
    """
    clean_text = text.strip()
    if not clean_text:
        return False

    for pattern_re in COMPILED_NOT_FOUND_RE:
        if pattern_re.search(clean_text):
            return True

    return False
