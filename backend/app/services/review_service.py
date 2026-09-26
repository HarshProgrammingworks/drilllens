from sqlalchemy.orm import Session, joinedload

from app.models import EngineeringReview


def serialize_review(row: EngineeringReview) -> dict:
    return {
        "id": str(row.id),
        "well_id": str(row.well_id) if row.well_id else None,
        "well_code": row.well.well_code if row.well else None,
        "well_name": row.well.well_name if row.well else None,
        "alert_id": str(row.alert_id) if row.alert_id else None,
        "engineer_id": str(row.engineer_id),
        "engineer_name": row.engineer.full_name if row.engineer else None,
        "decision": row.decision,
        "comment": row.comment,
        "risk_category": row.risk_category,
        "snapshot": row.snapshot,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


def list_reviews(db: Session, well_id=None, alert_id=None):
    query = db.query(EngineeringReview).options(
        joinedload(EngineeringReview.engineer),
        joinedload(EngineeringReview.well),
        joinedload(EngineeringReview.alert),
    )
    if well_id:
        query = query.filter(EngineeringReview.well_id == well_id)
    if alert_id:
        query = query.filter(EngineeringReview.alert_id == alert_id)
    return query.order_by(EngineeringReview.created_at.desc()).all()
