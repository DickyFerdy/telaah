import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class PaperResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    title: str | None = None
    authors: list[str] | None = None
    source_type: str | None = None
    source_ref: str | None = None
    file_path: str
    status: str
    error_message: str | None = None
    page_count: int | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

