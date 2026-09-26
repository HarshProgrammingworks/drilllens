import sys
from fastapi.testclient import TestClient
from app.main import app

def run_tests():
    client = TestClient(app)
    
    print("=" * 60)
    print("DRILLLENS RBAC VERIFICATION TEST SUITE")
    print("=" * 60)

    # 1. ADMIN TESTS
    print("\n[1] Testing ADMIN Role (admin / Admin123!)")
    res = client.post("/api/auth/login", json={"username": "admin", "password": "Admin123!"})
    assert res.status_code == 200, f"Admin login failed: {res.text}"
    admin_data = res.json()["data"]
    admin_token = admin_data["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    print(f" -> Logged in as ADMIN ({admin_data['user']['role']})")
    print(f" -> Permissions count: {len(admin_data['user'].get('permissions', []))}")
    assert "users:manage" in admin_data["user"].get("permissions", [])

    # Admin access to admin users list
    res = client.get("/api/admin/users", headers=admin_headers)
    assert res.status_code == 200, f"Admin cannot view users: {res.text}"
    print(" -> Admin can access /api/admin/users: OK (200)")

    # Admin access to audit logs
    res = client.get("/api/admin/audit-logs", headers=admin_headers)
    assert res.status_code == 200, f"Admin cannot view audit logs: {res.text}"
    print(" -> Admin can access /api/admin/audit-logs: OK (200)")

    # Admin access to system config
    res = client.get("/api/admin/system", headers=admin_headers)
    assert res.status_code == 200, f"Admin cannot access system: {res.text}"
    print(" -> Admin can access /api/admin/system: OK (200)")


    # 2. DRILLING ENGINEER TESTS
    print("\n[2] Testing DRILLING_ENGINEER Role (engineer / Engineer123!)")
    res = client.post("/api/auth/login", json={"username": "engineer", "password": "Engineer123!"})
    assert res.status_code == 200, f"Engineer login failed: {res.text}"
    eng_data = res.json()["data"]
    eng_token = eng_data["access_token"]
    eng_headers = {"Authorization": f"Bearer {eng_token}"}
    print(f" -> Logged in as DRILLING_ENGINEER ({eng_data['user']['role']})")
    assert "wells:create" in eng_data["user"].get("permissions", [])
    assert "users:manage" not in eng_data["user"].get("permissions", [])

    # Engineer can view wells
    res = client.get("/api/wells", headers=eng_headers)
    assert res.status_code == 200
    print(" -> Engineer can view /api/wells: OK (200)")

    # Engineer can view audit logs
    res = client.get("/api/admin/audit-logs", headers=eng_headers)
    assert res.status_code == 200
    print(" -> Engineer can view /api/admin/audit-logs: OK (200)")

    # Engineer FORBIDDEN from user management
    res = client.get("/api/admin/users", headers=eng_headers)
    assert res.status_code == 403, f"Expected 403 for engineer accessing /admin/users, got {res.status_code}"
    print(" -> Engineer blocked from /api/admin/users: OK (403 FORBIDDEN)")

    # Engineer FORBIDDEN from system management
    res = client.get("/api/admin/system", headers=eng_headers)
    assert res.status_code == 403, f"Expected 403 for engineer accessing /admin/system, got {res.status_code}"
    print(" -> Engineer blocked from /api/admin/system: OK (403 FORBIDDEN)")


    # 3. VIEWER TESTS
    print("\n[3] Testing VIEWER Role (viewer / Viewer123!)")
    res = client.post("/api/auth/login", json={"username": "viewer", "password": "Viewer123!"})
    assert res.status_code == 200, f"Viewer login failed: {res.text}"
    viewer_data = res.json()["data"]
    viewer_token = viewer_data["access_token"]
    viewer_headers = {"Authorization": f"Bearer {viewer_token}"}
    print(f" -> Logged in as VIEWER ({viewer_data['user']['role']})")
    assert "wells:view" in viewer_data["user"].get("permissions", [])
    assert "wells:create" not in viewer_data["user"].get("permissions", [])

    # Viewer CAN view wells
    res = client.get("/api/wells", headers=viewer_headers)
    assert res.status_code == 200
    print(" -> Viewer can view /api/wells: OK (200)")

    # Viewer CAN view reports
    res = client.get("/api/reports", headers=viewer_headers)
    assert res.status_code == 200
    print(" -> Viewer can view /api/reports: OK (200)")

    # Viewer FORBIDDEN from creating a well
    res = client.post("/api/wells", json={"well_id": "TEST-V-01", "well_name": "Test", "field": "Mumbai", "operator": "ONGC", "status": "PLANNED", "latitude": 18.5, "longitude": 72.8}, headers=viewer_headers)
    assert res.status_code == 403, f"Expected 403 for viewer creating well, got {res.status_code}"
    print(" -> Viewer blocked from creating well: OK (403 FORBIDDEN)")

    # Viewer FORBIDDEN from creating review
    res = client.post("/api/reviews", json={"decision": "REVIEW", "comment": "test"}, headers=viewer_headers)
    assert res.status_code == 403, f"Expected 403 for viewer creating review, got {res.status_code}"
    print(" -> Viewer blocked from creating engineering review: OK (403 FORBIDDEN)")

    # Viewer FORBIDDEN from user management
    res = client.get("/api/admin/users", headers=viewer_headers)
    assert res.status_code == 403, f"Expected 403 for viewer accessing /admin/users, got {res.status_code}"
    print(" -> Viewer blocked from /api/admin/users: OK (403 FORBIDDEN)")

    # Viewer FORBIDDEN from audit logs
    res = client.get("/api/admin/audit-logs", headers=viewer_headers)
    assert res.status_code == 403, f"Expected 403 for viewer accessing /admin/audit-logs, got {res.status_code}"
    print(" -> Viewer blocked from /api/admin/audit-logs: OK (403 FORBIDDEN)")

    print("\n" + "=" * 60)
    print("ALL RBAC TESTS PASSED SUCCESSFULLY!")
    print("=" * 60)

if __name__ == "__main__":
    run_tests()
