from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.core.database import get_db
from app.models import User
from app.services.evidence_service import get_evidence, serialize_evidence

router = APIRouter(prefix="/evidence", tags=["evidence"])


@router.get("/{evidence_id}")
def evidence_detail(evidence_id: UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    row = get_evidence(db, evidence_id)
    if row is None:
        raise HTTPException(status_code=404, detail={"message": "Evidence not found.", "error_code": "RESOURCE_NOT_FOUND"})
    return {"success": True, "data": serialize_evidence(row), "message": None}


@router.get("/{evidence_id}/source")
def evidence_source(evidence_id: UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    row = get_evidence(db, evidence_id)
    if row is None:
        raise HTTPException(status_code=404, detail={"message": "Evidence not found.", "error_code": "RESOURCE_NOT_FOUND"})
    data = serialize_evidence(row)
    data["document"] = {
        "report_id": data["report_id"],
        "title": data["report_title"],
        "file_url": f"/api/reports/{data['report_id']}/file" if data["report_id"] else None,
        "page": data["source_location"],
    }
    return {"success": True, "data": data, "message": None}
