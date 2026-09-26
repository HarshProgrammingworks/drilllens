from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from app.ml.features.feature_builder import latest_and_baseline
from app.ml.inference.engine import EvidenceRef, get_risk_engine
from app.models import DrillingParameter, Evidence, RiskEvent, RiskPrediction, RiskThreshold, Well
from app.services.alert_service import upsert_alert
from app.services.gis_service import nearby_wells

CATEGORIES = ["MUD", "STUCK_PIPE", "KICK", "TORQUE", "CEMENTING", "LOST_CIRCULATION"]


def ensure_thresholds(db: Session) -> None:
    existing = {row.category for row in db.query(RiskThreshold).all()}
    for category in CATEGORIES:
        if category not in existing:
            db.add(RiskThreshold(category=category))
    db.commit()


def _threshold_map(db: Session) -> dict:
    ensure_thresholds(db)
    rows = db.query(RiskThreshold).all()
    return {
        row.category: {
            "low_max": row.low_max,
            "moderate_max": row.moderate_max,
            "high_max": row.high_max,
            "alert_min_score": row.alert_min_score,
            "cooldown_minutes": row.cooldown_minutes,
            "torque_rise_pct": row.torque_rise_pct,
            "pressure_rise_pct": row.pressure_rise_pct,
            "flow_change_pct": row.flow_change_pct,
        }
        for row in rows
    }


def _parameter_rows(db: Session, well_id: UUID, limit: int = 40) -> list[dict]:
    rows = (
        db.query(DrillingParameter)
        .filter(DrillingParameter.well_id == well_id)
        .order_by(DrillingParameter.recorded_at.desc())
        .limit(limit)
        .all()
    )
    rows.reverse()
    return [
        {
            "depth": r.depth,
            "rop": r.rop,
            "wob": r.wob,
            "rpm": r.rpm,
            "torque": r.torque,
            "standpipe_pressure": r.standpipe_pressure,
            "mud_flow": r.mud_flow,
            "mud_weight": r.mud_weight,
            "pump_pressure": r.pump_pressure,
            "hook_load": r.hook_load,
            "recorded_at": r.recorded_at.isoformat() if r.recorded_at else None,
            "source": r.source,
            "provenance": r.provenance,
        }
        for r in rows
    ]


def _evidence_for_well(db: Session, well: Well) -> dict[str, list[EvidenceRef]]:
    coord = well.coordinate
    nearby_ids = {well.id}
    if coord is not None:
        neighbours = nearby_wells(
            db,
            latitude=coord.latitude,
            longitude=coord.longitude,
            radius_m=25000,
        )
        for item in neighbours:
            nearby_ids.add(UUID(item["id"]))
    rows = db.query(Evidence).filter(Evidence.well_id.in_(nearby_ids)).all()
    grouped: dict[str, list[EvidenceRef]] = {c: [] for c in CATEGORIES}
    for row in rows:
        category = None
        if row.event and row.event.risk_category:
            category = row.event.risk_category
        if category not in grouped:
            continue
        if len(grouped[category]) >= 5:
            continue
        well_code = row.well.well_code if row.well else None
        report_title = row.report.title if row.report else None
        grouped[category].append(
            EvidenceRef(
                id=str(row.id),
                text_excerpt=row.text_excerpt,
                well_code=well_code,
                formation=row.formation,
                depth_start=row.depth_start,
                report_title=report_title,
                confidence=row.confidence,
            )
        )
    return grouped


def serialize_result(result, computed_at: datetime, depth: float | None) -> dict:
    return {
        "category": result.category,
        "label": result.label,
        "score": result.score,
        "level": result.level,
        "confidence": result.confidence,
        "confidence_meaning": "Analytical confidence in the indicator given available data. This is not the probability that an event will occur.",
        "reasons": result.reasons,
        "evidence": [
            {
                "id": ev.id,
                "text_excerpt": ev.text_excerpt,
                "well_code": ev.well_code,
                "formation": ev.formation,
                "depth_start": ev.depth_start,
                "report_title": ev.report_title,
                "confidence": ev.confidence,
            }
            for ev in result.evidence
        ],
        "evidence_count": len(result.evidence),
        "current_data": result.inputs,
        "timestamp": computed_at.isoformat(),
        "depth": depth,
        "engine": result.engine,
        "engine_version": result.engine_version,
        "provenance": "RULE-BASED",
    }


def analyze_well(db: Session, well: Well, create_alerts: bool = True) -> list[dict]:
    rows = _parameter_rows(db, well.id)
    current, baseline, features = latest_and_baseline(rows)
    thresholds = _threshold_map(db)
    evidence = _evidence_for_well(db, well)
    coord = well.coordinate
    nearby_count = 0
    if coord is not None:
        nearby_count = len(
            nearby_wells(db, latitude=coord.latitude, longitude=coord.longitude, radius_m=25000, exclude_well_id=str(well.id))
        )
    engine = get_risk_engine()
    context = {
        "current": current,
        "baseline": baseline,
        "features": features,
        "thresholds": thresholds,
        "evidence": evidence,
        "operation": well.current_operation or "",
        "formation": well.current_formation,
        "nearby_count": nearby_count,
    }
    results = engine.analyze(context)
    computed_at = datetime.now(timezone.utc)
    payload = []
    for result in results:
        prediction = RiskPrediction(
            well_id=well.id,
            category=result.category,
            score=result.score,
            level=result.level,
            confidence=result.confidence,
            reasons=result.reasons,
            evidence_ids=[ev.id for ev in result.evidence],
            inputs={"current": current, "baseline": baseline, "rules": result.inputs},
            features=features,
            engine=result.engine,
            engine_version=result.engine_version,
            model_version=None,
            dataset_version=None,
            depth=current.get("depth") or well.current_depth,
            computed_at=computed_at,
        )
        db.add(prediction)
        db.flush()
        if result.level in {"HIGH", "CRITICAL"}:
            db.add(
                RiskEvent(
                    well_id=well.id,
                    prediction_id=prediction.id,
                    category=result.category,
                    score=result.score,
                    level=result.level,
                    recorded_at=computed_at,
                )
            )
        if create_alerts:
            th = thresholds.get(result.category, {})
            upsert_alert(
                db,
                well=well,
                result=result,
                alert_min_score=th.get("alert_min_score", 60),
                cooldown_minutes=th.get("cooldown_minutes", 30),
            )
        payload.append(serialize_result(result, computed_at, current.get("depth") or well.current_depth))
    db.commit()
    return payload


def latest_risks(db: Session, well_id: UUID) -> list[dict]:
    payload = []
    for category in CATEGORIES:
        row = (
            db.query(RiskPrediction)
            .filter(RiskPrediction.well_id == well_id, RiskPrediction.category == category)
            .order_by(RiskPrediction.computed_at.desc())
            .first()
        )
        if row is None:
            continue
        evidence_ids = row.evidence_ids or []
        evidence_rows = []
        if evidence_ids:
            uuids = []
            for item in evidence_ids:
                try:
                    uuids.append(UUID(item))
                except (TypeError, ValueError):
                    continue
            if uuids:
                evidence_rows = db.query(Evidence).filter(Evidence.id.in_(uuids)).all()
        payload.append(
            {
                "category": row.category,
                "label": {
                    "MUD": "Mud Problems",
                    "STUCK_PIPE": "Stuck Pipe",
                    "KICK": "Kick / Overpressure",
                    "TORQUE": "Torque Anomalies",
                    "CEMENTING": "Cementing Problems",
                    "LOST_CIRCULATION": "Lost Circulation",
                }[row.category],
                "score": row.score,
                "level": row.level,
                "confidence": row.confidence,
                "confidence_meaning": "Analytical confidence in the indicator given available data. This is not the probability that an event will occur.",
                "reasons": row.reasons,
                "evidence_ids": evidence_ids,
                "evidence": [
                    {
                        "id": str(item.id),
                        "text_excerpt": item.text_excerpt,
                        "formation": item.formation,
                        "depth_start": item.depth_start,
                        "confidence": item.confidence,
                    }
                    for item in evidence_rows
                ],
                "evidence_count": len(evidence_ids),
                "current_data": (row.inputs or {}).get("current"),
                "baseline": (row.inputs or {}).get("baseline"),
                "timestamp": row.computed_at.isoformat() if row.computed_at else None,
                "depth": row.depth,
                "engine": row.engine,
                "engine_version": row.engine_version,
                "provenance": "RULE-BASED",
            }
        )
    return payload
