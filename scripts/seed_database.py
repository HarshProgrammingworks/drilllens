"""Idempotent development seed for DrillLens.

All seeded wells, reports, and events use source_type DEMO.
Development users must be replaced before any production deployment.
"""

from __future__ import annotations

import math
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import text

HERE = Path(__file__).resolve().parent
CANDIDATES = [Path("/app"), HERE.parent / "backend", HERE.parent]
for candidate in CANDIDATES:
    if (candidate / "app").is_dir():
        sys.path.insert(0, str(candidate))
        break
ROOT = HERE.parent

from app.core.config import get_settings  # noqa: E402
from app.core.database import SessionLocal  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.models import (  # noqa: E402
    DrillingEvent,
    DrillingParameter,
    EngineeringReview,
    Evidence,
    Formation,
    HistoricalReport,
    Role,
    SystemConfig,
    User,
    Well,
    WellFormation,
)
from app.services.report_service import process_report  # noqa: E402
from app.services.risk_service import analyze_well, ensure_thresholds  # noqa: E402
from app.services.well_service import replace_trajectory, upsert_coordinate  # noqa: E402

USERS = [
    ("admin", "admin@drilllens.local", "Admin123!", "Avery Admin", "ADMIN"),
    ("engineer", "engineer@drilllens.local", "Engineer123!", "Riley Engineer", "DRILLING_ENGINEER"),
    ("viewer", "viewer@drilllens.local", "Viewer123!", "Casey Viewer", "VIEWER"),
]

FORMATIONS = [
    ("Wolfcamp", "Permian Wolfcamp interval used in the North Rift demo set."),
    ("Bone Spring", "Bone Spring interval used in the North Rift demo set."),
    ("Spraberry", "Spraberry interval used in the North Rift demo set."),
    ("Dean", "Dean interval used in the North Rift demo set."),
]

# Coordinates are a fictional cluster around a Permian-like latitude so PostGIS distances are real.
WELLS = [
    ("WL-001", "North Rift 1", "North Rift", "Rift Energy", 31.8500, -102.3500, "DRILLING", 2450, "Wolfcamp", "Drilling", "DEVELOPMENT", "DIRECTIONAL", True),
    ("WL-002", "North Rift 2", "North Rift", "Rift Energy", 31.8720, -102.3480, "COMPLETED", 2680, "Bone Spring", "Completed", "DEVELOPMENT", "DIRECTIONAL", False),
    ("WL-003", "North Rift 3", "North Rift", "Rift Energy", 31.8510, -102.2750, "COMPLETED", 2520, "Wolfcamp", "Completed", "DEVELOPMENT", "VERTICAL", False),
    ("WL-004", "East Flank 1", "East Flank", "Rift Energy", 31.9000, -102.2500, "COMPLETED", 2410, "Spraberry", "Completed", "EXPLORATION", "VERTICAL", False),
    ("WL-005", "East Flank 2", "East Flank", "Basin Drill Co", 31.9300, -102.2100, "SUSPENDED", 2555, "Bone Spring", "Suspended", "DEVELOPMENT", "DIRECTIONAL", False),
    ("WL-006", "South Bench 1", "South Bench", "Basin Drill Co", 31.7000, -102.3600, "COMPLETED", 2300, "Dean", "Completed", "DEVELOPMENT", "HORIZONTAL", False),
    ("WL-007", "South Bench 2", "South Bench", "Basin Drill Co", 31.6400, -102.4200, "COMPLETED", 2490, "Wolfcamp", "Completed", "DEVELOPMENT", "DIRECTIONAL", False),
    ("WL-008", "Far Offset 1", "Far Offset", "Offset Petro", 31.4000, -102.0500, "COMPLETED", 2100, "Spraberry", "Completed", "EXPLORATION", "VERTICAL", False),
]

INTERVALS = {
    "WL-001": [("Spraberry", 1800, 2200), ("Wolfcamp", 2200, 2700), ("Bone Spring", 2700, 3100)],
    "WL-002": [("Spraberry", 1750, 2150), ("Wolfcamp", 2150, 2550), ("Bone Spring", 2550, 2900)],
    "WL-003": [("Wolfcamp", 2000, 2700)],
    "WL-004": [("Spraberry", 1900, 2500)],
    "WL-005": [("Bone Spring", 2100, 2800)],
    "WL-006": [("Dean", 1700, 2400)],
    "WL-007": [("Wolfcamp", 2000, 2700)],
    "WL-008": [("Spraberry", 1600, 2300)],
}

EXTRA_EVENTS = [
    ("WL-003", "KICK", "KICK", 2410, "Wolfcamp", "At 2410 m a kick was suspected while drilling Wolfcamp Formation on North Rift 3. The well was shut in and pressure stabilized.", "Shut in the well", "Pressure stabilized", date(2023, 11, 2)),
    ("WL-004", "LOST_CIRCULATION", "LOST_CIRCULATION", 2280, "Spraberry", "At 2280 m lost circulation was observed in the Spraberry Formation on East Flank 1. LCM was pumped and circulation was partially restored.", "Pumped LCM", "Circulation restored", date(2022, 6, 18)),
    ("WL-005", "CEMENTING", "CEMENTING", 2490, "Bone Spring", "At 2490 m a cementing problem followed the casing cement job in the Bone Spring Formation. A squeeze was performed and the cement job completed.", "Circulated", "Cement job completed", date(2023, 1, 9)),
    ("WL-006", "MUD", "MUD", 2210, "Dean", "At 2210 m gas-cut mud was reported in the Dean Formation. Mud weight was increased and circulation continued.", "Increased mud weight", "Condition stabilized", date(2021, 9, 14)),
    ("WL-007", "TORQUE", "TORQUE", 2460, "Wolfcamp", "At 2460 m torque increased significantly while drilling Wolfcamp Formation on South Bench 2. RPM was reduced and torque stabilized.", "Reduced RPM", "Torque stabilized", date(2024, 1, 20)),
    ("WL-002", "STUCK_PIPE", "STUCK_PIPE", 2475, "Wolfcamp", "At 2475 m the crew worked the pipe after a stuck pipe indication in the Wolfcamp Formation. The pipe freed after jarring.", "Worked the pipe", "Pipe freed", date(2024, 3, 13)),
]


def seed() -> None:
    db = SessionLocal()
    try:
        if db.query(User).count():
            print("Seed skipped: users already exist.")
            return
        roles = {}
        for name, description in (
            ("ADMIN", "User, threshold, and system administration"),
            ("DRILLING_ENGINEER", "Engineering review, uploads, and well maintenance"),
            ("VIEWER", "Read-only access"),
        ):
            role = Role(name=name, description=description)
            db.add(role)
            roles[name] = role
        db.flush()
        users = {}
        for username, email, password, full_name, role_name in USERS:
            user = User(
                username=username,
                email=email,
                password_hash=hash_password(password),
                full_name=full_name,
                role_id=roles[role_name].id,
                is_active=True,
            )
            db.add(user)
            users[username] = user
        db.flush()
        formations = {}
        for name, description in FORMATIONS:
            row = Formation(name=name, description=description)
            db.add(row)
            formations[name] = row
        db.flush()
        wells = {}
        for code, name, field, operator, lat, lon, status, depth, formation, operation, well_type, trajectory, simulate in WELLS:
            well = Well(
                well_code=code,
                well_name=name,
                field=field,
                operator=operator,
                status=status,
                current_depth=depth,
                current_formation=formation,
                current_operation=operation,
                spud_date=date(2023, 4, 1),
                completion_date=None if status == "DRILLING" else date(2024, 8, 1),
                well_type=well_type,
                trajectory_type=trajectory,
                source_type="DEMO",
                simulate_sensors=simulate,
                demo_scenario="normal",
                created_by=users["admin"].id,
            )
            db.add(well)
            db.flush()
            upsert_coordinate(db, well, lat, lon)
            stations = []
            for index in range(8):
                stations.append(
                    {
                        "station_index": index,
                        "measured_depth": round(depth * (index + 1) / 8, 1),
                        "tvd": round(depth * (index + 1) / 8 * (0.98 if trajectory != "HORIZONTAL" else 0.85), 1),
                        "inclination": 8 * index if trajectory == "DIRECTIONAL" else (70 if trajectory == "HORIZONTAL" and index > 4 else 2),
                        "azimuth": 45,
                        "latitude": lat + index * 0.0004,
                        "longitude": lon + index * 0.0003,
                    }
                )
            replace_trajectory(db, well, stations)
            for fname, top, bottom in INTERVALS[code]:
                db.add(WellFormation(well_id=well.id, formation_id=formations[fname].id, depth_top=top, depth_bottom=bottom))
            wells[code] = well
        db.flush()

        now = datetime.now(timezone.utc)
        primary = wells["WL-001"]
        for index in range(30):
            stamp = now - timedelta(minutes=(30 - index) * 2)
            db.add(
                DrillingParameter(
                    well_id=primary.id,
                    recorded_at=stamp,
                    depth=2450 + index * 0.1,
                    rop=17.5 + math.sin(index / 3),
                    wob=12.0 + 0.2 * math.sin(index / 4),
                    rpm=118 + math.sin(index / 2),
                    torque=18.4 + 0.3 * math.sin(index / 5),
                    standpipe_pressure=1740 + 8 * math.sin(index / 3),
                    mud_flow=855 + 4 * math.sin(index / 4),
                    mud_weight=1.18,
                    pump_pressure=1840 + 6 * math.sin(index / 3),
                    hook_load=126 + math.sin(index / 6),
                    source="HISTORICAL",
                    provenance="HISTORICAL REPORT",
                )
            )

        upload_root = Path(get_settings().upload_directory) / "reports"
        upload_root.mkdir(parents=True, exist_ok=True)
        source = Path(__file__).with_name("WCR_DEMO_001.txt")
        target = upload_root / "WCR_DEMO_001.txt"
        target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
        report = HistoricalReport(
            well_id=wells["WL-002"].id,
            title="WCR_DEMO_001 North Rift 2",
            report_type="WCR",
            original_filename="WCR_DEMO_001.txt",
            storage_path=str(target),
            status="UPLOADED",
            file_size=target.stat().st_size,
            uploaded_by=users["engineer"].id,
            report_date=date(2024, 3, 12),
            source_type="DEMO",
        )
        db.add(report)
        db.commit()
        process_report(db, report.id)

        for code, event_type, risk, depth, formation, description, action, outcome, event_date in EXTRA_EVENTS:
            well = wells[code]
            event = DrillingEvent(
                well_id=well.id,
                depth_start=depth,
                depth_end=depth,
                formation_id=formations[formation].id,
                formation_name=formation,
                event_type=event_type,
                description=description,
                action_taken=action,
                outcome=outcome,
                risk_category=risk,
                event_date=event_date,
                confidence=0.9,
                source_type="DEMO",
            )
            db.add(event)
            db.flush()
            db.add(
                Evidence(
                    source_type="DEMO",
                    well_id=well.id,
                    event_id=event.id,
                    depth_start=depth,
                    depth_end=depth,
                    formation=formation,
                    text_excerpt=description,
                    source_location="DEMO seed record",
                    confidence=0.9,
                )
            )
        db.commit()
        db.execute(
            text(
                """
                UPDATE drilling_events
                SET search_vector = to_tsvector('english',
                    coalesce(description,'') || ' ' || coalesce(event_type,'') || ' ' ||
                    coalesce(risk_category,'') || ' ' || coalesce(formation_name,'') || ' ' ||
                    coalesce(action_taken,'') || ' ' || coalesce(outcome,''))
                """
            )
        )
        db.execute(
            text(
                """
                UPDATE evidence
                SET search_vector = to_tsvector('english', coalesce(text_excerpt,'') || ' ' || coalesce(formation,''))
                """
            )
        )
        db.add(SystemConfig(key="similarity_weights", value={"geographic": 0.20, "formation": 0.25, "depth": 0.20, "trajectory": 0.15, "event": 0.20}))
        ensure_thresholds(db)
        db.add(
            EngineeringReview(
                well_id=primary.id,
                engineer_id=users["engineer"].id,
                decision="REVIEW",
                comment="DEMO review. Initial offset-well scan recorded. No operational change was authorized by the system.",
                risk_category="STUCK_PIPE",
                snapshot={"source": "DEMO"},
            )
        )
        db.commit()
        analyze_well(db, primary, create_alerts=False)
        print("Seed completed with DEMO wells, report WCR_DEMO_001, and development users.")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
