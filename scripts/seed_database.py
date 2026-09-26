"""Idempotent seed and migration script for DrillLens 30 Indian MVP Demo Wells.

Replaces foreign well dataset with exactly 30 Indian wells across:
- Rajasthan - Barmer (7 wells)
- Gujarat - Cambay Basin (6 wells)
- Assam (5 wells)
- Andhra Pradesh - Krishna-Godavari Basin (5 wells)
- Mumbai Offshore / Maharashtra (3 wells)
- Tamil Nadu - Cauvery Basin (2 wells)
- Other Indian Basins: Tripura & Mahanadi (2 wells)
Total: Exactly 30 Indian Wells.

Recalculates all dependencies: Coordinates, Trajectories, Formations, Events,
Evidence, Reports, Risks, Similarities, Alerts, and Search Vectors.
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
    Alert,
    AuditLog,
    DrillingEvent,
    DrillingParameter,
    EngineeringReview,
    Evidence,
    Formation,
    HistoricalReport,
    NlpEntity,
    Notification,
    OcrResult,
    ReportPage,
    RiskEvent,
    RiskPrediction,
    Role,
    SystemConfig,
    User,
    Well,
    WellCoordinate,
    WellFormation,
    WellSimilarity,
    WellTrajectory,
)
from app.services.report_service import process_report  # noqa: E402
from app.services.risk_service import analyze_well, ensure_thresholds  # noqa: E402
from app.services.similarity_service import similar_wells  # noqa: E402
from app.services.well_service import replace_trajectory, upsert_coordinate  # noqa: E402

USERS = [
    ("admin", "admin@drilllens.local", "Admin123!", "Avery Admin", "ADMIN"),
    ("engineer", "engineer@drilllens.local", "Engineer123!", "Riley Engineer", "DRILLING_ENGINEER"),
    ("viewer", "viewer@drilllens.local", "Viewer123!", "Casey Viewer", "VIEWER"),
]

# Formations mapped to the major Indian basins
INDIAN_FORMATIONS = [
    # Barmer Basin (Rajasthan)
    ("Fatehgarh", "Upper Cretaceous to Lower Paleocene fluvial-deltaic reservoir sands in Barmer Basin."),
    ("Barmer Hill", "Organic-rich lacustrine siliceous shale and porcellanite source/reservoir rock."),
    ("Dharvi Dungar", "Eocene shale and argillaceous sandstone unit in Barmer Basin."),
    ("Thumbli", "Lower Eocene sandstone and claystone sequence in Barmer Basin."),
    
    # Cambay Basin (Gujarat)
    ("Kalol", "Middle Eocene sandstone and siltstone producing interval in North Cambay."),
    ("Ankleshwar", "Middle to Upper Eocene deltaic sandstone reservoir in South Cambay."),
    ("Cambay Shale", "Paleocene to Lower Eocene regional source rock and tight reservoir."),
    ("Hazad", "Eocene prograding deltaic sand member with prolific hydrocarbon pay in Cambay."),
    
    # Assam-Arakan Basin (Assam)
    ("Barail", "Oligocene deltaic sandstones; primary multi-pay reservoir in Upper Assam."),
    ("Tipam", "Miocene massive fluvial sandstone reservoir sequence across Assam oilfields."),
    ("Kopili", "Late Eocene to Early Oligocene marine shale forming regional top seal."),
    ("Girujan Clay", "Late Miocene to Pliocene mottled claystone formation in Upper Assam."),
    
    # Krishna-Godavari Basin (Andhra Pradesh)
    ("Raghavapuram", "Early Cretaceous marine shale with lenticular sandstone pays in KG Basin."),
    ("Tirupati", "Late Cretaceous littoral to deltaic sandstone reservoir in KG Basin."),
    ("Gollapalli", "Early Cretaceous delta-plain coarse sandstone pay in KG onshore."),
    ("Kommugudem", "Permian-Triassic fluvio-lacustrine sandstone and coal sequence in KG Basin."),
    
    # Mumbai Offshore Basin
    ("Bombay High Limestone", "Early to Middle Miocene bioclastic carbonate reservoir in Mumbai High."),
    ("Bassein", "Middle Eocene to Early Oligocene platform limestone in South Bassein gas field."),
    ("Mukta", "Oligocene limestone and carbonate sequence in Mumbai Offshore."),
    ("Panna", "Paleocene basal clastic and coaly shale sequence in Mumbai Offshore."),
    
    # Cauvery Basin (Tamil Nadu)
    ("Bhuvanagiri", "Cretaceous deepwater turbiditic sandstone in Cauvery Basin."),
    ("Nannilam", "Late Cretaceous fractured siltstone and sandstone pay in Cauvery."),
    ("Andimadam", "Early Cretaceous alluvial to deltaic reservoir unit in Cauvery."),
    
    # Other Basins (Tripura & Mahanadi)
    ("Bhuban", "Miocene rhythmic sandstone-shale sequence in Tripura fold belt."),
    ("Bokabil", "Middle Miocene argillaceous sandstone and shale in Surma group."),
    ("Mahanadi Carbonate", "Eocene-Oligocene shelf carbonates in Mahanadi offshore deepwater."),
]

# EXACTLY 30 INDIAN MVP DEMO WELLS
# Columns: Code, Name, Field/Area, Operator, Lat, Lon, Status, Depth (m), Current Formation, Operation, Well Type, Trajectory, Simulate Sensors
INDIAN_WELLS = [
    # --- 1. Rajasthan - Barmer (7 wells) ---
    ("WL-IN-001", "Barmer Mangala 01", "Mangala Field", "Cairn Oil & Gas", 25.8650, 71.2400, "DRILLING", 2450, "Fatehgarh", "Drilling ahead 8-1/2 in section", "DEVELOPMENT", "DIRECTIONAL", True),
    ("WL-IN-002", "Barmer Bhagyam 02", "Bhagyam Field", "Cairn Oil & Gas", 25.9820, 71.2650, "COMPLETED", 2680, "Barmer Hill", "Producing / Polymer flood monitoring", "DEVELOPMENT", "DIRECTIONAL", False),
    ("WL-IN-003", "Barmer Aishwarya 04", "Aishwarya Field", "Cairn Oil & Gas", 25.8230, 71.2210, "COMPLETED", 2520, "Fatehgarh", "Oil producer online", "DEVELOPMENT", "VERTICAL", False),
    ("WL-IN-004", "Barmer Saraswati 01", "Saraswati Field", "ONGC", 25.7500, 71.3100, "COMPLETED", 2410, "Dharvi Dungar", "Gas lift production", "EXPLORATION", "VERTICAL", False),
    ("WL-IN-005", "Barmer Raageshwari 03", "Raageshwari Field", "Cairn Oil & Gas", 25.6800, 71.3650, "SUSPENDED", 2950, "Thumbli", "Suspended for workover", "DEVELOPMENT", "DIRECTIONAL", False),
    ("WL-IN-006", "Barmer Guda 02", "Guda Field", "Cairn Oil & Gas", 25.7100, 71.4200, "COMPLETED", 2310, "Fatehgarh", "Flowing on 24/64 choke", "DEVELOPMENT", "HORIZONTAL", False),
    ("WL-IN-007", "Barmer Kameshwari 05", "Kameshwari Field", "Cairn Oil & Gas", 26.0400, 71.2100, "COMPLETED", 2590, "Barmer Hill", "Cyclic steam stimulation", "DEVELOPMENT", "DIRECTIONAL", False),

    # --- 2. Gujarat - Cambay Basin (6 wells) ---
    ("WL-IN-008", "Cambay Ankleshwar 14", "Ankleshwar Field", "ONGC", 21.6320, 72.9850, "COMPLETED", 2350, "Ankleshwar", "Dual string oil producer", "DEVELOPMENT", "DIRECTIONAL", False),
    ("WL-IN-009", "Cambay Gandhar 08", "Gandhar Field", "ONGC", 21.8900, 72.7600, "DRILLING", 2980, "Hazad", "Logging at TD", "DEVELOPMENT", "DIRECTIONAL", False),
    ("WL-IN-010", "Cambay Kalol 22", "Kalol Field", "ONGC", 23.2300, 72.5100, "COMPLETED", 2120, "Kalol", "Beam pump producing", "DEVELOPMENT", "VERTICAL", False),
    ("WL-IN-011", "Cambay Mehsana 07", "Mehsana Field", "ONGC", 23.6000, 72.3900, "COMPLETED", 2420, "Kalol", "In-situ combustion project", "DEVELOPMENT", "DIRECTIONAL", False),
    ("WL-IN-012", "Cambay Sanand 03", "Sanand Field", "ONGC", 23.0100, 72.3600, "COMPLETED", 1950, "Cambay Shale", "Completed as gas producer", "EXPLORATION", "VERTICAL", False),
    ("WL-IN-013", "Cambay Dahej 04", "Dahej Field", "ONGC", 21.7200, 72.5800, "SUSPENDED", 3240, "Hazad", "Waiting on stimulation unit", "DEVELOPMENT", "DIRECTIONAL", False),

    # --- 3. Assam - Assam-Arakan Basin (5 wells) ---
    ("WL-IN-014", "Assam Digboi Deep 02", "Digboi Field", "Oil India Ltd", 27.3850, 95.6200, "COMPLETED", 3150, "Tipam", "Pumping light sweet crude", "EXPLORATION", "VERTICAL", False),
    ("WL-IN-015", "Assam Naharkatiya 31", "Naharkatiya Field", "Oil India Ltd", 27.2800, 95.3400, "DRILLING", 3450, "Barail", "Running 7 in casing", "DEVELOPMENT", "DIRECTIONAL", False),
    ("WL-IN-016", "Assam Moran 12", "Moran Field", "Oil India Ltd", 27.1800, 94.9300, "COMPLETED", 3620, "Barail", "Gas-condensate production", "DEVELOPMENT", "DIRECTIONAL", False),
    ("WL-IN-017", "Assam Rudrasagar 18", "Rudrasagar Field", "ONGC", 26.9600, 94.6100, "COMPLETED", 3280, "Tipam", "Self-flowing oil well", "DEVELOPMENT", "VERTICAL", False),
    ("WL-IN-018", "Assam Geleki 09", "Geleki Field", "ONGC", 26.8500, 94.8500, "COMPLETED", 4120, "Kopili", "High pressure producer", "DEVELOPMENT", "DIRECTIONAL", False),

    # --- 4. Andhra Pradesh - Krishna-Godavari Basin (5 wells) ---
    ("WL-IN-019", "KG Ravva Offshore 06", "Ravva Offshore", "Cairn Oil & Gas", 16.4850, 82.1600, "COMPLETED", 2780, "Raghavapuram", "Platform-A oil production", "DEVELOPMENT", "DIRECTIONAL", False),
    ("WL-IN-020", "KG Razole Deep 03", "Razole Field", "ONGC", 16.4600, 81.8400, "DRILLING", 3820, "Gollapalli", "Drilling 5-7/8 in high pressure hole", "EXPLORATION", "VERTICAL", False),
    ("WL-IN-021", "KG Kesanapalli 09", "Kesanapalli Field", "ONGC", 16.5200, 82.0200, "COMPLETED", 2650, "Tirupati", "Gas producer on manifold", "DEVELOPMENT", "DIRECTIONAL", False),
    ("WL-IN-022", "KG Mori 02", "Mori Field", "ONGC", 16.3800, 81.7900, "COMPLETED", 2450, "Raghavapuram", "Producing oil with low GOR", "DEVELOPMENT", "VERTICAL", False),
    ("WL-IN-023", "KG Nagayalanka 04", "Nagayalanka Field", "Cairn / ONGC", 16.1200, 81.0100, "SUSPENDED", 3950, "Kommugudem", "Tight gas reservoir evaluation", "DEVELOPMENT", "DIRECTIONAL", False),

    # --- 5. Mumbai Offshore / Maharashtra (3 wells) ---
    ("WL-IN-024", "Mumbai High North 05", "Mumbai High North", "ONGC", 19.4200, 71.3400, "DRILLING", 2150, "Bombay High Limestone", "Sidetracking drain hole", "DEVELOPMENT", "DIRECTIONAL", False),
    ("WL-IN-025", "Mumbai High South 16", "Mumbai High South", "ONGC", 18.9600, 71.4500, "COMPLETED", 2280, "Bombay High Limestone", "ESP platform production", "DEVELOPMENT", "DIRECTIONAL", False),
    ("WL-IN-026", "Mumbai Bassein Gas 04", "Bassein Field", "ONGC", 19.0800, 72.0600, "COMPLETED", 3420, "Bassein", "Major sour gas producer", "DEVELOPMENT", "HORIZONTAL", False),

    # --- 6. Tamil Nadu - Cauvery Basin (2 wells) ---
    ("WL-IN-027", "Cauvery Narimanam 11", "Narimanam Field", "ONGC", 10.8200, 79.7400, "COMPLETED", 2650, "Bhuvanagiri", "Producing sweet light crude", "DEVELOPMENT", "DIRECTIONAL", False),
    ("WL-IN-028", "Cauvery Kamalapuram 03", "Kamalapuram Field", "ONGC", 10.9600, 79.6800, "COMPLETED", 3120, "Nannilam", "Gas producer tied to GCS", "DEVELOPMENT", "VERTICAL", False),

    # --- 7. Other Indian Basins: Tripura & Mahanadi (2 wells) ---
    ("WL-IN-029", "Tripura Rokhia Gas 07", "Rokhia Field", "ONGC", 23.6300, 91.2800, "COMPLETED", 2850, "Bhuban", "Supplying gas to Rokhia thermal plant", "DEVELOPMENT", "VERTICAL", False),
    ("WL-IN-030", "Mahanadi Deepwater 01", "Mahanadi Offshore", "Reliance-BP", 20.0800, 86.8200, "COMPLETED", 3750, "Mahanadi Carbonate", "Deepwater appraisal gas discovery", "EXPLORATION", "DIRECTIONAL", False),
]

# Formations per well intervals (top, bottom in meters)
INTERVALS: dict[str, list[tuple[str, float, float]]] = {
    # Barmer
    "WL-IN-001": [("Thumbli", 800, 1400), ("Dharvi Dungar", 1400, 1950), ("Barmer Hill", 1950, 2250), ("Fatehgarh", 2250, 2600)],
    "WL-IN-002": [("Thumbli", 850, 1450), ("Dharvi Dungar", 1450, 2050), ("Barmer Hill", 2050, 2400), ("Fatehgarh", 2400, 2750)],
    "WL-IN-003": [("Dharvi Dungar", 1300, 1900), ("Barmer Hill", 1900, 2200), ("Fatehgarh", 2200, 2580)],
    "WL-IN-004": [("Thumbli", 900, 1500), ("Dharvi Dungar", 1500, 2200), ("Fatehgarh", 2200, 2500)],
    "WL-IN-005": [("Thumbli", 1000, 1700), ("Dharvi Dungar", 1700, 2400), ("Barmer Hill", 2400, 2750), ("Fatehgarh", 2750, 3050)],
    "WL-IN-006": [("Dharvi Dungar", 1200, 1800), ("Barmer Hill", 1800, 2100), ("Fatehgarh", 2100, 2450)],
    "WL-IN-007": [("Thumbli", 950, 1550), ("Dharvi Dungar", 1550, 2150), ("Barmer Hill", 2150, 2650)],
    # Cambay
    "WL-IN-008": [("Kalol", 1400, 1850), ("Ankleshwar", 1850, 2250), ("Cambay Shale", 2250, 2500)],
    "WL-IN-009": [("Kalol", 1600, 2100), ("Hazad", 2100, 2700), ("Cambay Shale", 2700, 3100)],
    "WL-IN-010": [("Kalol", 1500, 1950), ("Cambay Shale", 1950, 2200)],
    "WL-IN-011": [("Kalol", 1650, 2200), ("Cambay Shale", 2200, 2550)],
    "WL-IN-012": [("Kalol", 1300, 1700), ("Cambay Shale", 1700, 2050)],
    "WL-IN-013": [("Kalol", 1700, 2250), ("Hazad", 2250, 2900), ("Cambay Shale", 2900, 3350)],
    # Assam
    "WL-IN-014": [("Girujan Clay", 1200, 2000), ("Tipam", 2000, 2900), ("Barail", 2900, 3250)],
    "WL-IN-015": [("Girujan Clay", 1400, 2200), ("Tipam", 2200, 3000), ("Barail", 3000, 3600)],
    "WL-IN-016": [("Girujan Clay", 1500, 2300), ("Tipam", 2300, 3100), ("Barail", 3100, 3750)],
    "WL-IN-017": [("Tipam", 1800, 2750), ("Barail", 2750, 3400)],
    "WL-IN-018": [("Tipam", 2100, 3000), ("Barail", 3000, 3700), ("Kopili", 3700, 4200)],
    # KG Basin
    "WL-IN-019": [("Tirupati", 1400, 2100), ("Raghavapuram", 2100, 2850)],
    "WL-IN-020": [("Tirupati", 1800, 2600), ("Raghavapuram", 2600, 3400), ("Gollapalli", 3400, 3950)],
    "WL-IN-021": [("Tirupati", 1500, 2300), ("Raghavapuram", 2300, 2750)],
    "WL-IN-022": [("Tirupati", 1300, 1950), ("Raghavapuram", 1950, 2550)],
    "WL-IN-023": [("Raghavapuram", 2200, 3100), ("Gollapalli", 3100, 3600), ("Kommugudem", 3600, 4050)],
    # Mumbai Offshore
    "WL-IN-024": [("Mukta", 1100, 1600), ("Bombay High Limestone", 1600, 2250), ("Panna", 2250, 2400)],
    "WL-IN-025": [("Mukta", 1200, 1750), ("Bombay High Limestone", 1750, 2350)],
    "WL-IN-026": [("Mukta", 1600, 2300), ("Bassein", 2300, 3250), ("Panna", 3250, 3550)],
    # Cauvery
    "WL-IN-027": [("Nannilam", 1500, 2150), ("Bhuvanagiri", 2150, 2750)],
    "WL-IN-028": [("Nannilam", 1800, 2700), ("Bhuvanagiri", 2700, 3250)],
    # Tripura & Mahanadi
    "WL-IN-029": [("Bokabil", 1200, 2050), ("Bhuban", 2050, 2950)],
    "WL-IN-030": [("Mahanadi Carbonate", 2200, 3850)],
}

# Historical drilling events for Indian wells
INDIAN_EVENTS = [
    ("WL-IN-001", "STUCK_PIPE", "STUCK_PIPE", 2380, "Fatehgarh", "At 2380 m while drilling Barmer Mangala 01 through Fatehgarh sandstone, tight hole and high torque led to stuck pipe indicator. Drill string was worked with 45 klb overpull and freed.", "Worked the pipe with jars and reduced WOB", "Pipe freed and drilling resumed", date(2024, 2, 10)),
    ("WL-IN-002", "KICK", "KICK", 2450, "Barmer Hill", "At 2450 m a gas kick was detected in Barmer Hill siliceous shale on Barmer Bhagyam 02. Annular preventer was closed and influx circulated out via choke manifold.", "Shut in the well and weighted up mud by 0.6 ppg", "Pressure stabilized with zero surface gas", date(2023, 11, 14)),
    ("WL-IN-003", "LOST_CIRCULATION", "LOST_CIRCULATION", 2180, "Barmer Hill", "At 2180 m lost circulation occurred in fractured Barmer Hill formation with 45 bph mud loss. Pumped high-viscosity pill with coarse calcium carbonate LCM.", "Pumped 40 bbl LCM pill and reduced pump rate", "Circulation restored to 98 percent returns", date(2023, 8, 22)),
    ("WL-IN-007", "TORQUE", "TORQUE", 2520, "Barmer Hill", "At 2520 m excessive torque fluctuations observed in Barmer Kameshwari 05 directional build section. Reamed hole and applied lubricant to mud system.", "Reduced RPM to 80 and added lubricant", "Torque stabilized within baseline threshold", date(2024, 1, 19)),
    ("WL-IN-008", "MUD", "MUD", 2140, "Ankleshwar", "At 2140 m gas-cut mud reported in Cambay Ankleshwar 14 while penetrating deltaic sands. Viscosity rose and mud density dropped to 1.05 sg.", "Increased mud weight to 1.18 sg and degassed pit", "Mud parameters stabilized", date(2023, 5, 27)),
    ("WL-IN-009", "OVERPRESSURE", "KICK", 2740, "Hazad", "At 2740 m abnormal pore pressure encountered in Hazad sands on Cambay Gandhar 08. Standpipe pressure spiked by 280 psi with pit gain of 12 bbl.", "Shut in well and established kill mud weight", "Well killed and secondary barrier restored", date(2024, 3, 2)),
    ("WL-IN-010", "LOST_CIRCULATION", "LOST_CIRCULATION", 1920, "Kalol", "At 1920 m partial losses of 20 bph observed in Kalol pay sand. Spotted 25 bbl nut-plug and fiber pill.", "Pumped fiber LCM and paused drilling", "Losses reduced to seepage level", date(2022, 10, 11)),
    ("WL-IN-015", "STUCK_PIPE", "STUCK_PIPE", 3320, "Barail", "At 3320 m differential sticking occurred in Barail coal-shale transition on Assam Naharkatiya 31. Spotted organic pipe-freeing soak.", "Spotted 35 bbl oil-based freeing soak and jarred", "String freed after 4 hours jarring", date(2023, 9, 5)),
    ("WL-IN-018", "CEMENTING", "CEMENTING", 3980, "Kopili", "At 3980 m intermediate casing cement job showed channeling through high-pressure Kopili shale. Squeeze cementing performed at shoe.", "Performed hesitation squeeze with micro-fine cement", "Shoe test held to 16.5 ppg equivalent", date(2023, 4, 18)),
    ("WL-IN-020", "KICK", "KICK", 3640, "Gollapalli", "At 3640 m high-pressure deep gas influx encountered in KG Razole Deep 03 Gollapalli formation. SICP reached 720 psi.", "Bulls-headed kill mud and circulated through degasser", "Influx evacuated and pressure normalized", date(2024, 1, 8)),
    ("WL-IN-024", "TORQUE", "TORQUE", 2050, "Bombay High Limestone", "At 2050 m severe torque oscillation in horizontal drainhole through Bombay High Limestone. Bit balling and carbonate fines suspected.", "Pumped acid wash pill and reduced WOB", "Torque smoothed and drilling rate increased", date(2024, 2, 28)),
    ("WL-IN-026", "MUD", "MUD", 3180, "Bassein", "At 3180 m hydrogen sulfide trace detected in drilling fluid from Bassein sour carbonate. Added H2S scavenger to active system.", "Treated mud with zinc-based H2S scavenger", "Atmospheric and mud sensors cleared", date(2023, 12, 15)),
    ("WL-IN-027", "LOST_CIRCULATION", "LOST_CIRCULATION", 2480, "Bhuvanagiri", "At 2480 m total lost circulation encountered in vuggy Bhuvanagiri sandstone in Cauvery Basin. Pumped thixotropic cement plug.", "Set 50 bbl balanced thixotropic cement plug", "Drilled out plug with full returns", date(2023, 7, 30)),
]


def purge_foreign_data(db) -> None:
    """Removes all previous foreign well records and dependent rows."""
    print("Purging existing / foreign well records to establish clean Indian MVP dataset...")
    # Delete child dependencies in correct order
    db.query(EngineeringReview).delete(synchronize_session=False)
    db.query(Evidence).delete(synchronize_session=False)
    db.query(DrillingEvent).delete(synchronize_session=False)
    db.query(NlpEntity).delete(synchronize_session=False)
    db.query(OcrResult).delete(synchronize_session=False)
    db.query(ReportPage).delete(synchronize_session=False)
    db.query(HistoricalReport).delete(synchronize_session=False)
    db.query(DrillingParameter).delete(synchronize_session=False)
    db.query(RiskEvent).delete(synchronize_session=False)
    db.query(RiskPrediction).delete(synchronize_session=False)
    db.query(Alert).delete(synchronize_session=False)
    db.query(WellSimilarity).delete(synchronize_session=False)
    db.query(WellTrajectory).delete(synchronize_session=False)
    db.query(WellCoordinate).delete(synchronize_session=False)
    db.query(WellFormation).delete(synchronize_session=False)
    db.query(Well).delete(synchronize_session=False)
    db.commit()
    print("Foreign data purge complete.")


def seed(clean: bool = True) -> None:
    db = SessionLocal()
    try:
        # 1. Ensure Roles
        roles: dict[str, Role] = {}
        for name, description in (
            ("ADMIN", "User, threshold, and system administration"),
            ("DRILLING_ENGINEER", "Engineering review, uploads, and well maintenance"),
            ("VIEWER", "Read-only access"),
        ):
            role = db.query(Role).filter(Role.name == name).one_or_none()
            if role is None:
                role = Role(name=name, description=description)
                db.add(role)
                db.flush()
            roles[name] = role
        db.commit()

        # 2. Ensure Demo Users
        users: dict[str, User] = {}
        for username, email, password, full_name, role_name in USERS:
            user = db.query(User).filter(User.username == username).one_or_none()
            if user is None:
                user = User(
                    username=username,
                    email=email,
                    password_hash=hash_password(password),
                    full_name=full_name,
                    role_id=roles[role_name].id,
                    is_active=True,
                )
                db.add(user)
                db.flush()
            users[username] = user
        db.commit()

        # 3. Clean previous foreign wells if requested or existing wells are foreign
        existing_well_count = db.query(Well).count()
        if clean or existing_well_count != 30:
            purge_foreign_data(db)

        # 4. Upsert Indian Formations
        formations: dict[str, Formation] = {}
        for name, description in INDIAN_FORMATIONS:
            form = db.query(Formation).filter(Formation.name == name).one_or_none()
            if form is None:
                form = Formation(name=name, description=description)
                db.add(form)
                db.flush()
            formations[name] = form
        db.commit()

        # 5. Insert Exactly 30 Indian MVP Demo Wells
        wells: dict[str, Well] = {}
        print(f"Creating exactly {len(INDIAN_WELLS)} Indian MVP demo wells...")
        for code, name, field, operator, lat, lon, status, depth, formation, operation, well_type, trajectory, simulate in INDIAN_WELLS:
            well = Well(
                well_code=code,
                well_name=name,
                field=field,
                operator=operator,
                status=status,
                current_depth=depth,
                current_formation=formation,
                current_operation=operation,
                spud_date=date(2023, 6, 1),
                completion_date=None if status == "DRILLING" else date(2024, 4, 15),
                well_type=well_type,
                trajectory_type=trajectory,
                source_type="DEMO",
                simulate_sensors=simulate,
                demo_scenario="KICK_WARNING" if code == "WL-IN-001" else "normal",
                created_by=users["admin"].id,
            )
            db.add(well)
            db.flush()
            wells[code] = well

            # PostGIS / Geographic coordinates
            upsert_coordinate(db, well, lat, lon)

            # Trajectory Stations (8 stations)
            stations = []
            for index in range(8):
                stations.append(
                    {
                        "station_index": index,
                        "measured_depth": round(depth * (index + 1) / 8, 1),
                        "tvd": round(depth * (index + 1) / 8 * (0.97 if trajectory != "HORIZONTAL" else 0.84), 1),
                        "inclination": 8 * index if trajectory == "DIRECTIONAL" else (72 if trajectory == "HORIZONTAL" and index > 4 else 2),
                        "azimuth": 45,
                        "latitude": round(lat + index * 0.0003, 6),
                        "longitude": round(lon + index * 0.0003, 6),
                    }
                )
            replace_trajectory(db, well, stations)

            # Formation intervals
            if code in INTERVALS:
                for fname, top, bottom in INTERVALS[code]:
                    if fname in formations:
                        db.add(WellFormation(well_id=well.id, formation_id=formations[fname].id, depth_top=top, depth_bottom=bottom))

        db.commit()
        print(f"Successfully created {len(wells)} Indian wells in database.")

        # 6. Seed Drilling Parameters for Primary Active Well (WL-IN-001)
        primary = wells["WL-IN-001"]
        now = datetime.now(timezone.utc)
        print("Generating telemetry stream for primary well WL-IN-001...")
        for index in range(40):
            stamp = now - timedelta(minutes=(40 - index) * 2)
            db.add(
                DrillingParameter(
                    well_id=primary.id,
                    recorded_at=stamp,
                    depth=round(2420 + index * 0.75, 1),
                    rop=round(16.5 + math.sin(index / 3) * 3, 1),
                    wob=round(22.0 + 0.4 * math.sin(index / 4), 1),
                    rpm=round(118 + math.sin(index / 2) * 5),
                    torque=round(24.5 + 1.2 * math.sin(index / 5), 1),
                    standpipe_pressure=round(3150 + 40 * math.sin(index / 3)),
                    mud_flow=round(625 + 10 * math.sin(index / 4)),
                    mud_weight=1.18,
                    pump_pressure=round(3100 + 35 * math.sin(index / 3)),
                    hook_load=round(175 + math.sin(index / 6) * 5),
                    source="HISTORICAL",
                    provenance="HISTORICAL REPORT",
                )
            )
        db.commit()

        # 7. Create Historical Report and process with OCR/NLP
        upload_root = Path(get_settings().upload_directory) / "reports"
        upload_root.mkdir(parents=True, exist_ok=True)
        source = Path(__file__).with_name("WCR_DEMO_001.txt")
        target = upload_root / "WCR_DEMO_001.txt"
        target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")

        report = HistoricalReport(
            well_id=wells["WL-IN-002"].id,
            title="WCR_DEMO_001 Barmer Bhagyam 02",
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

        # 8. Seed Historical Events and Evidence for Indian Wells
        print("Inserting historical drilling events and evidence records...")
        for code, event_type, risk, depth, formation, description, action, outcome, event_date in INDIAN_EVENTS:
            well = wells.get(code)
            if not well:
                continue
            form_row = formations.get(formation)
            event = DrillingEvent(
                well_id=well.id,
                depth_start=depth,
                depth_end=depth,
                formation_id=form_row.id if form_row else None,
                formation_name=formation,
                event_type=event_type,
                description=description,
                action_taken=action,
                outcome=outcome,
                risk_category=risk,
                event_date=event_date,
                confidence=0.92,
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
                    source_location=f"Indian Basin Historical Record · {well.well_name}",
                    confidence=0.92,
                )
            )
        db.commit()

        # 9. Update Full-Text Search Vectors
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
                SET search_vector = to_tsvector('english', coalesce(text_excerpt,'') || ' ' || coalesce(formation,'') || ' ' || coalesce(source_location,''))
                """
            )
        )
        db.commit()

        # 10. Recalculate Pairwise Similarity for all 30 Wells
        print("Recalculating similarity across all 30 Indian wells...")
        cfg = db.get(SystemConfig, "similarity_weights")
        if not cfg:
            db.add(SystemConfig(key="similarity_weights", value={"geographic": 0.20, "formation": 0.25, "depth": 0.20, "trajectory": 0.15, "event": 0.20}))
            db.commit()
        for well in wells.values():
            similar_wells(db, well, limit=10, persist=True)
        print("Similarity calculations completed.")

        # 11. Ensure Thresholds and Run Risk Analysis on Active Wells
        ensure_thresholds(db)
        print("Running risk analysis on active drilling wells...")
        for code in ["WL-IN-001", "WL-IN-009", "WL-IN-015", "WL-IN-020", "WL-IN-024"]:
            active_well = wells.get(code)
            if active_well:
                analyze_well(db, active_well, create_alerts=True)

        # 12. Engineering Review
        db.add(
            EngineeringReview(
                well_id=primary.id,
                engineer_id=users["engineer"].id,
                decision="MONITOR",
                comment="DEMO review: Barmer Mangala 01 active drilling scan reviewed. Offset Barmer Bhagyam 02 kick history noted in Barmer Hill formation. Controlled penetration rate recommended.",
                risk_category="STUCK_PIPE",
                snapshot={"source": "DEMO_BARMER", "well_id": primary.well_code},
            )
        )
        db.commit()

        total_wells = db.query(Well).count()
        print(f"=== SEED COMPLETE ===")
        print(f"Total Wells in Database: {total_wells} (Target: 30)")
        print(f"Events: {db.query(DrillingEvent).count()}, Evidence: {db.query(Evidence).count()}")
        print(f"Similarities: {db.query(WellSimilarity).count()}, Reports: {db.query(HistoricalReport).count()}")
    finally:
        db.close()


if __name__ == "__main__":
    clean_mode = "--no-clean" not in sys.argv
    seed(clean=clean_mode)
