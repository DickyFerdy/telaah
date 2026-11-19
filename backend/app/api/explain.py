import logging
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.db.models import Paper, User
from app.db.session import get_db
from app.llm.client import generate_text_answer
from app.llm.prompts import (
    EXPLAIN_TERM_SYSTEM_PROMPT,
    build_explain_term_prompt,
)
from app.schemas.explain import ExplainTermRequest, ExplainTermResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/papers/{paper_id}/explain-term", tags=["explain"])


@router.post("", response_model=ExplainTermResponse)
async def explain_term(
    paper_id: uuid.UUID,
    payload: ExplainTermRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ExplainTermResponse:
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

    clean_term = payload.term.strip()
    if not clean_term:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Istilah tidak boleh kosong",
        )

    # 2. Susun prompt penjelasan istilah
    prompt = build_explain_term_prompt(
        term=clean_term,
        context=payload.context,
        paper_title=paper.title,
    )

    try:
        explanation = await generate_text_answer(
            prompt=prompt,
            system_instruction=EXPLAIN_TERM_SYSTEM_PROMPT,
        )
    except Exception as err:
        logger.exception("Gagal menghasilkan penjelasan istilah dari LLM")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Gagal menghasilkan penjelasan istilah: {err}",
        ) from err

    return ExplainTermResponse(
        term=clean_term,
        explanation=explanation,
        context=payload.context,
    )
