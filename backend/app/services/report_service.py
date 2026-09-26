from datetime import datetime
from pathlib import Path
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.logging import log
from app.models import (
    DrillingEvent,
    Evidence,
    Formation,
    HistoricalReport,
    NlpEntity,
    Notification,
    OcrResult,
    ReportPage,
    Well,
)
from app.services.nlp_service import extract_entities, extract_events
from app.services.ocr_service import extract_csv_file, extract_pdf, extract_text_file

STATUS_PROGRESS = {
    "UPLOADED": 10,
    "OCR_PROCESSING": 30,
    "NLP_PROCESSING": 55,
    "STRUCTURING": 75,
    "INDEXING": 90,
    "COMPLETED": 100,
    "FAILED": 0,
}


def set_status(db: Session, report: HistoricalReport, status: str, error: str | None = None) -> None:
    report.status = status
    report.error_message = error
    report.updated_at = datetime.utcnow()
    db.commit()


def _formation(db: Session, name: str | None) -> Formation | None:
    if not name:
        return None
    row = db.query(Formation).filter(func.lower(Formation.name) == name.lower()).one_or_none()
    if row is None:
        row = Formation(name=name, description="Created from report extraction")
        db.add(row)
        db.flush()
    return row


def process_report(db: Session, report_id: UUID) -> HistoricalReport:
    report = db.get(HistoricalReport, report_id)
    if report is None:
        raise ValueError("Report not found")
    path = Path(report.storage_path)
    try:
        suffix = path.suffix.lower()
        set_status(db, report, "OCR_PROCESSING")
        if suffix == ".pdf":
            pages = extract_pdf(path)
        elif suffix == ".csv":
            pages = extract_csv_file(path)
        else:
            pages = extract_text_file(path)

        db.query(ReportPage).filter(ReportPage.report_id == report.id).delete()
        db.query(OcrResult).filter(OcrResult.report_id == report.id).delete()
        db.query(NlpEntity).filter(NlpEntity.report_id == report.id).delete()
        db.query(Evidence).filter(Evidence.report_id == report.id).delete()
        db.query(DrillingEvent).filter(DrillingEvent.report_id == report.id).delete()
        db.flush()

        page_rows: list[ReportPage] = []
        for page in pages:
            row = ReportPage(
                report_id=report.id,
                page_number=page.page_number,
                text_content=page.text,
                is_scanned=page.is_scanned,
                char_count=page.char_count,
            )
            db.add(row)
            db.flush()
            page_rows.append(row)
            if page.is_scanned:
                db.add(
                    OcrResult(
                        report_id=report.id,
                        page_id=row.id,
                        page_number=page.page_number,
                        raw_ocr_text=page.text,
                        confidence=page.ocr_confidence,
                        processing_time=page.processing_time,
                        status=page.ocr_status or "COMPLETED",
                    )
                )
        report.page_count = len(page_rows)
        db.commit()

        set_status(db, report, "NLP_PROCESSING")
        full_text = "\n".join(p.text_content for p in page_rows)
        date_hint = report.report_date.isoformat() if report.report_date else None
        for page in page_rows:
            for entity in extract_entities(page.text_content):
                db.add(
                    NlpEntity(
                        report_id=report.id,
                        page_id=page.id,
                        entity_type=entity.entity_type,
                        text=entity.text,
                        normalized_value=entity.normalized_value,
                        confidence=entity.confidence,
                        extractor=entity.extractor,
                        start_char=entity.start_char,
                        end_char=entity.end_char,
                    )
                )
        events = extract_events(full_text, date_hint)
        set_status(db, report, "STRUCTURING")
        page_for_text = {p.text_content: p for p in page_rows}
        for event in events:
            page = next((p for p in page_rows if event.description and event.description in (p.text_content or "")), page_rows[0] if page_rows else None)
            formation = _formation(db, event.formation)
            event_date = None
            if event.event_date:
                try:
                    event_date = datetime.fromisoformat(event.event_date).date()
                except ValueError:
                    event_date = report.report_date
            else:
                event_date = report.report_date
            row = DrillingEvent(
                well_id=report.well_id,
                report_id=report.id,
                page_id=page.id if page else None,
                depth_start=event.depth_start,
                depth_end=event.depth_end,
                formation_id=formation.id if formation else None,
                formation_name=event.formation,
                event_type=event.event_type,
                description=event.description,
                action_taken=event.action_taken,
                outcome=event.outcome,
                risk_category=event.risk_category,
                event_date=event_date,
                confidence=event.confidence,
                source_type="NLP_EXTRACTED" if report.source_type != "DEMO" else "DEMO",
            )
            db.add(row)
            db.flush()
            db.add(
                Evidence(
                    source_type=row.source_type,
                    report_id=report.id,
                    page_id=page.id if page else None,
                    well_id=report.well_id,
                    event_id=row.id,
                    depth_start=event.depth_start,
                    depth_end=event.depth_end,
                    formation=event.formation,
                    text_excerpt=event.description,
                    source_location=f"page {page.page_number}" if page else report.original_filename,
                    confidence=event.confidence,
                )
            )
        db.commit()

        set_status(db, report, "INDEXING")
        _index(db, report)
        report.status = "COMPLETED"
        report.error_message = None
        db.add(
            Notification(
                type="REPORT_COMPLETED",
                title=f"Report processing completed: {report.title}",
                body=f"{report.page_count} page(s) processed.",
                link=f"/reports/{report.id}",
            )
        )
        db.commit()
        db.refresh(report)
        return report
    except Exception as exc:
        log.exception("Report processing failed")
        db.rollback()
        report = db.get(HistoricalReport, report_id)
        if report:
            report.status = "FAILED"
            report.error_message = str(exc)[:1000]
            db.add(
                Notification(
                    type="REPORT_FAILED",
                    title=f"Report processing failed: {report.title}",
                    body=report.error_message,
                    link=f"/reports/{report.id}",
                )
            )
            db.commit()
        raise


def _index(db: Session, report: HistoricalReport) -> None:
    from sqlalchemy import text

    db.execute(
        text(
            """
            UPDATE historical_reports
            SET search_vector = to_tsvector('english', coalesce(title,'') || ' ' || coalesce(report_type,''))
            WHERE id = :id
            """
        ),
        {"id": report.id},
    )
    db.execute(
        text(
            """
            UPDATE report_pages
            SET search_vector = to_tsvector('english', coalesce(text_content, ''))
            WHERE report_id = :id
            """
        ),
        {"id": report.id},
    )
    db.execute(
        text(
            """
            UPDATE drilling_events
            SET search_vector = to_tsvector('english',
                coalesce(description,'') || ' ' || coalesce(event_type,'') || ' ' ||
                coalesce(risk_category,'') || ' ' || coalesce(formation_name,'') || ' ' ||
                coalesce(action_taken,'') || ' ' || coalesce(outcome,''))
            WHERE report_id = :id
            """
        ),
        {"id": report.id},
    )
    db.execute(
        text(
            """
            UPDATE evidence
            SET search_vector = to_tsvector('english', coalesce(text_excerpt,'') || ' ' || coalesce(formation,''))
            WHERE report_id = :id
            """
        ),
        {"id": report.id},
    )
    db.commit()


def report_progress(report: HistoricalReport) -> dict:
    return {
        "status": report.status,
        "progress": STATUS_PROGRESS.get(report.status, 0),
        "error_message": report.error_message,
    }


def link_well(db: Session, report: HistoricalReport) -> Well | None:
    if report.well_id is None:
        return None
    return db.get(Well, report.well_id)
