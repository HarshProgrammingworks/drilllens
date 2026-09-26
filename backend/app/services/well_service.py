from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session, joinedload

from app.models import Well, WellCoordinate, WellTrajectory


def sync_geography(db: Session, table: str, well_id) -> None:
    """Fill PostGIS geography when the extension and column exist. Latitude and longitude remain the source values."""
    if table not in {"well_coordinates", "well_trajectories"}:
        return
    try:
        present = db.execute(
            text(
                """
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name = :table AND column_name = 'location'
                )
                """
            ),
            {"table": table},
        ).scalar()
        if not present:
            return
        db.execute(
            text(
                f"""
                UPDATE {table}
                SET location = ST_SetSRID(ST_MakePoint(longitude, latitude), 4326)::geography
                WHERE well_id = :well_id
                """
            ),
            {"well_id": well_id},
        )
    except Exception:
        pass


def get_well(db: Session, ident: str) -> Well | None:
    query = db.query(Well).options(joinedload(Well.coordinate))
    try:
        as_uuid = UUID(ident)
    except ValueError:
        as_uuid = None
    if as_uuid:
        well = query.filter(Well.id == as_uuid).one_or_none()
        if well:
            return well
    return query.filter(Well.well_code == ident).one_or_none()


def serialize_well(well: Well, distance_m: float | None = None, risk_summary: dict | None = None) -> dict:
    coord = well.coordinate
    return {
        "id": str(well.id),
        "well_id": well.well_code,
        "well_name": well.well_name,
        "field": well.field,
        "operator": well.operator,
        "latitude": coord.latitude if coord else None,
        "longitude": coord.longitude if coord else None,
        "status": well.status,
        "current_depth": well.current_depth,
        "formation": well.current_formation,
        "current_operation": well.current_operation,
        "spud_date": well.spud_date.isoformat() if well.spud_date else None,
        "completion_date": well.completion_date.isoformat() if well.completion_date else None,
        "well_type": well.well_type,
        "trajectory_type": well.trajectory_type,
        "is_archived": well.is_archived,
        "source_type": well.source_type,
        "simulate_sensors": well.simulate_sensors,
        "demo_scenario": well.demo_scenario,
        "updated_at": well.updated_at.isoformat() if well.updated_at else None,
        "distance_m": distance_m,
        "risk_summary": risk_summary,
        "provenance": well.source_type,
    }


def upsert_coordinate(db: Session, well: Well, lat: float, lon: float) -> None:
    if well.coordinate is None:
        db.add(WellCoordinate(well_id=well.id, latitude=lat, longitude=lon))
        db.flush()
    else:
        well.coordinate.latitude = lat
        well.coordinate.longitude = lon
    sync_geography(db, "well_coordinates", well.id)


def replace_trajectory(db: Session, well: Well, stations: list[dict]) -> None:
    db.query(WellTrajectory).filter(WellTrajectory.well_id == well.id).delete()
    for station in stations:
        db.add(
            WellTrajectory(
                well_id=well.id,
                station_index=station["station_index"],
                measured_depth=station["measured_depth"],
                tvd=station["tvd"],
                inclination=station.get("inclination", 0),
                azimuth=station.get("azimuth", 0),
                latitude=station["latitude"],
                longitude=station["longitude"],
            )
        )
    db.flush()
    sync_geography(db, "well_trajectories", well.id)
