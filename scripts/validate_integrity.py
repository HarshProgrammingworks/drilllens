"""Data Integrity Verification Script for DrillLens.

Validates that:
- Total wells = exactly 30
- Every well has valid ID, coordinates, Indian bounding box location, field, formation, status
- Every event references a valid well_id
- Every report references a valid well_id
- Every evidence record has valid well/report/event relationships (no broken foreign links)
- Every risk record references a valid well_id
- Every similarity record references a valid source well and comparison well
- Every alert references a valid well_id
- Zero orphaned records
"""

from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CANDIDATES = [Path("/app"), HERE.parent / "backend", HERE.parent]
for candidate in CANDIDATES:
    if (candidate / "app").is_dir():
        sys.path.insert(0, str(candidate))
        break

from app.core.database import SessionLocal
from app.models import (
    Alert,
    DrillingEvent,
    DrillingParameter,
    EngineeringReview,
    Evidence,
    HistoricalReport,
    RiskEvent,
    RiskPrediction,
    Well,
    WellCoordinate,
    WellFormation,
    WellSimilarity,
    WellTrajectory,
)

INDIA_LAT_MIN, INDIA_LAT_MAX = 6.0, 38.0
INDIA_LON_MIN, INDIA_LON_MAX = 68.0, 98.0


def validate() -> bool:
    db = SessionLocal()
    errors: list[str] = []
    try:
        # 1. Total Wells Check
        wells = db.query(Well).all()
        well_count = len(wells)
        print(f"[CHECK 1] Total wells in database: {well_count}")
        if well_count != 30:
            errors.append(f"Expected exactly 30 wells, found {well_count}")

        well_ids = {w.id for w in wells}
        well_codes = {w.well_code for w in wells}

        # 2. Coordinates & Indian Geographic Bounding Box Check
        for w in wells:
            coord = db.query(WellCoordinate).filter(WellCoordinate.well_id == w.id).one_or_none()
            if not coord:
                errors.append(f"Well {w.well_code} has no coordinate record")
                continue
            if not (INDIA_LAT_MIN <= coord.latitude <= INDIA_LAT_MAX):
                errors.append(f"Well {w.well_code} latitude {coord.latitude} outside Indian bounds")
            if not (INDIA_LON_MIN <= coord.longitude <= INDIA_LON_MAX):
                errors.append(f"Well {w.well_code} longitude {coord.longitude} outside Indian bounds")
            if not w.field:
                errors.append(f"Well {w.well_code} is missing field/basin")
            if not w.current_formation:
                errors.append(f"Well {w.well_code} is missing current_formation")
            if not w.status:
                errors.append(f"Well {w.well_code} is missing status")

        # 3. Check Drilling Events
        events = db.query(DrillingEvent).all()
        print(f"[CHECK 2] Total historical drilling events: {len(events)}")
        for ev in events:
            if ev.well_id not in well_ids:
                errors.append(f"Event {ev.id} references invalid well_id {ev.well_id}")

        # 4. Check Historical Reports
        reports = db.query(HistoricalReport).all()
        print(f"[CHECK 3] Total historical reports: {len(reports)}")
        report_ids = {r.id for r in reports}
        for r in reports:
            if r.well_id and r.well_id not in well_ids:
                errors.append(f"Report {r.id} references invalid well_id {r.well_id}")

        # 5. Check Evidence Records
        evidence_rows = db.query(Evidence).all()
        print(f"[CHECK 4] Total evidence records: {len(evidence_rows)}")
        event_ids = {ev.id for ev in events}
        for ev in evidence_rows:
            if ev.well_id and ev.well_id not in well_ids:
                errors.append(f"Evidence {ev.id} references invalid well_id {ev.well_id}")
            if ev.report_id and ev.report_id not in report_ids:
                errors.append(f"Evidence {ev.id} references invalid report_id {ev.report_id}")
            if ev.event_id and ev.event_id not in event_ids:
                errors.append(f"Evidence {ev.id} references invalid event_id {ev.event_id}")

        # 6. Check Risk Predictions & Events
        predictions = db.query(RiskPrediction).all()
        print(f"[CHECK 5] Total risk predictions: {len(predictions)}")
        pred_ids = {p.id for p in predictions}
        for p in predictions:
            if p.well_id not in well_ids:
                errors.append(f"RiskPrediction {p.id} references invalid well_id {p.well_id}")

        risk_events = db.query(RiskEvent).all()
        print(f"[CHECK 6] Total risk events: {len(risk_events)}")
        for re in risk_events:
            if re.well_id not in well_ids:
                errors.append(f"RiskEvent {re.id} references invalid well_id {re.well_id}")
            if re.prediction_id and re.prediction_id not in pred_ids:
                errors.append(f"RiskEvent {re.id} references invalid prediction_id {re.prediction_id}")

        # 7. Check Well Similarity Pairs
        similarities = db.query(WellSimilarity).all()
        print(f"[CHECK 7] Total pairwise similarity records: {len(similarities)}")
        for sim in similarities:
            if sim.well_id not in well_ids:
                errors.append(f"WellSimilarity {sim.id} has invalid source well_id {sim.well_id}")
            if sim.other_well_id not in well_ids:
                errors.append(f"WellSimilarity {sim.id} has invalid comparison other_well_id {sim.other_well_id}")

        # 8. Check Alerts
        alerts = db.query(Alert).all()
        print(f"[CHECK 8] Total alerts: {len(alerts)}")
        for al in alerts:
            if al.well_id not in well_ids:
                errors.append(f"Alert {al.id} references invalid well_id {al.well_id}")

        # 9. Check Trajectories
        trajectories = db.query(WellTrajectory).all()
        print(f"[CHECK 9] Total trajectory stations: {len(trajectories)}")
        for tr in trajectories:
            if tr.well_id not in well_ids:
                errors.append(f"Trajectory {tr.id} references invalid well_id {tr.well_id}")

        # 10. Check Reviews
        reviews = db.query(EngineeringReview).all()
        print(f"[CHECK 10] Total engineering reviews: {len(reviews)}")
        for rv in reviews:
            if rv.well_id and rv.well_id not in well_ids:
                errors.append(f"Review {rv.id} references invalid well_id {rv.well_id}")

        # Print Result Summary
        print("-" * 60)
        if errors:
            print(f"FAILED: Found {len(errors)} data integrity errors:")
            for err in errors[:20]:
                print(f" - {err}")
            return False
        else:
            print("SUCCESS: 100% DATA INTEGRITY VERIFIED!")
            print("[OK] Exactly 30 Wells")
            print("[OK] All 30 Wells have valid Indian coordinates and formations")
            print("[OK] Zero orphaned records in events, reports, evidence, risk, similarities, or alerts.")
            return True
    finally:
        db.close()


if __name__ == "__main__":
    success = validate()
    sys.exit(0 if success else 1)
