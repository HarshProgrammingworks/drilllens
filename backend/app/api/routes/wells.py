from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.api.dependencies import ROLE_ADMIN, ROLE_ENGINEER, get_current_user, require_roles
from app.core.database import get_db
from app.models import DrillingEvent, DrillingParameter, EngineeringReview, User, Well, WellFormation, WellTrajectory
from app.schemas.domain import WellIn, WellUpdate
from app.services.gis_service import nearby_wells, postgis_enabled
from app.services.review_service import list_reviews, serialize_review
from app.services.risk_service import latest_risks
from app.services.similarity_service import depth_correlation, score_pair, similar_wells
from app.services.well_service import get_well, serialize_well, upsert_coordinate
from app.utils.audit import write_audit
from app.utils.pagination import page_window

router = APIRouter(prefix="/wells", tags=["wells"])

WELL_STATUSES = {"PLANNED", "DRILLING", "SUSPENDED", "COMPLETED", "ABANDONED"}


def _risk_summary(db: Session, well_id: UUID) -> dict:
    risks = latest_risks(db, well_id)
    if not risks:
        return {"level": "UNKNOWN", "max_score": None, "categories": []}
    top = max(risks, key=lambda item: item["score"])
    return {"level": top["level"], "max_score": top["score"], "top_category": top["category"], "categories": risks}


@router.get("")
def list_wells(
    q: str | None = None,
    status: str | None = None,
    field: str | None = None,
    formation: str | None = None,
    include_archived: bool = False,
    sort: str = "well_name",
    direction: str = "asc",
    page: int = 1,
    page_size: int = 20,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(Well)
    if not include_archived:
        query = query.filter(Well.is_archived.is_(False))
    if status:
        query = query.filter(Well.status == status)
    if field:
        query = query.filter(Well.field.ilike(f"%{field}%"))
    if formation:
        query = query.filter(Well.current_formation.ilike(f"%{formation}%"))
    if q:
        like = f"%{q}%"
        query = query.filter(
            (Well.well_name.ilike(like)) | (Well.well_code.ilike(like)) | (Well.field.ilike(like)) | (Well.operator.ilike(like))
        )
    sort_col = {
        "well_name": Well.well_name,
        "well_id": Well.well_code,
        "field": Well.field,
        "status": Well.status,
        "current_depth": Well.current_depth,
        "updated_at": Well.updated_at,
    }.get(sort, Well.well_name)
    query = query.order_by(sort_col.desc() if direction == "desc" else sort_col.asc())
    total = query.count()
    offset, limit = page_window(page, page_size)
    rows = query.options(joinedload(Well.coordinate)).offset(offset).limit(limit).all()
    return {
        "success": True,
        "data": {
            "items": [serialize_well(row) for row in rows],
            "total": total,
            "page": page,
            "page_size": page_size,
        },
        "message": None,
    }


@router.post("")
def create_well(
    body: WellIn,
    request: Request,
    user: User = Depends(require_roles(ROLE_ADMIN, ROLE_ENGINEER)),
    db: Session = Depends(get_db),
):
    if body.status not in WELL_STATUSES:
        raise HTTPException(status_code=422, detail={"message": "Unknown well status.", "error_code": "VALIDATION_ERROR"})
    if db.query(Well).filter(Well.well_code == body.well_id).first():
        raise HTTPException(status_code=409, detail={"message": "Well ID already exists.", "error_code": "CONFLICT"})
    well = Well(
        well_code=body.well_id.strip(),
        well_name=body.well_name.strip(),
        field=body.field.strip(),
        operator=body.operator.strip(),
        status=body.status,
        current_depth=body.current_depth,
        current_formation=body.formation,
        current_operation=body.current_operation,
        spud_date=body.spud_date,
        completion_date=body.completion_date,
        well_type=body.well_type,
        trajectory_type=body.trajectory_type,
        source_type="ENGINEER_ENTERED",
        simulate_sensors=body.simulate_sensors,
        created_by=user.id,
    )
    db.add(well)
    db.flush()
    upsert_coordinate(db, well, body.latitude, body.longitude)
    write_audit(db, user_id=user.id, action="WELL_CREATE", resource="well", resource_id=str(well.id), request=request, metadata={"well_id": well.well_code})
    db.commit()
    db.refresh(well)
    return {"success": True, "data": serialize_well(well), "message": "Well created."}


@router.get("/nearby")
def nearby(
    latitude: float = Query(..., ge=-90, le=90),
    longitude: float = Query(..., ge=-180, le=180),
    radius: float = Query(10, description="Radius in kilometres, or metres if radius_unit=m"),
    radius_unit: str = "km",
    formation: str | None = None,
    risk: str | None = None,
    min_depth: float | None = None,
    max_depth: float | None = None,
    status: str | None = None,
    exclude_well_id: str | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    radius_m = radius if radius_unit == "m" else radius * 1000
    if radius_m <= 0 or radius_m > 500_000:
        raise HTTPException(status_code=422, detail={"message": "Radius must be between 0 and 500 km.", "error_code": "VALIDATION_ERROR"})
    exclude = None
    if exclude_well_id:
        well = get_well(db, exclude_well_id)
        exclude = str(well.id) if well else exclude_well_id
    rows = nearby_wells(
        db,
        latitude=latitude,
        longitude=longitude,
        radius_m=radius_m,
        formation=formation,
        risk=risk,
        min_depth=min_depth,
        max_depth=max_depth,
        status=status,
        exclude_well_id=exclude,
    )
    data = []
    for row in rows:
        risks = _risk_summary(db, UUID(row["id"]))
        data.append(
            {
                "id": row["id"],
                "well_id": row["well_code"],
                "name": row["well_name"],
                "well_name": row["well_name"],
                "field": row["field"],
                "distance_m": round(float(row["distance_m"]), 1),
                "distance_km": round(float(row["distance_m"]) / 1000, 3),
                "formation": row["current_formation"],
                "depth": row["current_depth"],
                "status": row["status"],
                "latitude": row["latitude"],
                "longitude": row["longitude"],
                "trajectory_type": row["trajectory_type"],
                "risk_summary": risks,
                "provenance": "CALCULATED",
                "distance_method": "PostGIS geography ST_Distance SRID 4326" if postgis_enabled(db) else "Server-side haversine on stored coordinates",
            }
        )
    return {"success": True, "data": data, "message": None}


@router.get("/{well_id}")
def well_detail(well_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    well = get_well(db, well_id)
    if well is None:
        raise HTTPException(status_code=404, detail={"message": "Well not found.", "error_code": "RESOURCE_NOT_FOUND"})
    payload = serialize_well(well, risk_summary=_risk_summary(db, well.id))
    payload["formations"] = [
        {
            "name": row.formation.name,
            "depth_top": row.depth_top,
            "depth_bottom": row.depth_bottom,
        }
        for row in db.query(WellFormation).filter(WellFormation.well_id == well.id).all()
    ]
    return {"success": True, "data": payload, "message": None}


@router.put("/{well_id}")
def update_well(
    well_id: str,
    body: WellUpdate,
    request: Request,
    user: User = Depends(require_roles(ROLE_ADMIN, ROLE_ENGINEER)),
    db: Session = Depends(get_db),
):
    well = get_well(db, well_id)
    if well is None:
        raise HTTPException(status_code=404, detail={"message": "Well not found.", "error_code": "RESOURCE_NOT_FOUND"})
    if body.status and body.status not in WELL_STATUSES:
        raise HTTPException(status_code=422, detail={"message": "Unknown well status.", "error_code": "VALIDATION_ERROR"})
    mapping = {
        "well_name": "well_name",
        "field": "field",
        "operator": "operator",
        "status": "status",
        "current_depth": "current_depth",
        "current_operation": "current_operation",
        "spud_date": "spud_date",
        "completion_date": "completion_date",
        "well_type": "well_type",
        "trajectory_type": "trajectory_type",
        "simulate_sensors": "simulate_sensors",
        "is_archived": "is_archived",
    }
    data = body.model_dump(exclude_unset=True)
    for key, attr in mapping.items():
        if key in data:
            setattr(well, attr, data[key])
    if "formation" in data:
        well.current_formation = data["formation"]
    if body.latitude is not None and body.longitude is not None:
        upsert_coordinate(db, well, body.latitude, body.longitude)
    elif body.latitude is not None or body.longitude is not None:
        raise HTTPException(status_code=422, detail={"message": "Latitude and longitude must be updated together.", "error_code": "VALIDATION_ERROR"})
    write_audit(db, user_id=user.id, action="WELL_UPDATE", resource="well", resource_id=str(well.id), request=request, metadata={"fields": list(data.keys())})
    db.commit()
    db.refresh(well)
    return {"success": True, "data": serialize_well(well), "message": "Well updated."}


@router.delete("/{well_id}")
def archive_well(
    well_id: str,
    request: Request,
    user: User = Depends(require_roles(ROLE_ADMIN)),
    db: Session = Depends(get_db),
):
    well = get_well(db, well_id)
    if well is None:
        raise HTTPException(status_code=404, detail={"message": "Well not found.", "error_code": "RESOURCE_NOT_FOUND"})
    well.is_archived = True
    well.status = "ABANDONED" if well.status == "PLANNED" else well.status
    write_audit(db, user_id=user.id, action="WELL_ARCHIVE", resource="well", resource_id=str(well.id), request=request)
    db.commit()
    return {"success": True, "data": serialize_well(well), "message": "Well archived."}


@router.get("/{well_id}/events")
def well_events(well_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    well = get_well(db, well_id)
    if well is None:
        raise HTTPException(status_code=404, detail={"message": "Well not found.", "error_code": "RESOURCE_NOT_FOUND"})
    rows = db.query(DrillingEvent).filter(DrillingEvent.well_id == well.id).order_by(DrillingEvent.depth_start).all()
    return {
        "success": True,
        "data": [
            {
                "id": str(row.id),
                "event_type": row.event_type,
                "risk_category": row.risk_category,
                "description": row.description,
                "action_taken": row.action_taken,
                "outcome": row.outcome,
                "depth_start": row.depth_start,
                "depth_end": row.depth_end,
                "formation": row.formation_name,
                "event_date": row.event_date.isoformat() if row.event_date else None,
                "confidence": row.confidence,
                "report_id": str(row.report_id) if row.report_id else None,
                "page_id": str(row.page_id) if row.page_id else None,
                "source_type": row.source_type,
            }
            for row in rows
        ],
        "message": None,
    }


@router.get("/{well_id}/trajectory")
def trajectory(well_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    well = get_well(db, well_id)
    if well is None:
        raise HTTPException(status_code=404, detail={"message": "Well not found.", "error_code": "RESOURCE_NOT_FOUND"})
    rows = (
        db.query(WellTrajectory)
        .filter(WellTrajectory.well_id == well.id)
        .order_by(WellTrajectory.station_index)
        .all()
    )
    return {
        "success": True,
        "data": [
            {
                "station_index": row.station_index,
                "measured_depth": row.measured_depth,
                "tvd": row.tvd,
                "inclination": row.inclination,
                "azimuth": row.azimuth,
                "latitude": row.latitude,
                "longitude": row.longitude,
            }
            for row in rows
        ],
        "message": None,
    }


@router.get("/{well_id}/similar")
def similar(well_id: str, limit: int = 8, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    well = get_well(db, well_id)
    if well is None:
        raise HTTPException(status_code=404, detail={"message": "Well not found.", "error_code": "RESOURCE_NOT_FOUND"})
    return {"success": True, "data": similar_wells(db, well, limit=min(limit, 20)), "message": None}


@router.get("/{well_id}/compare/{other_id}")
def compare(well_id: str, other_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    left = get_well(db, well_id)
    right = get_well(db, other_id)
    if left is None or right is None:
        raise HTTPException(status_code=404, detail={"message": "Well not found.", "error_code": "RESOURCE_NOT_FOUND"})
    return {"success": True, "data": score_pair(db, left, right), "message": None}


@router.get("/{well_id}/depth-correlation")
def correlate(
    well_id: str,
    depth: float | None = None,
    tolerance: float = 100,
    formation: str | None = None,
    correction_m: float = 0,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    well = get_well(db, well_id)
    if well is None:
        raise HTTPException(status_code=404, detail={"message": "Well not found.", "error_code": "RESOURCE_NOT_FOUND"})
    if tolerance < 0 or tolerance > 2000:
        raise HTTPException(status_code=422, detail={"message": "Tolerance must be between 0 and 2000 m.", "error_code": "VALIDATION_ERROR"})
    return {
        "success": True,
        "data": depth_correlation(db, well, depth=depth, tolerance=tolerance, formation=formation, correction_m=correction_m),
        "message": None,
    }


@router.get("/{well_id}/parameters")
def parameters(
    well_id: str,
    limit: int = 300,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    well = get_well(db, well_id)
    if well is None:
        raise HTTPException(status_code=404, detail={"message": "Well not found.", "error_code": "RESOURCE_NOT_FOUND"})
    rows = (
        db.query(DrillingParameter)
        .filter(DrillingParameter.well_id == well.id)
        .order_by(DrillingParameter.recorded_at.desc())
        .limit(min(limit, 1000))
        .all()
    )
    rows.reverse()
    return {
        "success": True,
        "data": [
            {
                "timestamp": row.recorded_at.isoformat() if row.recorded_at else None,
                "depth": row.depth,
                "rop": row.rop,
                "wob": row.wob,
                "rpm": row.rpm,
                "torque": row.torque,
                "standpipe_pressure": row.standpipe_pressure,
                "mud_flow": row.mud_flow,
                "mud_weight": row.mud_weight,
                "pump_pressure": row.pump_pressure,
                "hook_load": row.hook_load,
                "source": row.source,
                "provenance": row.provenance,
            }
            for row in rows
        ],
        "message": None,
    }


@router.get("/{well_id}/parameters/latest")
def latest_parameters(well_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    well = get_well(db, well_id)
    if well is None:
        raise HTTPException(status_code=404, detail={"message": "Well not found.", "error_code": "RESOURCE_NOT_FOUND"})
    row = (
        db.query(DrillingParameter)
        .filter(DrillingParameter.well_id == well.id)
        .order_by(DrillingParameter.recorded_at.desc())
        .first()
    )
    if row is None:
        return {"success": True, "data": None, "message": "No parameter samples are stored for this well."}
    return {
        "success": True,
        "data": {
            "timestamp": row.recorded_at.isoformat(),
            "source": row.source,
            "provenance": row.provenance,
            "parameters": {
                "depth": {"value": row.depth, "unit": "m"},
                "rop": {"value": row.rop, "unit": "m/h"},
                "wob": {"value": row.wob, "unit": "klbf"},
                "rpm": {"value": row.rpm, "unit": "rpm"},
                "torque": {"value": row.torque, "unit": "kN·m"},
                "standpipe_pressure": {"value": row.standpipe_pressure, "unit": "psi"},
                "mud_flow": {"value": row.mud_flow, "unit": "L/min"},
                "mud_weight": {"value": row.mud_weight, "unit": "sg"},
                "pump_pressure": {"value": row.pump_pressure, "unit": "psi"},
                "hook_load": {"value": row.hook_load, "unit": "klbf"},
            },
        },
        "message": None,
    }


@router.get("/{well_id}/reviews")
def well_reviews(well_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    well = get_well(db, well_id)
    if well is None:
        raise HTTPException(status_code=404, detail={"message": "Well not found.", "error_code": "RESOURCE_NOT_FOUND"})
    return {"success": True, "data": [serialize_review(row) for row in list_reviews(db, well_id=well.id)], "message": None}


@router.get("/map")
def map_wells(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Registered after /nearby in code order. FastAPI matches static paths first if declared first.
    This function is also mounted via a dedicated path below if ordering conflicts.
    """
    raise HTTPException(status_code=404, detail={"message": "Use /wells.", "error_code": "RESOURCE_NOT_FOUND"})
