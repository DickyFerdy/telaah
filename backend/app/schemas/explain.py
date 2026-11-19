from pydantic import BaseModel, Field


class ExplainTermRequest(BaseModel):
    term: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Istilah atau frasa ilmiah yang ingin dijelaskan",
    )
    context: str | None = Field(
        default=None,
        max_length=2000,
        description="Potongan kalimat atau konteks sekitar istilah di paper",
    )


class ExplainTermResponse(BaseModel):
    term: str
    explanation: str
    context: str | None = None
