import math
from sqlalchemy import text
from sqlalchemy.orm import Session


def postgis_enabled(db: Session) -> bool:
    try:
        return bool(
            db.execute(text("SELECT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'postgis')")).scalar()
        )
    except Exception:
        return False


_FILTERS = """
          AND (:formation IS NULL OR w.current_formation LIKE :formation)
          AND (:status IS NULL OR w.status = :status)
          AND (:min_depth IS NULL OR w.current_depth >= :min_depth)
          AND (:max_depth IS NULL OR w.current_depth <= :max_depth)
          AND (:exclude_id IS NULL OR CAST(w.id AS TEXT) <> :exclude_id)
          AND (
                :risk IS NULL OR EXISTS (
                    SELECT 1 FROM drilling_events e
                    WHERE e.well_id = w.id AND e.risk_category = :risk
                )
          )
"""


def nearby_wells(
    db: Session,
    *,
    latitude: float,
    longitude: float,
    radius_m: float,
    formation: str | None = None,
    risk: str | None = None,
    min_depth: float | None = None,
    max_depth: float | None = None,
    status: str | None = None,
    exclude_well_id: str | None = None,
) -> list[dict]:
    """Server-side distance calculation with PostGIS support and haversine fallback."""
    from app.models import Well, WellCoordinate

    wells_query = db.query(Well).join(WellCoordinate, WellCoordinate.well_id == Well.id).filter(Well.is_archived.is_(False))
    if formation:
        wells_query = wells_query.filter(Well.current_formation.ilike(f"%{formation}%"))
    if status:
        wells_query = wells_query.filter(Well.status == status)
    if min_depth is not None:
        wells_query = wells_query.filter(Well.current_depth >= min_depth)
    if max_depth is not None:
        wells_query = wells_query.filter(Well.current_depth <= max_depth)
    if exclude_well_id:
        import uuid
        try:
            ex_uuid = exclude_well_id if isinstance(exclude_well_id, uuid.UUID) else uuid.UUID(str(exclude_well_id))
            wells_query = wells_query.filter(Well.id != ex_uuid)
        except Exception:
            pass

    wells = wells_query.all()
    results = []

    for w in wells:
        coord = w.coordinate
        if not coord:
            continue
        # Haversine distance in meters
        dlat = math.radians(coord.latitude - latitude)
        dlon = math.radians(coord.longitude - longitude)
        a = (
            math.sin(dlat / 2) ** 2
            + math.cos(math.radians(latitude))
            * math.cos(math.radians(coord.latitude))
            * math.sin(dlon / 2) ** 2
        )
        c = 2 * math.asin(math.sqrt(a))
        distance_m = 6371000 * c

        if distance_m <= radius_m:
            results.append(
                {
                    "id": str(w.id),
                    "well_code": w.well_code,
                    "well_name": w.well_name,
                    "field": w.field,
                    "status": w.status,
                    "current_depth": w.current_depth,
                    "current_formation": w.current_formation,
                    "trajectory_type": w.trajectory_type,
                    "well_type": w.well_type,
                    "current_operation": w.current_operation,
                    "latitude": coord.latitude,
                    "longitude": coord.longitude,
                    "distance_m": round(distance_m, 1),
                }
            )

    results.sort(key=lambda item: item["distance_m"])
    return results


def distance_between(db: Session, well_a, well_b) -> float | None:
    import uuid
    from app.models import WellCoordinate

    try:
        uid_a = well_a if isinstance(well_a, uuid.UUID) else uuid.UUID(str(well_a))
        uid_b = well_b if isinstance(well_b, uuid.UUID) else uuid.UUID(str(well_b))
    except Exception:
        return None

    coord_a = db.query(WellCoordinate).filter(WellCoordinate.well_id == uid_a).first()
    coord_b = db.query(WellCoordinate).filter(WellCoordinate.well_id == uid_b).first()

    if not coord_a or not coord_b:
        return None

    dlat = math.radians(coord_b.latitude - coord_a.latitude)
    dlon = math.radians(coord_b.longitude - coord_a.longitude)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(coord_a.latitude))
        * math.cos(math.radians(coord_b.latitude))
        * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.asin(math.sqrt(a))
    return round(6371000 * c, 2)
