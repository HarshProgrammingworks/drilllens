from uuid import UUID

from sqlalchemy.orm import Session, joinedload

from app.models import Evidence


def get_evidence(db: Session, evidence_id: UUID) -> Evidence | None:
    return (
        db.query(Evidence)
        .options(joinedload(Evidence.report), joinedload(Evidence.well), joinedload(Evidence.event))
        .filter(Evidence.id == evidence_id)
        .one_or_none()
    )


def serialize_evidence(row: Evidence) -> dict:
    page_number = None
    if row.event and row.event.page_id and row.source_location:
        page_number = row.source_location
    return {
        "id": str(row.id),
        "source_type": row.source_type,
        "report_id": str(row.report_id) if row.report_id else None,
        "report_title": row.report.title if row.report else None,
        "report_type": row.report.report_type if row.report else None,
        "page_id": str(row.page_id) if row.page_id else None,
        "source_location": row.source_location,
        "well_id": str(row.well_id) if row.well_id else None,
        "well_code": row.well.well_code if row.well else None,
        "well_name": row.well.well_name if row.well else None,
        "event_id": str(row.event_id) if row.event_id else None,
        "event_type": row.event.event_type if row.event else None,
        "event_description": row.event.description if row.event else None,
        "action_taken": row.event.action_taken if row.event else None,
        "outcome": row.event.outcome if row.event else None,
        "depth_start": row.depth_start,
        "depth_end": row.depth_end,
        "formation": row.formation,
        "text_excerpt": row.text_excerpt,
        "confidence": row.confidence,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "provenance": row.source_type,
    }
