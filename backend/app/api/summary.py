import logging
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.db.models import Chunk, Paper, Summary, User
from app.db.session import get_db
from app.llm.client import generate_structured_json
from app.llm.prompts import (
    SUMMARY_PROMPT_VERSION,
    SUMMARY_SYSTEM_PROMPT_V1,
    build_summary_prompt,
)
from app.schemas.summary import SummaryContent, SummaryResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/papers/{paper_id}/summary", tags=["summary"])


def _extract_section_contexts(chunks: list[Chunk]) -> dict[str, str]:
    """
    Mengelompokkan teks chunk berdasarkan bagian-bagian ilmiah penting
    (Abstract, Methodology, Experiments/Results, Conclusion, Discussion).
    Jika chunk tidak memiliki bagian terdeteksi, ambil potongan awal dan akhir paper.
    """
    section_map: dict[str, list[str]] = {
        "abstract": [],
        "methodology": [],
        "experiments_results": [],
        "conclusion": [],
        "discussion": [],
        "other": [],
    }

    for c in chunks:
        sec = (c.section or "other").lower().strip()
        if "abstract" in sec or "summary" in sec:
            section_map["abstract"].append(c.text)
        elif "method" in sec or "approach" in sec or "architecture" in sec:
            section_map["methodology"].append(c.text)
        elif "result" in sec or "experiment" in sec or "evaluation" in sec:
            section_map["experiments_results"].append(c.text)
        elif "conclusion" in sec or "concluding" in sec:
            section_map["conclusion"].append(c.text)
        elif "discussion" in sec or "limitation" in sec:
            section_map["discussion"].append(c.text)
        else:
            section_map["other"].append(c.text)

    # Gabungkan teks dengan batas panjang per bagian agar efisien
    result_texts: dict[str, str] = {}

    has_structured_sections = any(
        len(section_map[k]) > 0
        for k in ["abstract", "methodology", "experiments_results", "conclusion"]
    )

    if has_structured_sections:
        for k, text_list in section_map.items():
            if k == "other":
                continue
            if text_list:
                # Batasi ~3500 karakter per bagian penting
                combined = " ".join(text_list)[:3500]
                result_texts[k] = combined
    else:
        # Fallback jika struktur bagian tidak terdeteksi: ambil chunk awal (1-4) dan akhir (terakhir 2)
        all_texts = [c.text for c in chunks]
        early_texts = all_texts[:4]
        late_texts = all_texts[-2:] if len(all_texts) > 4 else []
        result_texts["awal_dokumen"] = " ".join(early_texts)[:4000]
        if late_texts:
            result_texts["akhir_dokumen"] = " ".join(late_texts)[:3000]

    return result_texts


@router.get("", response_model=SummaryResponse)
async def get_summary(
    paper_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SummaryResponse:
    # 1. Validasi kepemilikan paper
    paper = await db.scalar(
        select(Paper).where(
            Paper.id == paper_id,
            Paper.user_id == current_user.id,
        )
    )
    if not paper:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Paper tidak ditemukan",
        )

    # 2. Cari ringkasan yang tersimpan
    summary = await db.scalar(
        select(Summary).where(Summary.paper_id == paper_id)
    )
    if not summary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ringkasan belum dibuat untuk paper ini",
        )

    return SummaryResponse.model_validate(summary)


@router.post("", response_model=SummaryResponse)
@router.post("/regenerate", response_model=SummaryResponse)
async def generate_summary(
    paper_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SummaryResponse:
    # 1. Validasi kepemilikan paper
    paper = await db.scalar(
        select(Paper).where(
            Paper.id == paper_id,
            Paper.user_id == current_user.id,
        )
    )
    if not paper:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Paper tidak ditemukan",
        )

    # 2. Pastikan paper sudah berstatus 'ready'
    if paper.status != "ready":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Paper belum selesai diproses (status: {paper.status}). Harap tunggu hingga status 'ready'.",
        )

    # 3. Ambil chunk teks dokumen untuk diekstrak
    stmt = (
        select(Chunk)
        .where(Chunk.paper_id == paper_id)
        .order_by(Chunk.page_start.asc(), Chunk.id.asc())
    )
    result = await db.execute(stmt)
    chunks = list(result.scalars().all())

    if not chunks:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tidak ada teks atau chunk yang ditemukan pada paper ini untuk diringkas.",
        )

    # 4. Susun konteks dan panggil Gemini API
    section_texts = _extract_section_contexts(chunks)
    prompt = build_summary_prompt(paper.title, section_texts)

    try:
        raw_json = await generate_structured_json(
            prompt=prompt,
            system_instruction=SUMMARY_SYSTEM_PROMPT_V1,
        )
        content = SummaryContent(
            research_question=raw_json.get("research_question", "Tidak disebutkan"),
            method=raw_json.get("method", "Tidak disebutkan"),
            dataset=raw_json.get("dataset", "Tidak disebutkan"),
            metrics=raw_json.get("metrics", "Tidak disebutkan"),
            results=raw_json.get("results", "Tidak disebutkan"),
            limitations=raw_json.get("limitations", "Tidak disebutkan"),
            tldr=raw_json.get("tldr"),
        )
    except Exception as err:
        logger.exception("Gagal menghasilkan ringkasan terstruktur dari LLM")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Gagal menghasilkan ringkasan paper dari LLM: {err}",
        ) from err

    # 5. Simpan ke database (buat baru atau update)
    existing_summary = await db.scalar(
        select(Summary).where(Summary.paper_id == paper_id)
    )

    if existing_summary:
        existing_summary.content = content.model_dump()
        existing_summary.prompt_version = SUMMARY_PROMPT_VERSION
        existing_summary.created_at = func.now()
        await db.commit()
        await db.refresh(existing_summary)
        summary = existing_summary
    else:
        summary = Summary(
            id=uuid.uuid4(),
            paper_id=paper_id,
            content=content.model_dump(),
            prompt_version=SUMMARY_PROMPT_VERSION,
        )
        db.add(summary)
        await db.commit()
        await db.refresh(summary)

    return SummaryResponse.model_validate(summary)
