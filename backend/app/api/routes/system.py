import shutil

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.dependencies import ROLE_ADMIN, ROLE_ENGINEER, get_current_user, require_roles
from app.core.config import get_settings
from app.core.database import get_db
from app.models import AuditLog, HistoricalReport, Notification, RiskThreshold, SystemConfig, User, Well
from app.schemas.domain import DemoScenarioRequest, SimilarityWeights, ThresholdUpdate, UserCreateAdmin, UserUpdate
from app.services.auth_service import create_user, public_user, role_by_name
from app.services.nlp_service import transformer_status
from app.services.ocr_service import tesseract_available
from app.services.risk_service import ensure_thresholds
from app.services.well_service import get_well
from app.utils.audit import write_audit
from app.utils.pagination import page_window

router = APIRouter(tags=["system"])


@router.get("/health")
def health():
    return {"success": True, "data": {"status": "ok", "service": "drilllens"}, "message": None}


@router.get("/health/database")
def health_db(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    try:
        postgis = db.execute(text("SELECT PostGIS_Version()")).scalar()
    except Exception:
        postgis = "spatial_fallback (haversine)"
    return {"success": True, "data": {"database": "ok", "postgis": postgis}, "message": None}


@router.get("/system/public-config")
def public_config():
    settings = get_settings()
    return {
        "success": True,
        "data": {
            "app_name": "DrillLens",
            "platform": "eRTMAC-NWIS",
            "full_name": "Enhanced Real-Time Monitoring & Control Centre – Nearby Well Intelligence System",
            "version": settings.app_version,
            "osm_tile_url": settings.osm_tile_url,
            "sensor_adapter": settings.sensor_adapter,
            "risk_engine": settings.risk_engine,
        },
        "message": None,
    }


@router.get("/notifications")
def notifications(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = (
        db.query(Notification)
        .filter((Notification.user_id.is_(None)) | (Notification.user_id == user.id))
        .order_by(Notification.created_at.desc())
        .limit(40)
        .all()
    )
    return {
        "success": True,
        "data": [
            {
                "id": str(row.id),
                "type": row.type,
                "title": row.title,
                "body": row.body,
                "link": row.link,
                "read": row.read_at is not None,
                "created_at": row.created_at.isoformat() if row.created_at else None,
            }
            for row in rows
        ],
        "message": None,
    }


@router.post("/notifications/{notification_id}/read")
def read_notification(notification_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    from datetime import datetime, timezone
    from uuid import UUID

    row = db.get(Notification, UUID(notification_id))
    if row is None:
        raise HTTPException(status_code=404, detail={"message": "Notification not found.", "error_code": "RESOURCE_NOT_FOUND"})
    row.read_at = datetime.now(timezone.utc)
    db.commit()
    return {"success": True, "data": {"id": notification_id, "read": True}, "message": None}


@router.post("/monitoring/{well_id}/demo-scenario")
def demo_scenario(
    well_id: str,
    body: DemoScenarioRequest,
    request: Request,
    user: User = Depends(require_roles(ROLE_ADMIN, ROLE_ENGINEER)),
    db: Session = Depends(get_db),
):
    allowed = {"normal", "stuck_pipe", "kick", "lost_circulation", "mud", "torque", "cementing"}
    if body.scenario not in allowed:
        raise HTTPException(status_code=422, detail={"message": "Unknown demo scenario.", "error_code": "VALIDATION_ERROR"})
    well = get_well(db, well_id)
    if well is None:
        raise HTTPException(status_code=404, detail={"message": "Well not found.", "error_code": "RESOURCE_NOT_FOUND"})
    if not well.simulate_sensors:
        raise HTTPException(status_code=409, detail={"message": "This well is not on the demo sensor stream.", "error_code": "NOT_SIMULATED"})
    well.demo_scenario = body.scenario
    if body.scenario == "cementing":
        well.current_operation = "Cementing"
    elif body.scenario == "normal":
        well.current_operation = "Drilling"
    write_audit(
        db,
        user_id=user.id,
        action="DEMO_SCENARIO",
        resource="well",
        resource_id=str(well.id),
        request=request,
        metadata={"scenario": body.scenario, "label": "DEMO"},
    )
    db.commit()
    return {
        "success": True,
        "data": {"well_id": well.well_code, "scenario": well.demo_scenario, "label": "DEMO SENSOR STREAM"},
        "message": "Demo scenario applied to the simulated sensor stream only.",
    }


@router.get("/admin/users")
def admin_users(user: User = Depends(require_roles(ROLE_ADMIN)), db: Session = Depends(get_db)):
    return {"success": True, "data": [public_user(row) for row in db.query(User).order_by(User.username).all()], "message": None}


@router.post("/admin/users")
def admin_create_user(body: UserCreateAdmin, request: Request, user: User = Depends(require_roles(ROLE_ADMIN)), db: Session = Depends(get_db)):
    if role_by_name(db, body.role) is None:
        raise HTTPException(status_code=422, detail={"message": "Unknown role.", "error_code": "VALIDATION_ERROR"})
    if db.query(User).filter((User.username == body.username) | (User.email == body.email.lower())).first():
        raise HTTPException(status_code=409, detail={"message": "Username or email already exists.", "error_code": "CONFLICT"})
    created = create_user(db, username=body.username, email=body.email, password=body.password, full_name=body.full_name, role_name=body.role)
    created.is_active = body.is_active
    write_audit(db, user_id=user.id, action="USER_CREATE", resource="user", resource_id=str(created.id), request=request, metadata={"role": body.role})
    db.commit()
    db.refresh(created)
    return {"success": True, "data": public_user(created), "message": "User created."}


@router.put("/admin/users/{user_id}")
def admin_update_user(user_id: str, body: UserUpdate, request: Request, actor: User = Depends(require_roles(ROLE_ADMIN)), db: Session = Depends(get_db)):
    from uuid import UUID

    target = db.get(User, UUID(user_id))
    if target is None:
        raise HTTPException(status_code=404, detail={"message": "User not found.", "error_code": "RESOURCE_NOT_FOUND"})
    if body.role:
        role = role_by_name(db, body.role)
        if role is None:
            raise HTTPException(status_code=422, detail={"message": "Unknown role.", "error_code": "VALIDATION_ERROR"})
        target.role_id = role.id
    if body.full_name is not None:
        target.full_name = body.full_name
    if body.is_active is not None:
        target.is_active = body.is_active
    if body.email is not None:
        target.email = body.email.lower()
    write_audit(db, user_id=actor.id, action="USER_UPDATE", resource="user", resource_id=str(target.id), request=request, metadata=body.model_dump(exclude_unset=True))
    db.commit()
    db.refresh(target)
    return {"success": True, "data": public_user(target), "message": "User updated."}


@router.delete("/admin/users/{user_id}")
def admin_delete_user(user_id: str, request: Request, actor: User = Depends(require_roles(ROLE_ADMIN)), db: Session = Depends(get_db)):
    from uuid import UUID

    if str(actor.id) == user_id:
        raise HTTPException(status_code=400, detail={"message": "You cannot delete your own account.", "error_code": "SELF_DELETION_FORBIDDEN"})
    target = db.get(User, UUID(user_id))
    if target is None:
        raise HTTPException(status_code=404, detail={"message": "User not found.", "error_code": "RESOURCE_NOT_FOUND"})
    username = target.username
    db.delete(target)
    write_audit(db, user_id=actor.id, action="USER_DELETE", resource="user", resource_id=str(user_id), request=request, metadata={"username": username})
    db.commit()
    return {"success": True, "data": {"id": user_id, "username": username}, "message": "User deleted."}


@router.get("/admin/risk-thresholds")
def get_thresholds(user: User = Depends(require_roles(ROLE_ADMIN)), db: Session = Depends(get_db)):
    ensure_thresholds(db)
    rows = db.query(RiskThreshold).order_by(RiskThreshold.category).all()
    return {
        "success": True,
        "data": [
            {
                "category": row.category,
                "low_max": row.low_max,
                "moderate_max": row.moderate_max,
                "high_max": row.high_max,
                "alert_min_score": row.alert_min_score,
                "cooldown_minutes": row.cooldown_minutes,
                "torque_rise_pct": row.torque_rise_pct,
                "pressure_rise_pct": row.pressure_rise_pct,
                "flow_change_pct": row.flow_change_pct,
                "updated_at": row.updated_at.isoformat() if row.updated_at else None,
            }
            for row in rows
        ],
        "message": None,
    }


@router.put("/admin/risk-thresholds/{category}")
def update_threshold(
    category: str,
    body: ThresholdUpdate,
    request: Request,
    user: User = Depends(require_roles(ROLE_ADMIN)),
    db: Session = Depends(get_db),
):
    from datetime import datetime, timezone

    ensure_thresholds(db)
    row = db.query(RiskThreshold).filter(RiskThreshold.category == category).one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail={"message": "Threshold category not found.", "error_code": "RESOURCE_NOT_FOUND"})
    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(row, key, value)
    if not (row.low_max < row.moderate_max < row.high_max < 100):
        raise HTTPException(status_code=422, detail={"message": "Thresholds must increase: low < moderate < high < 100.", "error_code": "VALIDATION_ERROR"})
    row.updated_by = user.id
    row.updated_at = datetime.now(timezone.utc)
    write_audit(db, user_id=user.id, action="CONFIG_CHANGE", resource="risk_threshold", resource_id=category, request=request, metadata=body.model_dump(exclude_unset=True))
    db.commit()
    return {"success": True, "data": {"category": category}, "message": "Threshold updated."}


@router.get("/admin/audit-logs")
def audit_logs(
    action: str | None = None,
    page: int = 1,
    page_size: int = 50,
    user: User = Depends(require_roles(ROLE_ADMIN, ROLE_ENGINEER)),
    db: Session = Depends(get_db),
):
    query = db.query(AuditLog)
    if action:
        query = query.filter(AuditLog.action == action)
    total = query.count()
    offset, limit = page_window(page, page_size)
    rows = query.order_by(AuditLog.created_at.desc()).offset(offset).limit(limit).all()
    users = {u.id: u.username for u in db.query(User).all()}
    return {
        "success": True,
        "data": {
            "total": total,
            "items": [
                {
                    "id": str(row.id),
                    "user_id": str(row.user_id) if row.user_id else None,
                    "username": users.get(row.user_id),
                    "action": row.action,
                    "resource": row.resource,
                    "resource_id": row.resource_id,
                    "ip_address": row.ip_address,
                    "metadata": row.metadata_json,
                    "timestamp": row.created_at.isoformat() if row.created_at else None,
                }
                for row in rows
            ],
        },
        "message": None,
    }


@router.get("/admin/system")
def admin_system(user: User = Depends(require_roles(ROLE_ADMIN)), db: Session = Depends(get_db)):
    settings = get_settings()
    failures = db.query(HistoricalReport).filter(HistoricalReport.status == "FAILED").count()
    return {
        "success": True,
        "data": {
            "version": settings.app_version,
            "environment": settings.environment,
            "risk_engine": settings.risk_engine,
            "sensor_adapter": settings.sensor_adapter,
            "tesseract_available": tesseract_available(),
            "transformers": transformer_status(),
            "wells": db.query(Well).count(),
            "users": db.query(User).count(),
            "reports": db.query(HistoricalReport).count(),
            "processing_failures": failures,
            "upload_directory": settings.upload_directory,
            "disk_free_mb": round((shutil.disk_usage(settings.upload_directory).free if __import__("os").path.isdir(settings.upload_directory) else shutil.disk_usage("/").free) / (1024 * 1024), 1),
            "decision_support_notice": "DrillLens does not control drilling equipment and does not authorize operations.",
        },
        "message": None,
    }


@router.get("/admin/similarity-weights")
def get_weights(user: User = Depends(require_roles(ROLE_ADMIN)), db: Session = Depends(get_db)):
    from app.services.similarity_service import get_weights as load

    return {"success": True, "data": load(db), "message": None}


@router.put("/admin/similarity-weights")
def put_weights(body: SimilarityWeights, request: Request, user: User = Depends(require_roles(ROLE_ADMIN)), db: Session = Depends(get_db)):
    from datetime import datetime, timezone

    total = body.geographic + body.formation + body.depth + body.trajectory + body.event
    if abs(total - 1.0) > 0.02:
        raise HTTPException(status_code=422, detail={"message": "Similarity weights must sum to 1.", "error_code": "VALIDATION_ERROR"})
    row = db.get(SystemConfig, "similarity_weights")
    value = body.model_dump()
    if row is None:
        db.add(SystemConfig(key="similarity_weights", value=value, updated_by=user.id))
    else:
        row.value = value
        row.updated_by = user.id
        row.updated_at = datetime.now(timezone.utc)
    write_audit(db, user_id=user.id, action="CONFIG_CHANGE", resource="similarity_weights", resource_id="similarity_weights", request=request, metadata=value)
    db.commit()
    return {"success": True, "data": value, "message": "Similarity weights updated."}


@router.get("/admin/uploads")
def uploads(user: User = Depends(require_roles(ROLE_ADMIN)), db: Session = Depends(get_db)):
    rows = db.query(HistoricalReport).order_by(HistoricalReport.created_at.desc()).limit(100).all()
    return {
        "success": True,
        "data": [
            {
                "id": str(row.id),
                "title": row.title,
                "status": row.status,
                "error_message": row.error_message,
                "file_size": row.file_size,
                "original_filename": row.original_filename,
            }
            for row in rows
        ],
        "message": None,
    }
