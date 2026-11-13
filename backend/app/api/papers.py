import uuid
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import get_current_user
from app.db.models import Paper, User
from app.db.session import get_db
from app.ingest.validator import validate_pdf
from app.schemas.paper import PaperResponse

router = APIRouter(prefix="/papers", tags=["papers"])


@router.post(
    "",
    response_model=PaperResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_paper(
    file: Annotated[UploadFile, File(description="File PDF paper ilmiah")],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PaperResponse:
    # 1. Validate the PDF file (extension, MIME, magic bytes, size)
    content = await validate_pdf(file)

    # 2. Generate unique paper ID and determine storage destination
    paper_id = uuid.uuid4()
    user_storage_dir = Path(settings.storage_path) / str(current_user.id)
    user_storage_dir.mkdir(parents=True, exist_ok=True)

    dest_file_path = user_storage_dir / f"{paper_id}.pdf"
    dest_file_path.write_bytes(content)

    # 3. Create database record
    paper = Paper(
        id=paper_id,
        user_id=current_user.id,
        title=None,
        authors=None,
        source_type="upload",
        source_ref=file.filename,
        file_path=str(dest_file_path),
        status="uploaded",
    )
    db.add(paper)
    await db.commit()
    await db.refresh(paper)

    return PaperResponse.model_validate(paper)

