from fastapi.testclient import TestClient

from backend.phases.phase1.api.app import app


client = TestClient(app)


def test_root_serves_frontend_html() -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")
    assert "AI Restaurant Recommendations" in response.text
