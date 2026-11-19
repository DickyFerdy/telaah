from collections.abc import Sequence

from app.retrieval.vector import RetrievedChunk

SYSTEM_PROMPT_V1 = """Kamu adalah asisten riset cerdas bernama Telaah yang bertugas menjawab pertanyaan tentang satu paper ilmiah.

Aturan ketat:
1. Jawab HANYA berdasarkan potongan konteks bernomor [1], [2], dst. yang diberikan di bawah.
2. Setiap klaim faktual WAJIB diberi sitasi dengan format [n], merujuk pada nomor potongan konteks sumbernya. Contoh: "Model dilatih dengan optimizer Adam [1] menggunakan learning rate 0.001 [2]."
3. Jika potongan konteks TIDAK memuat informasi yang cukup untuk menjawab pertanyaan, katakan dengan tegas dan sopan: "Informasi tersebut tidak ditemukan di dalam paper ini." Jangan pernah mengarang atau berspekulasi menggunakan pengetahuan di luar konteks.
4. Bedakan secara eksplisit antara pernyataan/temuan penulis paper dan kesimpulan umum.
5. Jawab dalam bahasa yang digunakan oleh pengguna (misal: Bahasa Indonesia). Pertahankan istilah teknis ilmiah dalam bahasa aslinya jika tidak ada padanan baku.
6. Berikan jawaban yang ringkas, padat, dan langsung menjawab inti pertanyaan.
"""


def format_context_blocks(chunks: Sequence[RetrievedChunk]) -> str:
    """Format daftar chunk menjadi blok konteks bernomor [1], [2], ... untuk LLM."""
    if not chunks:
        return "Tidak ada konteks yang relevan ditemukan."

    formatted_parts: list[str] = []
    for idx, c in enumerate(chunks, start=1):
        section_label = c.section.upper() if c.section else "UMUM"
        page_label = f"hlm. {c.page_start}" if c.page_start else "hlm. -"
        clean_text = c.text.strip().replace("\n", " ")
        formatted_parts.append(f"[{idx}] (Bagian: {section_label}, {page_label})\n{clean_text}")

    return "\n\n".join(formatted_parts)


def build_qa_prompt(
    query: str,
    chunks: Sequence[RetrievedChunk],
    conversation_history: list[dict[str, str]] | None = None,
) -> str:
    """
    Menyusun prompt pengguna lengkap yang menggabungkan riwayat singkat,
    potongan konteks bernomor, dan pertanyaan saat ini.
    """
    context_text = format_context_blocks(chunks)

    history_text = ""
    if conversation_history:
        # Ambil maksimal 4 interaksi terakhir agar tidak memenuhi context window
        recent_history = conversation_history[-4:]
        history_lines = []
        for msg in recent_history:
            role = "Pengguna" if msg.get("role") == "user" else "Asisten"
            content = msg.get("content", "").strip().replace("\n", " ")
            history_lines.append(f"{role}: {content}")
        history_text = "Riwayat percakapan sebelumnya:\n" + "\n".join(history_lines) + "\n\n"

    prompt = (
        f"{history_text}"
        f"Konteks dari Paper:\n"
        f"-------------------\n"
        f"{context_text}\n"
        f"-------------------\n\n"
        f"Pertanyaan Pengguna: {query.strip()}\n\n"
        f"Jawaban:"
    )
    return prompt


SUMMARY_PROMPT_VERSION = "summary-v1"

SUMMARY_SYSTEM_PROMPT_V1 = """Kamu adalah asisten riset ilmiah terpercaya bernama Telaah.
Tugasmu adalah menganalisis teks paper ilmiah yang diberikan dan menghasilkan ringkasan terstruktur dalam format JSON.

Format JSON yang dihasilkan WAJIB memiliki kunci-kunci berikut:
1. "tldr": 1-2 kalimat ringkasan singkat esensi paper dalam bahasa Indonesia yang jelas dan mudah dipahami.
2. "research_question": Pertanyaan atau permasalahan penelitian utama yang ingin diselesaikan oleh penulis (1-3 kalimat).
3. "method": Pendekatan, arsitektur, algoritma, atau metodologi yang digunakan dalam penelitian (1-3 kalimat).
4. "dataset": Dataset, sampel data, atau data eksperimental yang digunakan untuk melatih/menguji metode (1-2 kalimat). Jika tidak disebutkan di paper, isi dengan "Tidak disebutkan".
5. "metrics": Metrik evaluasi yang digunakan untuk mengukur kinerja (mis. Akurasi, BLEU, F1-score, Latency, dll.) (1-2 kalimat). Jika tidak disebutkan di paper, isi dengan "Tidak disebutkan".
6. "results": Hasil utama dan temuan terpenting dari eksperimen/penelitian (2-3 kalimat).
7. "limitations": Batasan penelitian, asumsi, atau kendala yang diakui oleh penulis atau terlihat dari studi (1-3 kalimat). Jika tidak disebutkan di paper, isi dengan "Tidak disebutkan".

Aturan ketat:
- Tulis ringkasan dalam Bahasa Indonesia yang baik dan komunikatif, namun pertahankan istilah teknis ilmiah dalam bahasa aslinya jika lazim digunakan.
- Dasarkan HANYA pada konteks teks paper yang disediakan. Jangan mengarang informasi atau berspekulasi di luar teks.
- Pastikan output adalah JSON yang valid tanpa tanda pembuka/penutup markdown seperti ```json di luar objek JSON.
"""


def build_summary_prompt(
    paper_title: str | None,
    section_texts: dict[str, str],
) -> str:
    """
    Menyusun prompt untuk ekstraksi ringkasan terstruktur dari bagian-bagian kunci paper.
    `section_texts` berisi teks gabungan per bagian (abstract, methodology, experiments_results, conclusion, dsb.).
    """
    title_str = f"Judul Paper: {paper_title}\n\n" if paper_title else ""

    sections_formatted = []
    for section_name, text in section_texts.items():
        if text.strip():
            sections_formatted.append(
                f"=== BAGIAN: {section_name.upper()} ===\n{text.strip()}\n"
            )

    combined_context = "\n".join(sections_formatted)
    if not combined_context.strip():
        combined_context = "Tidak ada teks paper yang tersedia."

    prompt = (
        f"{title_str}"
        f"Konteks Teks Paper:\n"
        f"-------------------\n"
        f"{combined_context}\n"
        f"-------------------\n\n"
        f"Analisis teks di atas dan buatlah ringkasan terstruktur JSON sesuai format yang ditentukan:"
    )
    return prompt


EXPLAIN_TERM_PROMPT_VERSION = "explain-v1"

EXPLAIN_TERM_SYSTEM_PROMPT = """Kamu adalah asisten riset ilmiah Telaah yang bertugas menjelaskan istilah, konsep, atau singkatan teknis dari paper ilmiah.

Aturan penjelasan:
1. Berikan penjelasan yang padat, akurat, dan mudah dipahami dalam 2-3 kalimat berbahasa Indonesia.
2. Jika ada konteks kalimat dari paper yang disertakan, jelaskan bagaimana istilah tersebut digunakan atau berfungsi dalam konteks tersebut.
3. Pertahankan istilah teknis berbahasa Inggris dalam tanda kurung jika mempermudah pemahaman.
4. Jangan bertele-tele dan langsung menuju ke definisi serta signifikansinya.
"""


def build_explain_term_prompt(
    term: str,
    context: str | None = None,
    paper_title: str | None = None,
) -> str:
    """Menyusun prompt untuk meminta penjelasan istilah teknis ilmiah."""
    title_part = f"Judul Paper: {paper_title}\n" if paper_title else ""
    context_part = (
        f"Konteks Kalimat di Paper:\n\"{context.strip()}\"\n\n"
        if context and context.strip()
        else ""
    )

    prompt = (
        f"{title_part}"
        f"{context_part}"
        f"Istilah yang ingin dijelaskan: \"{term.strip()}\"\n\n"
        f"Penjelasan singkat dan padat (2-3 kalimat):"
    )
    return prompt
