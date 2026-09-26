from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session, joinedload

from app.api.dependencies import ROLE_ADMIN, ROLE_ENGINEER, get_current_user, require_roles
from app.core.config import get_settings
from app.core.database import SessionLocal, get_db
from app.models import HistoricalReport, NlpEntity, OcrResult, ReportPage, User
from app.services.report_service import process_report, report_progress
from app.services.well_service import get_well
from app.utils.audit import write_audit
from app.utils.files import assert_inside, stored_name, validate_upload
from app.utils.pagination import page_window

router = APIRouter(prefix="/reports", tags=["reports"])


def _run_process(report_id: str) -> None:
    db = SessionLocal()
    try:
        process_report(db, UUID(report_id))
    except Exception:
        pass
    finally:
        db.close()


def _serialize(report: HistoricalReport) -> dict:
    progress = report_progress(report)
    return {
        "id": str(report.id),
        "title": report.title,
        "report_type": report.report_type,
        "original_filename": report.original_filename,
        "status": report.status,
        "progress": progress["progress"],
        "error_message": report.error_message,
        "page_count": report.page_count,
        "file_size": report.file_size,
        "well_id": str(report.well_id) if report.well_id else None,
        "well_code": report.well.well_code if report.well else None,
        "well_name": report.well.well_name if report.well else None,
        "report_date": report.report_date.isoformat() if report.report_date else None,
        "source_type": report.source_type,
        "created_at": report.created_at.isoformat() if report.created_at else None,
        "updated_at": report.updated_at.isoformat() if report.updated_at else None,
    }


@router.get("")
def list_reports(
    q: str | None = None,
    status: str | None = None,
    report_type: str | None = None,
    well_id: str | None = None,
    page: int = 1,
    page_size: int = 20,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(HistoricalReport)
    if status:
        query = query.filter(HistoricalReport.status == status)
    if report_type:
        query = query.filter(HistoricalReport.report_type == report_type)
    if well_id:
        well = get_well(db, well_id)
        if well:
            query = query.filter(HistoricalReport.well_id == well.id)
    if q:
        like = f"%{q}%"
        query = query.filter(HistoricalReport.title.ilike(like))
    total = query.count()
    offset, limit = page_window(page, page_size)
    rows = query.options(joinedload(HistoricalReport.well)).order_by(HistoricalReport.created_at.desc()).offset(offset).limit(limit).all()
    return {"success": True, "data": {"items": [_serialize(r) for r in rows], "total": total, "page": page, "page_size": page_size}, "message": None}


@router.get("/stats")
def stats(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.query(HistoricalReport.status, HistoricalReport.report_type).all()
    by_status: dict[str, int] = {}
    by_type: dict[str, int] = {}
    for status, report_type in rows:
        by_status[status] = by_status.get(status, 0) + 1
        by_type[report_type] = by_type.get(report_type, 0) + 1
    return {"success": True, "data": {"total": len(rows), "by_status": by_status, "by_type": by_type}, "message": None}


@router.post("/upload")
async def upload(
    request: Request,
    background: BackgroundTasks,
    file: UploadFile = File(...),
    title: str = Form(...),
    report_type: str = Form("WCR"),
    well_id: str | None = Form(None),
    report_date: str | None = Form(None),
    user: User = Depends(require_roles(ROLE_ADMIN, ROLE_ENGINEER)),
    db: Session = Depends(get_db),
):
    settings = get_settings()
    if report_type not in {"WCR", "DDR", "OTHER"}:
        raise HTTPException(status_code=422, detail={"message": "Report type must be WCR, DDR, or OTHER.", "error_code": "VALIDATION_ERROR"})
    content = await file.read()
    ext = validate_upload(file, content, settings.max_upload_size_mb)
    well = get_well(db, well_id) if well_id else None
    if well_id and well is None:
        raise HTTPException(status_code=404, detail={"message": "Well not found.", "error_code": "RESOURCE_NOT_FOUND"})
    root = Path(settings.upload_directory) / "reports"
    root.mkdir(parents=True, exist_ok=True)
    name = stored_name(ext)
    target = assert_inside(root, root / name)
    target.write_bytes(content)
    parsed_date = None
    if report_date:
        from datetime import date
        try:
            parsed_date = date.fromisoformat(report_date)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail={"message": "report_date must be YYYY-MM-DD.", "error_code": "VALIDATION_ERROR"}) from exc
    report = HistoricalReport(
        well_id=well.id if well else None,
        title=title.strip(),
        report_type=report_type,
        original_filename=Path(file.filename or name).name,
        storage_path=str(target),
        status="UPLOADED",
        file_size=len(content),
        uploaded_by=user.id,
        report_date=parsed_date,
        source_type="ENGINEER_ENTERED",
    )
    db.add(report)
    db.flush()
    write_audit(
        db,
        user_id=user.id,
        action="REPORT_UPLOAD",
        resource="report",
        resource_id=str(report.id),
        request=request,
        metadata={"filename": report.original_filename, "bytes": len(content)},
    )
    db.commit()
    background.add_task(_run_process, str(report.id))
    db.refresh(report)
    return {"success": True, "data": _serialize(report), "message": "Upload stored. Processing started."}


@router.get("/{report_id}")
def detail(report_id: UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    report = db.query(HistoricalReport).options(joinedload(HistoricalReport.well)).filter(HistoricalReport.id == report_id).one_or_none()
    if report is None:
        raise HTTPException(status_code=404, detail={"message": "Report not found.", "error_code": "RESOURCE_NOT_FOUND"})
    return {"success": True, "data": _serialize(report), "message": None}


@router.get("/{report_id}/pages")
def pages(report_id: UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.query(ReportPage).filter(ReportPage.report_id == report_id).order_by(ReportPage.page_number).all()
    return {
        "success": True,
        "data": [
            {
                "id": str(row.id),
                "page_number": row.page_number,
                "text_content": row.text_content,
                "is_scanned": row.is_scanned,
                "char_count": row.char_count,
            }
            for row in rows
        ],
        "message": None,
    }


@router.get("/{report_id}/ocr")
def ocr(report_id: UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.query(OcrResult).filter(OcrResult.report_id == report_id).order_by(OcrResult.page_number).all()
    return {
        "success": True,
        "data": [
            {
                "page_number": row.page_number,
                "raw_ocr_text": row.raw_ocr_text,
                "confidence": row.confidence,
                "processing_time": row.processing_time,
                "status": row.status,
            }
            for row in rows
        ],
        "message": None,
    }


@router.get("/{report_id}/entities")
def entities(report_id: UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.query(NlpEntity).filter(NlpEntity.report_id == report_id).order_by(NlpEntity.entity_type).all()
    return {
        "success": True,
        "data": [
            {
                "id": str(row.id),
                "entity_type": row.entity_type,
                "text": row.text,
                "normalized_value": row.normalized_value,
                "confidence": row.confidence,
                "extractor": row.extractor,
            }
            for row in rows
        ],
        "message": None,
    }


@router.post("/{report_id}/process")
def reprocess(
    report_id: UUID,
    request: Request,
    background: BackgroundTasks,
    user: User = Depends(require_roles(ROLE_ADMIN, ROLE_ENGINEER)),
    db: Session = Depends(get_db),
):
    report = db.get(HistoricalReport, report_id)
    if report is None:
        raise HTTPException(status_code=404, detail={"message": "Report not found.", "error_code": "RESOURCE_NOT_FOUND"})
    report.status = "UPLOADED"
    write_audit(db, user_id=user.id, action="REPORT_PROCESS", resource="report", resource_id=str(report.id), request=request)
    db.commit()
    background.add_task(_run_process, str(report.id))
    return {"success": True, "data": _serialize(report), "message": "Processing restarted."}


@router.get("/{report_id}/file")
def download(report_id: UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    report = db.get(HistoricalReport, report_id)
    if report is None:
        raise HTTPException(status_code=404, detail={"message": "Report not found.", "error_code": "RESOURCE_NOT_FOUND"})
    settings = get_settings()
    path = assert_inside(Path(settings.upload_directory), Path(report.storage_path))
    if not path.exists():
        raise HTTPException(status_code=404, detail={"message": "Stored file is missing.", "error_code": "FILE_MISSING"})
    return FileResponse(path, filename=report.original_filename)
