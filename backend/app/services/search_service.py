from sqlalchemy import text
from sqlalchemy.orm import Session


def search_all(db: Session, query: str, limit: int = 20) -> dict:
    """PostgreSQL full-text search with ILIKE fallback for short engineering phrases."""
    q = query.strip()
    if not q:
        return {"wells": [], "reports": [], "events": [], "evidence": [], "formations": []}

    wells = db.execute(
        text(
            """
            SELECT id::text, well_code, well_name, field, current_formation, status
            FROM wells
            WHERE is_archived = false
              AND (
                well_name ILIKE :like OR well_code ILIKE :like OR field ILIKE :like
                OR current_formation ILIKE :like
              )
            ORDER BY well_name
            LIMIT :limit
            """
        ),
        {"like": f"%{q}%", "limit": limit},
    ).mappings().all()

    reports = db.execute(
        text(
            """
            SELECT r.id::text, r.title, r.report_type, r.status, w.well_code, w.well_name,
                   ts_headline('english', coalesce(p.text_content, ''), plainto_tsquery('english', :q)) AS excerpt
            FROM historical_reports r
            LEFT JOIN wells w ON w.id = r.well_id
            LEFT JOIN LATERAL (
                SELECT text_content FROM report_pages
                WHERE report_id = r.id
                ORDER BY page_number LIMIT 1
            ) p ON true
            WHERE r.search_vector @@ plainto_tsquery('english', :q)
               OR r.title ILIKE :like
               OR coalesce(p.text_content, '') ILIKE :like
            LIMIT :limit
            """
        ),
        {"q": q, "like": f"%{q}%", "limit": limit},
    ).mappings().all()

    events = db.execute(
        text(
            """
            SELECT e.id::text, e.event_type, e.risk_category, e.description, e.depth_start,
                   e.formation_name, e.event_date::text AS event_date, e.report_id::text,
                   w.well_code, w.well_name, w.id::text AS well_id,
                   rp.page_number
            FROM drilling_events e
            LEFT JOIN wells w ON w.id = e.well_id
            LEFT JOIN report_pages rp ON rp.id = e.page_id
            WHERE e.search_vector @@ plainto_tsquery('english', :q)
               OR e.description ILIKE :like
               OR e.event_type ILIKE :like
               OR coalesce(e.risk_category, '') ILIKE :like
               OR coalesce(e.formation_name, '') ILIKE :like
               OR coalesce(w.well_name, '') ILIKE :like
               OR coalesce(w.field, '') ILIKE :like
            ORDER BY e.created_at DESC
            LIMIT :limit
            """
        ),
        {"q": q, "like": f"%{q}%", "limit": limit},
    ).mappings().all()

    evidence = db.execute(
        text(
            """
            SELECT ev.id::text, ev.text_excerpt, ev.formation, ev.depth_start, ev.confidence,
                   ev.source_type, w.well_code, w.well_name, r.title AS report_title, rp.page_number
            FROM evidence ev
            LEFT JOIN wells w ON w.id = ev.well_id
            LEFT JOIN historical_reports r ON r.id = ev.report_id
            LEFT JOIN report_pages rp ON rp.id = ev.page_id
            WHERE ev.search_vector @@ plainto_tsquery('english', :q)
               OR ev.text_excerpt ILIKE :like
               OR coalesce(ev.formation, '') ILIKE :like
            LIMIT :limit
            """
        ),
        {"q": q, "like": f"%{q}%", "limit": limit},
    ).mappings().all()

    formations = db.execute(
        text(
            """
            SELECT id::text, name, description
            FROM formations
            WHERE name ILIKE :like OR coalesce(description, '') ILIKE :like
            LIMIT :limit
            """
        ),
        {"like": f"%{q}%", "limit": limit},
    ).mappings().all()

    return {
        "query": q,
        "wells": [dict(r) for r in wells],
        "reports": [dict(r) for r in reports],
        "events": [dict(r) for r in events],
        "evidence": [dict(r) for r in evidence],
        "formations": [dict(r) for r in formations],
        "engine": "postgresql_full_text",
        "future": "Interface is isolated in search_service so Elasticsearch, OpenSearch, or a vector index can replace the SQL.",
    }
