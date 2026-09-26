from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.api.dependencies import ROLE_ADMIN, ROLE_ENGINEER, get_current_user, require_roles
from app.core.database import get_db
from app.models import RiskPrediction, User
from app.schemas.domain import AnalyzeRequest
from app.services.risk_service import analyze_well, latest_risks
from app.services.well_service import get_well
from app.utils.audit import write_audit

router = APIRouter(prefix="/risk", tags=["risk"])


@router.get("/current")
def current(well_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    well = get_well(db, well_id)
    if well is None:
        raise HTTPException(status_code=404, detail={"message": "Well not found.", "error_code": "RESOURCE_NOT_FOUND"})
    data = latest_risks(db, well.id)
    return {"success": True, "data": data, "message": None if data else "No risk analysis has been stored for this well yet."}


@router.get("/history")
def history(
    well_id: str,
    category: str | None = None,
    limit: int = 200,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    well = get_well(db, well_id)
    if well is None:
        raise HTTPException(status_code=404, detail={"message": "Well not found.", "error_code": "RESOURCE_NOT_FOUND"})
    query = db.query(RiskPrediction).filter(RiskPrediction.well_id == well.id)
    if category:
        query = query.filter(RiskPrediction.category == category)
    rows = query.order_by(RiskPrediction.computed_at.desc()).limit(min(limit, 1000)).all()
    return {
        "success": True,
        "data": [
            {
                "id": str(row.id),
                "category": row.category,
                "score": row.score,
                "level": row.level,
                "confidence": row.confidence,
                "depth": row.depth,
                "timestamp": row.computed_at.isoformat() if row.computed_at else None,
                "engine": row.engine,
                "provenance": "RULE-BASED",
            }
            for row in rows
        ],
        "message": None,
    }


@router.post("/analyze")
def analyze(
    body: AnalyzeRequest,
    request: Request,
    user: User = Depends(require_roles(ROLE_ADMIN, ROLE_ENGINEER)),
    db: Session = Depends(get_db),
):
    well = get_well(db, str(body.well_id))
    if well is None:
        raise HTTPException(status_code=404, detail={"message": "Well not found.", "error_code": "RESOURCE_NOT_FOUND"})
    data = analyze_well(db, well, create_alerts=True)
    write_audit(db, user_id=user.id, action="RISK_ANALYZE", resource="well", resource_id=str(well.id), request=request)
    db.commit()
    return {
        "success": True,
        "data": data,
        "message": "Rule-based risk indicators calculated. These are decision-support values, not operational instructions.",
    }
