import json
import logging
import uuid
from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rate_limit import rate_limit_chat
from app.core.security import get_current_user
from app.db.models import Conversation, Message, Paper, User
from app.db.session import async_session_maker, get_db
from app.llm.citation import validate_citations
from app.llm.client import stream_generate_answer
from app.llm.not_found import NOT_FOUND_DEFAULT_MESSAGE, is_not_found_response
from app.llm.prompts import SYSTEM_PROMPT_V1, build_qa_prompt
from app.retrieval.hybrid import search_hybrid
from app.schemas.chat import ChatRequest, ConversationResponse, MessageResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/papers/{paper_id}/chat", tags=["chat"])


@router.post("", dependencies=[Depends(rate_limit_chat)])
async def chat_with_paper(
    paper_id: uuid.UUID,
    payload: ChatRequest,
    request: Request,
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

        # Jalur cepat: Jika tidak ada konteks teks sama sekali dari paper
        if not retrieved_chunks:
            yield f"event: delta\ndata: {json.dumps({'delta': NOT_FOUND_DEFAULT_MESSAGE})}\n\n"
            async with async_session_maker() as save_db:
                assistant_msg = Message(
                    id=uuid.uuid4(),
                    conversation_id=conv_id,
                    role="assistant",
                    content=NOT_FOUND_DEFAULT_MESSAGE,
                    citations=[],
                )
                save_db.add(assistant_msg)
                await save_db.commit()
                msg_id = str(assistant_msg.id)

            yield (
                f"event: done\ndata: {json.dumps({'message_id': msg_id, 'conversation_id': str(conv_id), 'citations': [], 'not_found': True})}\n\n"
            )
            return

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
            not_found = is_not_found_response(full_answer)
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
                f"event: done\ndata: {json.dumps({'message_id': msg_id, 'conversation_id': str(conv_id), 'citations': validated_citations, 'not_found': not_found})}\n\n"
            )

        except Exception as exc:
            logger.exception("Gagal menghasilkan streaming jawaban chat.")
            yield f"event: error\ndata: {json.dumps({'error': str(exc)})}\n\n"

    resp_headers = {
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",
    }
    if hasattr(request, "state") and hasattr(request.state, "rate_limit_headers"):
        resp_headers.update(request.state.rate_limit_headers)

    return StreamingResponse(
        sse_event_stream(),
        media_type="text/event-stream",
        headers=resp_headers,
    )


@router.get("/conversations", response_model=list[ConversationResponse])
async def list_conversations(
    paper_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[ConversationResponse]:
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

    # 2. Ambil semua percakapan untuk paper ini milik current_user
    stmt = (
        select(Conversation)
        .where(
            Conversation.paper_id == paper_id,
            Conversation.user_id == current_user.id,
        )
        .order_by(Conversation.created_at.desc())
    )
    result = await db.execute(stmt)
    conversations = result.scalars().all()

    response_list: list[ConversationResponse] = []
    for conv in conversations:
        msg_stmt = (
            select(Message)
            .where(Message.conversation_id == conv.id)
            .order_by(Message.created_at.asc())
        )
        msg_result = await db.execute(msg_stmt)
        messages = msg_result.scalars().all()

        preview = None
        for m in messages:
            if m.role == "user":
                preview = m.content[:80] + ("..." if len(m.content) > 80 else "")
                break

        response_list.append(
            ConversationResponse(
                id=conv.id,
                paper_id=conv.paper_id,
                user_id=conv.user_id,
                created_at=conv.created_at,
                message_count=len(messages),
                preview=preview,
            )
        )

    return response_list


@router.get(
    "/conversations/{conversation_id}/messages",
    response_model=list[MessageResponse],
)
async def get_conversation_messages(
    paper_id: uuid.UUID,
    conversation_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[MessageResponse]:
    # 1. Validasi percakapan
    conversation = await db.scalar(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.paper_id == paper_id,
            Conversation.user_id == current_user.id,
        )
    )
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Percakapan tidak ditemukan",
        )

    # 2. Ambil semua pesan
    stmt = (
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc())
    )
    result = await db.execute(stmt)
    messages = result.scalars().all()

    return [MessageResponse.model_validate(m) for m in messages]


@router.delete(
    "/conversations/{conversation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_conversation(
    paper_id: uuid.UUID,
    conversation_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    conversation = await db.scalar(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.paper_id == paper_id,
            Conversation.user_id == current_user.id,
        )
    )
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Percakapan tidak ditemukan",
        )

    await db.delete(conversation)
    await db.commit()
