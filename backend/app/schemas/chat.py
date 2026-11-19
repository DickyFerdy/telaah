import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class ChatRequest(BaseModel):
    message: str
    conversation_id: uuid.UUID | None = None


class ContextChunkItem(BaseModel):
    index: int  # 1-based index corresponding to [1], [2], etc.
    chunk_id: uuid.UUID
    section: str | None
    page_start: int | None
    page_end: int | None
    text: str
    bbox: dict[str, Any] | None
    similarity_score: float


class MessageResponse(BaseModel):
    id: uuid.UUID
    conversation_id: uuid.UUID
    role: str
    content: str
    citations: list[dict[str, Any]] | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ConversationResponse(BaseModel):
    id: uuid.UUID
    paper_id: uuid.UUID
    user_id: uuid.UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
