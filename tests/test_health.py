from fastapi.testclient import TestClient

from backend.phases.phase1.api.app import app


client = TestClient(app)


def test_health_endpoint_returns_ok() -> None:
    response = client.get("/health")
    assert response.status_code == 200

    payload = response.json()
    assert payload["status"] == "ok"
    assert "service" in payload
    assert "environment" in payload
