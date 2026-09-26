from pathlib import Path

from app.services.nlp_service import extract_entities, extract_events

REPORT = Path(__file__).resolve().parents[2] / "scripts" / "WCR_DEMO_001.txt"


def test_demo_report_extracts_depth_formation_and_events():
    text = REPORT.read_text(encoding="utf-8")
    entities = extract_entities(text)
    types = {item.entity_type for item in entities}
    assert "DEPTH" in types
    assert "FORMATION" in types
    events = extract_events(text, "2024-03-12")
    categories = {event.risk_category for event in events}
    assert "STUCK_PIPE" in categories
    assert "KICK" in categories
    assert "LOST_CIRCULATION" in categories
    stuck = next(event for event in events if event.risk_category == "STUCK_PIPE")
    assert stuck.depth_start == 2450
    assert stuck.formation == "Wolfcamp"
    assert stuck.action_taken == "Reduced WOB"
    assert stuck.outcome == "Torque stabilized"


def test_extraction_confidence_is_present():
    events = extract_events("At 1800 m, lost circulation was observed in the Dean Formation. LCM was pumped.")
    assert events
    assert 0 < events[0].confidence <= 0.95
