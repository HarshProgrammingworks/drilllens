from sqlalchemy.orm import Session

from app.models import DrillingEvent, Evidence, Formation, HistoricalReport, Well


def search_all(db: Session, query: str, limit: int = 20) -> dict:
    """Universal cross-database search for wells, reports, events, evidence, and formations."""
    q = query.strip()
    if not q:
        return {"wells": [], "reports": [], "events": [], "evidence": [], "formations": []}

    like = f"%{q}%"

    wells_q = (
        db.query(Well)
        .filter(
            Well.is_archived.is_(False),
            (Well.well_name.ilike(like))
            | (Well.well_code.ilike(like))
            | (Well.field.ilike(like))
            | (Well.current_formation.ilike(like)),
        )
        .order_by(Well.well_name)
        .limit(limit)
        .all()
    )

    reports_q = (
        db.query(HistoricalReport)
        .filter(
            (HistoricalReport.title.ilike(like))
            | (HistoricalReport.report_type.ilike(like))
            | (HistoricalReport.original_filename.ilike(like))
        )
        .limit(limit)
        .all()
    )

    events_q = (
        db.query(DrillingEvent)
        .filter(
            (DrillingEvent.description.ilike(like))
            | (DrillingEvent.event_type.ilike(like))
            | (DrillingEvent.formation_name.ilike(like))
            | (DrillingEvent.risk_category.ilike(like))
        )
        .order_by(DrillingEvent.created_at.desc())
        .limit(limit)
        .all()
    )

    evidence_q = (
        db.query(Evidence)
        .filter((Evidence.text_excerpt.ilike(like)) | (Evidence.formation.ilike(like)))
        .limit(limit)
        .all()
    )

    formations_q = (
        db.query(Formation)
        .filter((Formation.name.ilike(like)) | (Formation.description.ilike(like)))
        .limit(limit)
        .all()
    )

    return {
        "query": q,
        "wells": [
            {
                "id": str(w.id),
                "well_code": w.well_code,
                "well_name": w.well_name,
                "field": w.field,
                "current_formation": w.current_formation,
                "status": w.status,
            }
            for w in wells_q
        ],
        "reports": [
            {
                "id": str(r.id),
                "title": r.title,
                "report_type": r.report_type,
                "status": r.status,
                "well_code": r.well.well_code if r.well else "",
                "well_name": r.well.well_name if r.well else "",
                "excerpt": r.title,
            }
            for r in reports_q
        ],
        "events": [
            {
                "id": str(e.id),
                "event_type": e.event_type,
                "risk_category": e.risk_category,
                "description": e.description,
                "depth_start": e.depth_start,
                "formation_name": e.formation_name,
                "event_date": str(e.event_date) if e.event_date else "",
                "report_id": str(e.report_id) if e.report_id else "",
                "well_code": e.well.well_code if e.well else "",
                "well_name": e.well.well_name if e.well else "",
                "well_id": str(e.well_id) if e.well_id else "",
                "page_number": 1,
            }
            for e in events_q
        ],
        "evidence": [
            {
                "id": str(ev.id),
                "text_excerpt": ev.text_excerpt,
                "formation": ev.formation,
                "depth_start": ev.depth_start,
                "confidence": ev.confidence,
                "source_type": ev.source_type,
                "well_code": ev.well.well_code if ev.well else "",
                "well_name": ev.well.well_name if ev.well else "",
                "report_title": ev.report.title if ev.report else "",
                "page_number": 1,
            }
            for ev in evidence_q
        ],
        "formations": [
            {"id": str(f.id), "name": f.name, "description": f.description} for f in formations_q
        ],
        "engine": "universal_orm_search",
        "future": "Interface is isolated in search_service so Elasticsearch, OpenSearch, or a vector index can replace the SQL.",
    }
