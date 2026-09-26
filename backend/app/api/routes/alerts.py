from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session, joinedload

from app.api.dependencies import ROLE_ADMIN, ROLE_ENGINEER, get_current_user, require_roles
from app.core.database import get_db
from app.models import Alert, User
from app.schemas.domain import AlertAction
from app.services.alert_service import apply_action
from app.utils.audit import write_audit
from app.utils.pagination import page_window

router = APIRouter(prefix="/alerts", tags=["alerts"])


def _serialize(alert: Alert) -> dict:
    return {
        "id": str(alert.id),
        "well_id": str(alert.well_id),
        "well_code": alert.well.well_code if alert.well else None,
        "well_name": alert.well.well_name if alert.well else None,
        "risk_category": alert.risk_category,
        "severity": alert.severity,
        "title": alert.title,
        "description": alert.description,
        "score": alert.score,
        "trigger_source": alert.trigger_source,
        "status": alert.status,
        "note": alert.note,
        "created_at": alert.created_at.isoformat() if alert.created_at else None,
        "updated_at": alert.updated_at.isoformat() if alert.updated_at else None,
        "acknowledged_at": alert.acknowledged_at.isoformat() if alert.acknowledged_at else None,
        "acknowledged_by": str(alert.acknowledged_by) if alert.acknowledged_by else None,
        "escalated_at": alert.escalated_at.isoformat() if alert.escalated_at else None,
    }


@router.get("")
def list_alerts(
    status: str | None = None,
    well_id: str | None = None,
    severity: str | None = None,
    page: int = 1,
    page_size: int = 30,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(Alert)
    if status:
        query = query.filter(Alert.status == status)
    if severity:
        query = query.filter(Alert.severity == severity)
    if well_id:
        from app.services.well_service import get_well

        well = get_well(db, well_id)
        if well:
            query = query.filter(Alert.well_id == well.id)
    total = query.count()
    offset, limit = page_window(page, page_size)
    rows = query.options(joinedload(Alert.well)).order_by(Alert.created_at.desc()).offset(offset).limit(limit).all()
    return {"success": True, "data": {"items": [_serialize(r) for r in rows], "total": total, "page": page}, "message": None}


@router.get("/{alert_id}")
def get_alert(alert_id: UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    alert = db.query(Alert).options(joinedload(Alert.well)).filter(Alert.id == alert_id).one_or_none()
    if alert is None:
        raise HTTPException(status_code=404, detail={"message": "Alert not found.", "error_code": "RESOURCE_NOT_FOUND"})
    return {"success": True, "data": _serialize(alert), "message": None}


def _act(action: str):
    def endpoint(
        alert_id: UUID,
        body: AlertAction,
        request: Request,
        user: User = Depends(require_roles(ROLE_ADMIN, ROLE_ENGINEER)),
        db: Session = Depends(get_db),
    ):
        alert = db.query(Alert).options(joinedload(Alert.well)).filter(Alert.id == alert_id).one_or_none()
        if alert is None:
            raise HTTPException(status_code=404, detail={"message": "Alert not found.", "error_code": "RESOURCE_NOT_FOUND"})
        apply_action(db, alert, action, user.id, body.note)
        audit_action = {
            "acknowledge": "ALERT_ACKNOWLEDGE",
            "review": "ALERT_REVIEW",
            "escalate": "ALERT_ESCALATE",
            "false_positive": "ALERT_FALSE_POSITIVE",
            "note": "ALERT_NOTE",
        }[action]
        write_audit(db, user_id=user.id, action=audit_action, resource="alert", resource_id=str(alert.id), request=request)
        db.commit()
        db.refresh(alert)
        return {"success": True, "data": _serialize(alert), "message": "Alert updated."}

    endpoint.__name__ = f"alert_{action}"
    return endpoint


router.post("/{alert_id}/acknowledge")(_act("acknowledge"))
router.post("/{alert_id}/review")(_act("review"))
router.post("/{alert_id}/escalate")(_act("escalate"))
router.post("/{alert_id}/false-positive")(_act("false_positive"))
router.post("/{alert_id}/note")(_act("note"))
