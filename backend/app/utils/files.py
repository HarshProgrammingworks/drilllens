import re
from pathlib import Path

from fastapi import HTTPException, UploadFile

ALLOWED_EXTENSIONS = {".pdf", ".txt", ".csv"}
PDF_MAGIC = b"%PDF"


def safe_extension(filename: str) -> str:
    name = Path(filename or "").name
    ext = Path(name).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "Only PDF, TXT, and CSV reports are accepted.",
                "error_code": "INVALID_FILE_TYPE",
            },
        )
    return ext


def stored_name(ext: str) -> str:
    from uuid import uuid4

    return f"{uuid4().hex}{ext}"


def assert_inside(root: Path, target: Path) -> Path:
    root_r = root.resolve()
    target_r = target.resolve()
    if root_r != target_r and root_r not in target_r.parents:
        raise HTTPException(
            status_code=400,
            detail={"message": "Invalid storage path.", "error_code": "PATH_TRAVERSAL"},
        )
    return target_r


def validate_upload(file: UploadFile, content: bytes, max_mb: int) -> str:
    ext = safe_extension(file.filename or "")
    if len(content) == 0:
        raise HTTPException(
            status_code=400,
            detail={"message": "The uploaded file is empty.", "error_code": "EMPTY_FILE"},
        )
    if len(content) > max_mb * 1024 * 1024:
        raise HTTPException(
            status_code=413,
            detail={
                "message": f"File exceeds the {max_mb} MB limit.",
                "error_code": "FILE_TOO_LARGE",
            },
        )
    if ext == ".pdf" and not content.startswith(PDF_MAGIC):
        raise HTTPException(
            status_code=400,
            detail={"message": "File is not a valid PDF.", "error_code": "INVALID_PDF"},
        )
    if ext in {".txt", ".csv"}:
        try:
            content.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise HTTPException(
                status_code=400,
                detail={"message": "Text reports must be UTF-8.", "error_code": "INVALID_ENCODING"},
            ) from exc
    if re.search(r"[\\/]", file.filename or ""):
        # Original name is metadata only; storage name is generated.
        pass
    return ext
