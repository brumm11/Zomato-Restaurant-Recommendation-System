from fastapi.testclient import TestClient

from backend.phases.phase1.api.app import app

client = TestClient(app)


def test_recommendations_valid_payload_is_canonicalized() -> None:
    response = client.post(
        "/recommendations",
        json={
            "location": "Bengaluru",
            "budget": "medium",
            "cuisine": "North Indian, Chinese",
            "min_rating": 4.1,
            "additional_preferences": "Family friendly and quick service",
            "top_k": 5,
        },
    )
    assert response.status_code == 200
    payload = response.json()["user_preferences"]
    assert payload["location"] == "bangalore"
    assert payload["budget_cost_range"] == {"min": 801, "max": 2000}
    assert payload["cuisines"] == ["north-indian", "chinese"]
    assert "family" in payload["preference_keywords"]
    assert "quick" in payload["preference_keywords"]
    assert "candidates" in response.json()
    assert "recommendations" in response.json()
    assert "ranking_source" in response.json()
    assert "warnings" in response.json()
    assert "request_id" in response.json()
    assert "applied_preferences" in response.json()
    assert "latency_ms" in response.json()


def test_recommendations_rejects_invalid_min_rating() -> None:
    response = client.post(
        "/recommendations",
        json={"location": "Delhi", "min_rating": 6.5},
    )
    assert response.status_code == 422


def test_recommendations_returns_404_for_unknown_location() -> None:
    response = client.post(
        "/recommendations",
        json={"location": "Mars City"},
    )
    assert response.status_code == 404
    detail = response.json()["detail"]
    assert detail["code"] == "LOCATION_NOT_FOUND"
    assert "suggestions" in detail


def test_recommendations_returns_phase4_warning_without_dataset(monkeypatch) -> None:
    monkeypatch.setattr(
        "backend.phases.phase4.service.settings.normalized_data_path",
        "artifacts/data/does_not_exist.jsonl",
    )
    response = client.post("/recommendations", json={"location": "Delhi"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["candidates"] == []
    assert payload["recommendations"] == []
    assert len(payload["warnings"]) >= 1
