from uuid import UUID

from sqlalchemy.orm import Session

from app.models import DrillingEvent, SystemConfig, Well, WellFormation, WellSimilarity
from app.services.gis_service import distance_between

DEFAULT_WEIGHTS = {
    "geographic": 0.20,
    "formation": 0.25,
    "depth": 0.20,
    "trajectory": 0.15,
    "event": 0.20,
}


def get_weights(db: Session) -> dict:
    row = db.get(SystemConfig, "similarity_weights")
    if row is None or not isinstance(row.value, dict):
        return dict(DEFAULT_WEIGHTS)
    weights = dict(DEFAULT_WEIGHTS)
    for key in DEFAULT_WEIGHTS:
        if key in row.value:
            weights[key] = float(row.value[key])
    total = sum(weights.values()) or 1.0
    return {key: value / total for key, value in weights.items()}


def _formations(db: Session, well_id: UUID) -> set[str]:
    rows = (
        db.query(WellFormation)
        .filter(WellFormation.well_id == well_id)
        .all()
    )
    names = set()
    for row in rows:
        if row.formation and row.formation.name:
            names.add(row.formation.name.lower())
    well = db.get(Well, well_id)
    if well and well.current_formation:
        names.add(well.current_formation.lower())
    return names


def _events(db: Session, well_id: UUID) -> list[DrillingEvent]:
    return db.query(DrillingEvent).filter(DrillingEvent.well_id == well_id).all()


def score_pair(db: Session, left: Well, right: Well, weights: dict | None = None) -> dict:
    weights = weights or get_weights(db)
    distance = distance_between(db, str(left.id), str(right.id))
    if distance is None:
        geo = 0.0
    else:
        geo = max(0.0, 1.0 - (distance / 50000.0))

    forms_a = _formations(db, left.id)
    forms_b = _formations(db, right.id)
    if forms_a and forms_b:
        formation = len(forms_a & forms_b) / len(forms_a | forms_b)
    else:
        formation = 0.0

    if left.current_depth is not None and right.current_depth is not None:
        depth = max(0.0, 1.0 - abs(left.current_depth - right.current_depth) / 1500.0)
    else:
        depth = 0.0

    if left.trajectory_type and right.trajectory_type:
        trajectory = 1.0 if left.trajectory_type == right.trajectory_type else 0.35
    else:
        trajectory = 0.0

    events_a = _events(db, left.id)
    events_b = _events(db, right.id)
    types_a = {e.event_type for e in events_a}
    types_b = {e.event_type for e in events_b}
    if types_a and types_b:
        event = len(types_a & types_b) / len(types_a | types_b)
        # Boost when events occur within 150 m of each other.
        close = 0
        for ea in events_a:
            for eb in events_b:
                if ea.event_type == eb.event_type and ea.depth_start is not None and eb.depth_start is not None:
                    if abs(ea.depth_start - eb.depth_start) <= 150:
                        close += 1
        if close:
            event = min(1.0, event + 0.15)
    elif not types_a and not types_b:
        event = 0.5
    else:
        event = 0.0

    overall = (
        weights["geographic"] * geo
        + weights["formation"] * formation
        + weights["depth"] * depth
        + weights["trajectory"] * trajectory
        + weights["event"] * event
    )
    parts = []
    if formation >= 0.5:
        parts.append("high formation similarity")
    elif formation > 0:
        parts.append("partial formation overlap")
    if depth >= 0.6:
        parts.append("comparable drilling depth")
    if geo >= 0.7:
        parts.append("close geographic proximity")
    elif geo >= 0.3:
        parts.append("moderate geographic proximity")
    shared = types_a & types_b
    if shared:
        labels = ", ".join(sorted(shared)).replace("_", " ").lower()
        parts.append(f"shared historical event types ({labels})")
    if trajectory >= 0.9:
        parts.append(f"matching {left.trajectory_type.lower()} trajectory type")
    if not parts:
        explanation = "Limited similarity on the configured geographic, formation, depth, trajectory, and event factors."
    else:
        sentence = parts[0].capitalize()
        if len(parts) > 1:
            sentence = sentence + " and " + ", ".join(parts[1:])
        explanation = sentence + "."
    return {
        "well_id": str(right.id),
        "well_code": right.well_code,
        "well_name": right.well_name,
        "overall_score": round(overall, 4),
        "geographic_score": round(geo, 4),
        "formation_score": round(formation, 4),
        "depth_score": round(depth, 4),
        "trajectory_score": round(trajectory, 4),
        "event_score": round(event, 4),
        "explanation": explanation,
        "distance_m": None if distance is None else round(distance, 1),
        "weights": weights,
        "provenance": "CALCULATED",
    }


def similar_wells(db: Session, well: Well, limit: int = 8, persist: bool = True) -> list[dict]:
    weights = get_weights(db)
    others = (
        db.query(Well)
        .filter(Well.id != well.id, Well.is_archived.is_(False))
        .all()
    )
    scored = [score_pair(db, well, other, weights) for other in others]
    scored.sort(key=lambda item: item["overall_score"], reverse=True)
    top = scored[:limit]
    if persist:
        for item in top:
            existing = (
                db.query(WellSimilarity)
                .filter(
                    WellSimilarity.well_id == well.id,
                    WellSimilarity.other_well_id == UUID(item["well_id"]),
                )
                .one_or_none()
            )
            if existing is None:
                existing = WellSimilarity(well_id=well.id, other_well_id=UUID(item["well_id"]))
                db.add(existing)
            existing.overall_score = item["overall_score"]
            existing.geographic_score = item["geographic_score"]
            existing.formation_score = item["formation_score"]
            existing.depth_score = item["depth_score"]
            existing.trajectory_score = item["trajectory_score"]
            existing.event_score = item["event_score"]
            existing.explanation = item["explanation"]
            existing.weights = weights
            existing.distance_m = item["distance_m"]
        db.commit()
    return top


def depth_correlation(
    db: Session,
    well: Well,
    *,
    depth: float | None,
    tolerance: float,
    formation: str | None,
    correction_m: float,
) -> dict:
    """Compare a reference depth with historical events.

    correction_m is an engineer-supplied comparison offset. Source event depths
    are not modified.
    """
    reference = depth if depth is not None else well.current_depth
    events = db.query(DrillingEvent).filter(DrillingEvent.well_id.isnot(None)).all()
    rows = []
    for event in events:
        if event.depth_start is None or reference is None:
            continue
        if formation and (event.formation_name or "").lower() != formation.lower():
            continue
        original = event.depth_start
        adjusted = original + correction_m
        difference = reference - adjusted
        if abs(difference) > tolerance:
            continue
        uncertainty = round(abs(correction_m) * 0.25 + (1.0 - (event.confidence or 0.5)) * tolerance * 0.5, 2)
        source_well = db.get(Well, event.well_id)
        rows.append(
            {
                "event_id": str(event.id),
                "well_id": str(event.well_id),
                "well_code": source_well.well_code if source_well else None,
                "well_name": source_well.well_name if source_well else None,
                "current_depth": reference,
                "historical_depth": original,
                "adjusted_comparison_depth": round(adjusted, 2),
                "correction_m": correction_m,
                "depth_difference": round(difference, 2),
                "formation": event.formation_name,
                "event_type": event.event_type,
                "description": event.description,
                "uncertainty": uncertainty,
                "confidence": event.confidence,
                "provenance": "CALCULATED",
                "source_note": "Original historical depth is unchanged. The adjusted depth is a comparison view only.",
            }
        )
    rows.sort(key=lambda item: abs(item["depth_difference"]))
    return {
        "reference_depth": reference,
        "tolerance_m": tolerance,
        "correction_m": correction_m,
        "formation": formation,
        "matches": rows,
    }
