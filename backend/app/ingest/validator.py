from fastapi import HTTPException, UploadFile, status

MAX_FILE_SIZE_BYTES = 20 * 1024 * 1024  # 20 MB
PDF_MAGIC_BYTES = b"%PDF-"


async def validate_pdf(
    file: UploadFile,
    max_size_bytes: int = MAX_FILE_SIZE_BYTES,
) -> bytes:
    # 1. Check filename extension
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File harus memiliki ekstensi .pdf",
        )

    # 2. Check content-type header (MIME type)
    if file.content_type and file.content_type.lower() != "application/pdf":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tipe konten file harus application/pdf",
        )

    # 3. Read content in chunks to check size and magic bytes safely
    content_chunks: list[bytes] = []
    total_size = 0
    chunk_size = 1024 * 1024  # 1 MB chunk

    while chunk := await file.read(chunk_size):
        total_size += len(chunk)
        if total_size > max_size_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                detail=f"Ukuran file melebihi batas maksimal {max_size_bytes // (1024 * 1024)} MB",
            )
        content_chunks.append(chunk)

    if total_size == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File PDF kosong",
        )

    full_content = b"".join(content_chunks)

    # 4. Check magic bytes
    if not full_content.startswith(PDF_MAGIC_BYTES):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File bukan dokumen PDF yang valid (tanda tangan magic bytes tidak cocok)",
        )

    return full_content
