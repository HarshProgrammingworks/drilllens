from sqlalchemy import text
from sqlalchemy.orm import Session


def postgis_enabled(db: Session) -> bool:
    return bool(
        db.execute(text("SELECT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'postgis')")).scalar()
    )


_FILTERS = """
          AND (:formation IS NULL OR w.current_formation ILIKE :formation)
          AND (:status IS NULL OR w.status = :status)
          AND (:min_depth IS NULL OR w.current_depth >= :min_depth)
          AND (:max_depth IS NULL OR w.current_depth <= :max_depth)
          AND (:exclude_id IS NULL OR w.id::text <> :exclude_id)
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
    """Server-side distance. PostGIS geography when the extension is installed, otherwise haversine on stored coordinates."""
    if postgis_enabled(db):
        distance_sql = """
            ST_Distance(
                c.location,
                ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography
            )
        """
        within_sql = """
          AND ST_DWithin(
                c.location,
                ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography,
                :radius
          )
        """
    else:
        distance_sql = """
            6371000 * 2 * asin(sqrt(
                power(sin(radians(c.latitude - :lat) / 2), 2)
                + cos(radians(:lat)) * cos(radians(c.latitude))
                  * power(sin(radians(c.longitude - :lon) / 2), 2)
            ))
        """
        within_sql = ""
    sql = f"""
        SELECT * FROM (
            SELECT
                w.id::text AS id,
                w.well_code,
                w.well_name,
                w.field,
                w.status,
                w.current_depth,
                w.current_formation,
                w.trajectory_type,
                w.well_type,
                w.current_operation,
                c.latitude,
                c.longitude,
                {distance_sql} AS distance_m
            FROM wells w
            JOIN well_coordinates c ON c.well_id = w.id
            WHERE w.is_archived = false
            {within_sql}
            {_FILTERS}
        ) nearby
        WHERE distance_m <= :radius
        ORDER BY distance_m ASC
    """
    rows = db.execute(
        text(sql),
        {
            "lat": latitude,
            "lon": longitude,
            "radius": radius_m,
            "formation": f"%{formation}%" if formation else None,
            "status": status,
            "min_depth": min_depth,
            "max_depth": max_depth,
            "exclude_id": exclude_well_id,
            "risk": risk,
        },
    ).mappings().all()
    return [dict(row) for row in rows]


def distance_between(db: Session, well_a: str, well_b: str) -> float | None:
    if postgis_enabled(db):
        sql = """
            SELECT ST_Distance(a.location, b.location) AS distance_m
            FROM well_coordinates a
            JOIN well_coordinates b ON b.well_id::text = :b
            WHERE a.well_id::text = :a
        """
    else:
        sql = """
            SELECT 6371000 * 2 * asin(sqrt(
                power(sin(radians(b.latitude - a.latitude) / 2), 2)
                + cos(radians(a.latitude)) * cos(radians(b.latitude))
                  * power(sin(radians(b.longitude - a.longitude) / 2), 2)
            )) AS distance_m
            FROM well_coordinates a
            JOIN well_coordinates b ON b.well_id::text = :b
            WHERE a.well_id::text = :a
        """
    row = db.execute(text(sql), {"a": well_a, "b": well_b}).mappings().first()
    if row is None:
        return None
    return float(row["distance_m"])
