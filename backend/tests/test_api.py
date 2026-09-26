import socket
import uuid

import pytest

def _db_up() -> bool:
    try:
        sock = socket.create_connection(("127.0.0.1", 5432), 1)
        sock.close()
        return True
    except OSError:
        return False


if _db_up():
    from fastapi.testclient import TestClient
    from app.main import app
    client = TestClient(app)
else:
    client = None


pytestmark = pytest.mark.skipif(not _db_up(), reason="PostgreSQL/PostGIS is not reachable")


def login(username: str, password: str) -> str:
    response = client.post("/api/auth/login", json={"username": username, "password": password, "remember": False})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["success"] is True
    return body["data"]["access_token"]


def auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_health_and_postgis():
    health = client.get("/health")
    assert health.status_code == 200
    db = client.get("/api/health/database")
    assert db.status_code == 200
    assert "postgis" in db.json()["data"]["postgis"].lower() or db.json()["data"]["postgis"]


def test_rbac_viewer_cannot_create_well_or_change_threshold():
    viewer = login("viewer", "Viewer123!")
    engineer = login("engineer", "Engineer123!")
    admin = login("admin", "Admin123!")
    created = client.post(
        "/api/wells",
        headers=auth(viewer),
        json={
            "well_id": f"WL-TEST-{uuid.uuid4().hex[:6]}",
            "well_name": "Denied",
            "field": "North Rift",
            "operator": "Test",
            "latitude": 31.8,
            "longitude": -102.3,
        },
    )
    assert created.status_code == 403
    code = f"WL-T{uuid.uuid4().hex[:6]}"
    ok = client.post(
        "/api/wells",
        headers=auth(engineer),
        json={
            "well_id": code,
            "well_name": "API Test Well",
            "field": "North Rift",
            "operator": "Test",
            "latitude": 31.86,
            "longitude": -102.34,
            "status": "PLANNED",
            "formation": "Wolfcamp",
            "current_depth": 1000,
        },
    )
    assert ok.status_code == 200, ok.text
    nearby = client.get("/api/wells/nearby", headers=auth(engineer), params={"latitude": 31.85, "longitude": -102.35, "radius": 25})
    assert nearby.status_code == 200
    assert nearby.json()["data"]
    assert nearby.json()["data"][0]["distance_method"].startswith("PostGIS")
    blocked = client.put(
        "/api/admin/risk-thresholds/STUCK_PIPE",
        headers=auth(engineer),
        json={"cooldown_minutes": 45},
    )
    assert blocked.status_code == 403
    changed = client.put(
        "/api/admin/risk-thresholds/STUCK_PIPE",
        headers=auth(admin),
        json={"cooldown_minutes": 30},
    )
    assert changed.status_code == 200
    logs = client.get("/api/admin/audit-logs", headers=auth(admin))
    assert logs.status_code == 200
    assert any(item["action"] == "CONFIG_CHANGE" for item in logs.json()["data"]["items"])


def test_upload_search_similarity_and_risk():
    engineer = login("engineer", "Engineer123!")
    wells = client.get("/api/wells", headers=auth(engineer), params={"q": "WL-001"})
    well = wells.json()["data"]["items"][0]
    content = (pytest.importorskip("pathlib").Path(__file__).resolve().parents[2] / "scripts" / "WCR_DEMO_001.txt").read_bytes()
    upload = client.post(
        "/api/reports/upload",
        headers=auth(engineer),
        data={"title": "API upload demo", "report_type": "WCR", "well_id": "WL-002"},
        files={"file": ("WCR_DEMO_001.txt", content, "text/plain")},
    )
    assert upload.status_code == 200, upload.text
    report_id = upload.json()["data"]["id"]
    from app.core.database import SessionLocal
    from app.services.report_service import process_report
    from uuid import UUID

    db = SessionLocal()
    try:
        process_report(db, UUID(report_id))
    finally:
        db.close()
    detail = client.get(f"/api/reports/{report_id}", headers=auth(engineer))
    assert detail.json()["data"]["status"] == "COMPLETED"
    entities = client.get(f"/api/reports/{report_id}/entities", headers=auth(engineer))
    assert any(item["entity_type"] == "DEPTH" for item in entities.json()["data"])
    found = client.get("/api/search", headers=auth(engineer), params={"q": "stuck pipe"})
    assert found.status_code == 200
    assert found.json()["data"]["events"] or found.json()["data"]["evidence"]
    similar = client.get(f"/api/wells/{well['id']}/similar", headers=auth(engineer))
    assert similar.status_code == 200
    assert "overall_score" in similar.json()["data"][0]
    risk = client.post("/api/risk/analyze", headers=auth(engineer), json={"well_id": well["id"]})
    assert risk.status_code == 200
    assert len(risk.json()["data"]) == 6
    evidence_id = None
    for item in risk.json()["data"]:
        if item["evidence"]:
            evidence_id = item["evidence"][0]["id"]
            break
    if evidence_id:
        evidence = client.get(f"/api/evidence/{evidence_id}", headers=auth(engineer))
        assert evidence.status_code == 200
        assert evidence.json()["data"]["text_excerpt"]
    review = client.post(
        "/api/reviews",
        headers=auth(engineer),
        json={"well_id": well["id"], "decision": "REVIEW", "comment": "API test review. No parameter change authorized.", "risk_category": "STUCK_PIPE"},
    )
    assert review.status_code == 200
    logout = client.post("/api/auth/logout", headers=auth(engineer))
    assert logout.status_code == 200
    reused = client.get("/api/auth/me", headers=auth(engineer))
    assert reused.status_code == 401
