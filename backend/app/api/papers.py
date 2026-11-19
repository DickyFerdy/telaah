import uuid
from pathlib import Path
from typing import Annotated

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    HTTPException,
    UploadFile,
    status,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import get_current_user
from app.db.models import Paper, User
from app.db.session import get_db
from app.ingest.arxiv import (
    download_arxiv_pdf,
    fetch_arxiv_metadata,
    parse_arxiv_id,
)
from app.ingest.pipeline import run_ingest_pipeline
from app.ingest.validator import validate_pdf
from app.schemas.paper import ArxivImportRequest, PaperResponse

router = APIRouter(prefix="/papers", tags=["papers"])


@router.post(
    "",
    response_model=PaperResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_paper(
    file: Annotated[UploadFile, File(description="File PDF paper ilmiah")],
    background_tasks: BackgroundTasks,
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

    # 4. Enqueue background ingestion pipeline
    background_tasks.add_task(run_ingest_pipeline, paper.id)

    return PaperResponse.model_validate(paper)


@router.post(
    "/arxiv",
    response_model=PaperResponse,
    status_code=status.HTTP_201_CREATED,
)
async def import_arxiv_paper(
    payload: ArxivImportRequest,
    background_tasks: BackgroundTasks,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PaperResponse:
    # 1. Parse arXiv ID from user input (URL or raw ID)
    arxiv_id = parse_arxiv_id(payload.arxiv_url)

    # 2. Check if user already imported this arXiv paper
    existing_paper = await db.scalar(
        select(Paper).where(
            Paper.user_id == current_user.id,
            Paper.source_type == "arxiv",
            Paper.source_ref == arxiv_id,
        )
    )
    if existing_paper:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Paper arXiv '{arxiv_id}' sudah pernah diimpor",
        )

    # 3. Fetch metadata from arXiv API
    metadata = await fetch_arxiv_metadata(arxiv_id)

    # 4. Download PDF and validate magic bytes/size
    content = await download_arxiv_pdf(arxiv_id)

    # 5. Save PDF file
    paper_id = uuid.uuid4()
    user_storage_dir = Path(settings.storage_path) / str(current_user.id)
    user_storage_dir.mkdir(parents=True, exist_ok=True)

    dest_file_path = user_storage_dir / f"{paper_id}.pdf"
    dest_file_path.write_bytes(content)

    # 6. Create database record
    paper = Paper(
        id=paper_id,
        user_id=current_user.id,
        title=metadata.title,
        authors=metadata.authors,
        source_type="arxiv",
        source_ref=arxiv_id,
        file_path=str(dest_file_path),
        status="uploaded",
    )
    db.add(paper)
    await db.commit()
    await db.refresh(paper)

    # 7. Enqueue background ingestion pipeline
    background_tasks.add_task(run_ingest_pipeline, paper.id)

    return PaperResponse.model_validate(paper)


@router.get("", response_model=list[PaperResponse])
async def list_papers(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[PaperResponse]:
    query = (
        select(Paper)
        .where(Paper.user_id == current_user.id)
        .order_by(Paper.created_at.desc())
    )
    result = await db.execute(query)
    papers = result.scalars().all()
    return [PaperResponse.model_validate(p) for p in papers]


@router.get("/{paper_id}", response_model=PaperResponse)
async def get_paper(
    paper_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PaperResponse:
    query = select(Paper).where(
        Paper.id == paper_id, Paper.user_id == current_user.id
    )
    result = await db.execute(query)
    paper = result.scalar_one_or_none()
    if not paper:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Paper tidak ditemukan",
        )
    return PaperResponse.model_validate(paper)


@router.delete("/{paper_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_paper(
    paper_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    query = select(Paper).where(
        Paper.id == paper_id, Paper.user_id == current_user.id
    )
    result = await db.execute(query)
    paper = result.scalar_one_or_none()
    if not paper:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Paper tidak ditemukan",
        )

    # 1. Remove file on disk if it exists
    if paper.file_path:
        file_to_delete = Path(paper.file_path)
        if file_to_delete.exists():
            file_to_delete.unlink(missing_ok=True)

    # 2. Delete paper record in DB (cascades to chunks, summaries, conversations)
    await db.delete(paper)
    await db.commit()



