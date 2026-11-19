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
