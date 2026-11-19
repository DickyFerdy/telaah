import json
import logging
import uuid
from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.db.models import Conversation, Message, Paper, User
from app.db.session import async_session_maker, get_db
from app.llm.citation import validate_citations
from app.llm.client import stream_generate_answer
from app.llm.prompts import SYSTEM_PROMPT_V1, build_qa_prompt
from app.retrieval.hybrid import search_hybrid
from app.schemas.chat import ChatRequest

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/papers/{paper_id}/chat", tags=["chat"])


@router.post("")
async def chat_with_paper(
    paper_id: uuid.UUID,
    payload: ChatRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> StreamingResponse:
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

    # 2. Ambil atau buat percakapan (Conversation)
    conversation: Conversation | None = None
    if payload.conversation_id:
        conversation = await db.scalar(
            select(Conversation).where(
                Conversation.id == payload.conversation_id,
                Conversation.paper_id == paper_id,
                Conversation.user_id == current_user.id,
            )
        )

    if not conversation:
        conversation = Conversation(
            id=uuid.uuid4(),
            paper_id=paper_id,
            user_id=current_user.id,
        )
        db.add(conversation)
        await db.commit()
        await db.refresh(conversation)

    conv_id = conversation.id

    # 3. Simpan pesan pengguna
    user_msg = Message(
        id=uuid.uuid4(),
        conversation_id=conv_id,
        role="user",
        content=payload.message.strip(),
    )
    db.add(user_msg)
    await db.commit()

    # 4. Ambil riwayat percakapan sebelumnya untuk konteks
    history_rows = await db.scalars(
        select(Message)
        .where(Message.conversation_id == conv_id)
        .order_by(Message.created_at.asc())
    )
    history = [{"role": m.role, "content": m.content} for m in history_rows.all()]

    # 5. Retrieval kandidat teks relevan menggunakan Hybrid Search & Reranking
    retrieved_chunks = await search_hybrid(
        query=payload.message,
        paper_id=paper_id,
        db=db,
        top_k=5,
    )

    # 6. Susun payload context event untuk SSE
    context_data = [
        {
            "index": idx,
            "chunk_id": str(c.chunk_id),
            "section": c.section,
            "page_start": c.page_start,
            "page_end": c.page_end,
            "text": c.text,
            "bbox": c.bbox,
            "similarity_score": c.similarity_score,
        }
        for idx, c in enumerate(retrieved_chunks, start=1)
    ]

    # 7. Susun prompt lengkap
    qa_prompt = build_qa_prompt(
        query=payload.message,
        chunks=retrieved_chunks,
        conversation_history=history,
    )

    # Generator streaming SSE
    async def sse_event_stream() -> AsyncGenerator[str, None]:
        # Event 1: Mengirim metadata context chunks
        yield f"event: context\ndata: {json.dumps(context_data)}\n\n"

        assistant_text_parts: list[str] = []

        try:
            # Event 2: Streaming delta token
            async for chunk_token in stream_generate_answer(
                prompt=qa_prompt,
                system_instruction=SYSTEM_PROMPT_V1,
            ):
                assistant_text_parts.append(chunk_token)
                yield f"event: delta\ndata: {json.dumps({'delta': chunk_token})}\n\n"

            full_answer = "".join(assistant_text_parts).strip()
            _, validated_citations = validate_citations(full_answer, context_data)

            # Simpan pesan asisten ke database menggunakan session baru
            async with async_session_maker() as save_db:
                assistant_msg = Message(
                    id=uuid.uuid4(),
                    conversation_id=conv_id,
                    role="assistant",
                    content=full_answer,
                    citations=validated_citations,
                )
                save_db.add(assistant_msg)
                await save_db.commit()
                msg_id = str(assistant_msg.id)

            # Event 3: Selesai
            yield (
                f"event: done\ndata: {json.dumps({'message_id': msg_id, 'conversation_id': str(conv_id), 'citations': validated_citations})}\n\n"
            )

        except Exception as exc:
            logger.exception("Gagal menghasilkan streaming jawaban chat.")
            yield f"event: error\ndata: {json.dumps({'error': str(exc)})}\n\n"

    return StreamingResponse(
        sse_event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
