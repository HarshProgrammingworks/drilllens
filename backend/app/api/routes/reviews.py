from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session, joinedload

from app.api.dependencies import ROLE_ADMIN, ROLE_ENGINEER, get_current_user, require_roles
from app.core.database import get_db
from app.models import Alert, EngineeringReview, User
from app.schemas.domain import ReviewIn, ReviewUpdate
from app.services.alert_service import apply_action
from app.services.review_service import list_reviews, serialize_review
from app.services.risk_service import latest_risks
from app.services.well_service import get_well
from app.utils.audit import write_audit

router = APIRouter(prefix="/reviews", tags=["reviews"])

DECISIONS = {"ACKNOWLEDGE", "REVIEW", "COMMENT", "FALSE_POSITIVE", "ESCALATE"}


@router.get("")
def reviews(well_id: str | None = None, alert_id: UUID | None = None, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    well_uuid = None
    if well_id:
        well = get_well(db, well_id)
        if well is None:
            raise HTTPException(status_code=404, detail={"message": "Well not found.", "error_code": "RESOURCE_NOT_FOUND"})
        well_uuid = well.id
    rows = list_reviews(db, well_id=well_uuid, alert_id=alert_id)
    return {"success": True, "data": [serialize_review(row) for row in rows], "message": None}


@router.post("")
def create_review(
    body: ReviewIn,
    request: Request,
    user: User = Depends(require_roles(ROLE_ADMIN, ROLE_ENGINEER)),
    db: Session = Depends(get_db),
):
    if body.decision not in DECISIONS:
        raise HTTPException(status_code=422, detail={"message": "Unknown review decision.", "error_code": "VALIDATION_ERROR"})
    well = get_well(db, str(body.well_id)) if body.well_id else None
    alert = None
    if body.alert_id:
        alert = db.query(Alert).options(joinedload(Alert.well)).filter(Alert.id == body.alert_id).one_or_none()
        if alert is None:
            raise HTTPException(status_code=404, detail={"message": "Alert not found.", "error_code": "RESOURCE_NOT_FOUND"})
        action = {
            "ACKNOWLEDGE": "acknowledge",
            "REVIEW": "review",
            "COMMENT": "note",
            "FALSE_POSITIVE": "false_positive",
            "ESCALATE": "escalate",
        }[body.decision]
        apply_action(db, alert, action, user.id, body.comment)
        if well is None:
            well = alert.well
    snapshot = {}
    if well:
        snapshot = {"risks": latest_risks(db, well.id), "well_id": well.well_code, "depth": well.current_depth, "formation": well.current_formation}
    review = EngineeringReview(
        well_id=well.id if well else None,
        alert_id=alert.id if alert else body.alert_id,
        engineer_id=user.id,
        decision=body.decision,
        comment=body.comment,
        risk_category=body.risk_category,
        snapshot=snapshot,
    )
    db.add(review)
    write_audit(
        db,
        user_id=user.id,
        action="RISK_REVIEW",
        resource="engineering_review",
        resource_id=str(review.id) if review.id else None,
        request=request,
        metadata={"decision": body.decision},
    )
    db.commit()
    db.refresh(review)
    review = list_reviews(db, well_id=review.well_id)[0] if review.well_id else review
    if not getattr(review, "engineer", None):
        db.refresh(review)
    loaded = (
        db.query(EngineeringReview)
        .options(joinedload(EngineeringReview.engineer), joinedload(EngineeringReview.well))
        .filter(EngineeringReview.id == review.id)
        .one()
    )
    return {"success": True, "data": serialize_review(loaded), "message": "Engineering review recorded. Operational decisions remain with the engineer."}


@router.put("/{review_id}")
def update_review(
    review_id: UUID,
    body: ReviewUpdate,
    request: Request,
    user: User = Depends(require_roles(ROLE_ADMIN, ROLE_ENGINEER)),
    db: Session = Depends(get_db),
):
    review = db.get(EngineeringReview, review_id)
    if review is None:
        raise HTTPException(status_code=404, detail={"message": "Review not found.", "error_code": "RESOURCE_NOT_FOUND"})
    if user.role.name != ROLE_ADMIN and review.engineer_id != user.id:
        raise HTTPException(status_code=403, detail={"message": "You can only edit your own review.", "error_code": "FORBIDDEN"})
    if body.decision:
        if body.decision not in DECISIONS:
            raise HTTPException(status_code=422, detail={"message": "Unknown review decision.", "error_code": "VALIDATION_ERROR"})
        review.decision = body.decision
    if body.comment is not None:
        review.comment = body.comment
    write_audit(db, user_id=user.id, action="RISK_REVIEW_UPDATE", resource="engineering_review", resource_id=str(review.id), request=request)
    db.commit()
    loaded = (
        db.query(EngineeringReview)
        .options(joinedload(EngineeringReview.engineer), joinedload(EngineeringReview.well))
        .filter(EngineeringReview.id == review.id)
        .one()
    )
    return {"success": True, "data": serialize_review(loaded), "message": "Review updated."}
