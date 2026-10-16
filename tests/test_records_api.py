
from fastapi.testclient import TestClient
from conftest import ROOT, load_module

def test_records_api_crud_and_openapi(monkeypatch):
    monkeypatch.setenv("DOMAIN_PROFILE","manufacturing-field-ops"); module=load_module("records_app_test", ROOT/"src"/"records-api"/"app.py"); client=TestClient(module.app)
    assert client.get("/healthz").json()["status"]=="ok"; records=client.get("/records").json(); assert records
    assert client.get(f"/records/{records[0]['id']}").json()["id"]==records[0]["id"]
    created=client.post("/records",json={"title":"Validate new request","description":"Created by offline test","priority":"low","assigned_to":"Test owner","location":"Test area","items_required":[],"due_date":"2026-10-10T17:00:00Z"}).json(); assert created["id"]
    assert client.patch(f"/records/{created['id']}",json={"status":"in_progress"}).json()["status"]=="in_progress"
    ops={route["operationId"] for path in client.get("/openapi.json").json()["paths"].values() for route in path.values() if isinstance(route,dict) and "operationId" in route}
    assert {"list_records","get_record","create_record","update_record"}.issubset(ops)

def test_gateway_collection_trailing_slash_does_not_redirect(monkeypatch):
    monkeypatch.setenv("DOMAIN_PROFILE", "manufacturing-field-ops")
    module = load_module("records_gateway_slash_test", ROOT / "src" / "records-api" / "app.py")
    client = TestClient(module.app, follow_redirects=False)
    assert client.get("/records/").status_code == 200
    response = client.post("/records/", json={
        "title": "Synthetic gateway test", "description": "Collection route without backend redirect",
        "priority": "low", "assigned_to": "Test owner", "location": "Test area",
        "items_required": [], "due_date": "2026-10-20T17:00:00Z",
    })
    assert response.status_code == 201
    assert "location" not in response.headers
    assert "/records/" not in client.get("/openapi.json").json()["paths"]
