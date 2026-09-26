import asyncio

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.core.logging import log
from app.models import DrillingParameter, Well
from app.services.risk_service import analyze_well
from app.services.sensor_adapter import get_sensor_adapter
from app.services.well_service import serialize_well
from app.websocket.hub import hub

_ticks: dict[str, int] = {}
_anchors: dict[str, float] = {}
_running = False


def tick_once(db: Session) -> list[dict]:
    adapter = get_sensor_adapter()
    wells = db.query(Well).filter(Well.simulate_sensors.is_(True), Well.is_archived.is_(False)).all()
    payloads = []
    for well in wells:
        tick = _ticks.get(well.well_code, 0) + 1
        _ticks[well.well_code] = tick
        if well.well_code not in _anchors:
            _anchors[well.well_code] = well.current_depth or 2400.0
        reading = adapter.read(well.well_code, _anchors[well.well_code], well.demo_scenario or "normal", tick)
        # Do not let the demo stream permanently rewrite the engineering depth record
        # by a large amount. Store the reading and mirror current depth from it.
        row = DrillingParameter(
            well_id=well.id,
            depth=reading.depth,
            rop=reading.rop,
            wob=reading.wob,
            rpm=reading.rpm,
            torque=reading.torque,
            standpipe_pressure=reading.standpipe_pressure,
            mud_flow=reading.mud_flow,
            mud_weight=reading.mud_weight,
            pump_pressure=reading.pump_pressure,
            hook_load=reading.hook_load,
            source=reading.source,
            provenance=reading.provenance,
            recorded_at=reading.recorded_at,
        )
        db.add(row)
        well.current_depth = reading.depth
        if well.demo_scenario == "cementing":
            well.current_operation = "Cementing"
        elif well.current_operation == "Cementing" and well.demo_scenario == "normal":
            well.current_operation = "Drilling"
        parameters = {
            "depth": reading.depth,
            "rop": reading.rop,
            "wob": reading.wob,
            "rpm": reading.rpm,
            "torque": reading.torque,
            "standpipe_pressure": reading.standpipe_pressure,
            "mud_flow": reading.mud_flow,
            "mud_weight": reading.mud_weight,
            "pump_pressure": reading.pump_pressure,
            "hook_load": reading.hook_load,
        }
        payloads.append(
            {
                "well_id": well.well_code,
                "well_uuid": str(well.id),
                "timestamp": reading.recorded_at.isoformat(),
                "source": "SIMULATED",
                "label": "DEMO SENSOR STREAM",
                "scenario": well.demo_scenario,
                "parameters": parameters,
                "units": {
                    "depth": "m",
                    "rop": "m/h",
                    "wob": "klbf",
                    "rpm": "rpm",
                    "torque": "kN·m",
                    "standpipe_pressure": "psi",
                    "mud_flow": "L/min",
                    "mud_weight": "sg",
                    "pump_pressure": "psi",
                    "hook_load": "klbf",
                },
            }
        )
        if tick % 5 == 0:
            db.flush()
            analyze_well(db, well, create_alerts=True)
    db.commit()
    return payloads


async def sensor_loop() -> None:
    global _running
    if _running:
        return
    _running = True
    settings = get_settings()
    log.info("Demo sensor stream started (interval %ss)", settings.websocket_interval_seconds)
    while True:
        try:
            def _run():
                db = SessionLocal()
                try:
                    return tick_once(db)
                finally:
                    db.close()

            payloads = await asyncio.to_thread(_run)
            for payload in payloads:
                await hub.broadcast_monitoring(payload["well_id"], payload)
                await hub.broadcast_monitoring(payload["well_uuid"], payload)
        except Exception:
            log.exception("Sensor loop iteration failed")
        await asyncio.sleep(settings.websocket_interval_seconds)


def well_snapshot(db: Session, well: Well) -> dict:
    return serialize_well(well)
