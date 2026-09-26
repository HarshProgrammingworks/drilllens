from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from app.api.dependencies import user_from_token_string
from app.core.database import SessionLocal
from app.services.well_service import get_well
from app.websocket.hub import hub

router = APIRouter(tags=["monitoring"])


@router.websocket("/ws/monitoring/{well_id}")
async def monitoring_socket(websocket: WebSocket, well_id: str):
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=4401)
        return
    db: Session = SessionLocal()
    try:
        user_from_token_string(token, db)
        well = get_well(db, well_id)
        if well is None:
            await websocket.close(code=4404)
            return
        keys = [well.well_code, str(well.id)]
    except Exception:
        await websocket.close(code=4401)
        db.close()
        return
    finally:
        db.close()
    await websocket.accept()
    for key in keys:
        await hub.join_monitoring(key, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        for key in keys:
            await hub.leave_monitoring(key, websocket)


@router.websocket("/ws/notifications")
async def notification_socket(websocket: WebSocket):
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=4401)
        return
    db = SessionLocal()
    try:
        user_from_token_string(token, db)
    except Exception:
        await websocket.close(code=4401)
        return
    finally:
        db.close()
    await websocket.accept()
    await hub.join_notifications(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        await hub.leave_notifications(websocket)
