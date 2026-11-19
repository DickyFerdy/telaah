import datetime
import uuid

from pydantic import BaseModel, ConfigDict, Field


class SummaryContent(BaseModel):
    research_question: str = Field(
        ..., description="Pertanyaan atau permasalahan penelitian utama"
    )
    method: str = Field(
        ..., description="Metodologi, pendekatan, atau arsitektur yang digunakan"
    )
    dataset: str = Field(
        ..., description="Dataset atau data eksperimental yang digunakan"
    )
    metrics: str = Field(..., description="Metrik evaluasi yang digunakan")
    results: str = Field(
        ..., description="Hasil utama dan temuan penting dari penelitian"
    )
    limitations: str = Field(
        ..., description="Keterbatasan penelitian atau batasan studi"
    )
    tldr: str | None = Field(
        default=None, description="Ringkasan 1-2 kalimat esensi paper"
    )


class SummaryResponse(BaseModel):
    id: uuid.UUID
    paper_id: uuid.UUID
    content: SummaryContent
    prompt_version: str | None = None
    created_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)
