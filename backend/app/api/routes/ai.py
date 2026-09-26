from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.core.database import get_db
from app.models import User, Well
from app.services.gemini_service import analyze_well_with_gemini, call_gemini
from app.services.well_service import get_well

router = APIRouter(prefix="/ai", tags=["ai"])


class AiAskRequest(BaseModel):
    prompt: str
    well_id: str | None = None
    context: str | None = None


class AiAnalyzeWellRequest(BaseModel):
    well_id: str


@router.post("/ask")
async def ask_gemini(
    body: AiAskRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not body.prompt.strip():
        raise HTTPException(status_code=422, detail={"message": "Prompt is required", "error_code": "VALIDATION_ERROR"})

    extra_context = body.context or ""
    if body.well_id:
        well = get_well(db, body.well_id)
        if well:
            extra_context += f"\nWell Context: {well.well_code} ({well.well_name}), Field: {well.field}, Depth: {well.current_depth}m, Formation: {well.current_formation}, Status: {well.status}, Operation: {well.current_operation}"

    response_text = await call_gemini(body.prompt, extra_context if extra_context else None)
    return {
        "success": True,
        "data": {
            "answer": response_text,
            "model": "gemini-flash-latest",
            "provider": "Google Gemini",
        },
        "message": None,
    }


@router.post("/analyze-well/{well_id}")
async def analyze_well_ai(
    well_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    well = get_well(db, well_id)
    if not well:
        raise HTTPException(status_code=404, detail={"message": "Well not found", "error_code": "RESOURCE_NOT_FOUND"})

    well_dict = {
        "well_id": well.well_code,
        "well_name": well.well_name,
        "field": well.field,
        "operator": well.operator,
        "current_depth": well.current_depth,
        "formation": well.current_formation,
        "status": well.status,
        "current_operation": well.current_operation,
    }

    # Fetch offset wells from same field
    offsets = (
        db.query(Well)
        .filter(Well.field == well.field, Well.id != well.id)
        .limit(5)
        .all()
    )
    offset_dicts = [
        {
            "well_id": o.well_code,
            "well_name": o.well_name,
            "formation": o.current_formation,
            "current_depth": o.current_depth,
            "status": o.status,
        }
        for o in offsets
    ]

    analysis = await analyze_well_with_gemini(well_dict, offset_dicts)
    return {
        "success": True,
        "data": {
            "well_id": well.well_code,
            "analysis": analysis,
            "model": "gemini-flash-latest",
        },
        "message": None,
    }
