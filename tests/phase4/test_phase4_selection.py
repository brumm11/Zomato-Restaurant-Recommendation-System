import json

from backend.phases.phase3.models import UserPreference
from backend.phases.phase4.service import select_candidates


def test_phase4_select_candidates_filters_and_scores(tmp_path, monkeypatch) -> None:
    data_file = tmp_path / "restaurants_normalized.jsonl"
    rows = [
        {
            "restaurant_id": "r1",
            "name": "Aroma",
            "city": "bangalore",
            "area": "indiranagar",
            "cuisines": ["north-indian", "chinese"],
            "avg_cost_for_two": 1200,
            "budget_tier": "medium",
            "rating": 4.6,
            "tags": ["family-friendly", "quick-service"],
        },
        {
            "restaurant_id": "r2",
            "name": "Spice Hub",
            "city": "bangalore",
            "area": "koramangala",
            "cuisines": ["north-indian"],
            "avg_cost_for_two": 1300,
            "budget_tier": "medium",
            "rating": 4.2,
            "tags": ["casual-dining"],
        },
        {
            "restaurant_id": "r3",
            "name": "Sea View",
            "city": "mumbai",
            "area": "bandra",
            "cuisines": ["seafood"],
            "avg_cost_for_two": 2500,
            "budget_tier": "high",
            "rating": 4.8,
            "tags": ["fine-dining"],
        },
    ]
    data_file.write_text("\n".join(json.dumps(r) for r in rows), encoding="utf-8")
    monkeypatch.setattr("backend.phases.phase4.service.settings.normalized_data_path", str(data_file))

    pref = UserPreference(
        location="bangalore",
        budget="medium",
        budget_cost_range={"min": 801, "max": 2000},
        cuisines=["north-indian"],
        min_rating=4.0,
        additional_preferences="family friendly",
        preference_keywords=["family-friendly"],
        top_k=5,
    )
    result = select_candidates(pref)
    assert result.warnings == []
    assert len(result.candidates) == 2
    assert result.candidates[0].name == "Aroma"
    assert result.candidates[0].score >= result.candidates[1].score


def test_phase4_returns_warning_when_dataset_missing(monkeypatch) -> None:
    monkeypatch.setattr(
        "backend.phases.phase4.service.settings.normalized_data_path",
        "artifacts/data/does_not_exist.jsonl",
    )
    pref = UserPreference(
        location="bangalore",
        budget=None,
        budget_cost_range=None,
        cuisines=[],
        min_rating=None,
        additional_preferences=None,
        preference_keywords=[],
        top_k=5,
    )
    result = select_candidates(pref)
    assert result.candidates == []
    assert result.ranking_source == "rule_based_fallback"
    assert len(result.warnings) == 1
