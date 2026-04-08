from backend.phases.phase3.models import UserPreference
from backend.phases.phase4.models import CandidateRestaurant
from backend.phases.phase5.service import rank_with_llm


def _sample_pref() -> UserPreference:
    return UserPreference(
        location="bangalore",
        budget="medium",
        budget_cost_range={"min": 801, "max": 2000},
        cuisines=["north-indian"],
        min_rating=4.0,
        additional_preferences="family friendly",
        preference_keywords=["family-friendly"],
        top_k=3,
    )


def _sample_candidates() -> list[CandidateRestaurant]:
    return [
        CandidateRestaurant(
            restaurant_id="r1",
            name="Aroma",
            city="bangalore",
            area="indiranagar",
            cuisines=["north-indian"],
            avg_cost_for_two=1200,
            budget_tier="medium",
            rating=4.5,
            tags=["family-friendly"],
            score=0.88,
            score_trace={"rating_score": 0.9, "cuisine_match_score": 1, "budget_fit_score": 1, "preference_match_score": 1},
        ),
        CandidateRestaurant(
            restaurant_id="r2",
            name="Spice Hub",
            city="bangalore",
            area="koramangala",
            cuisines=["north-indian"],
            avg_cost_for_two=1300,
            budget_tier="medium",
            rating=4.2,
            tags=["casual-dining"],
            score=0.76,
            score_trace={
                "rating_score": 0.84,
                "cuisine_match_score": 1,
                "budget_fit_score": 1,
                "preference_match_score": 0,
            },
        ),
    ]


def test_phase5_fallback_when_no_key(monkeypatch) -> None:
    monkeypatch.setattr("backend.phases.phase5.service.settings.llm_api_key", "")
    recommendations, source, warnings = rank_with_llm(_sample_pref(), _sample_candidates(), top_k=2)
    assert source == "rule_based_fallback"
    assert len(recommendations) == 2
    assert len(warnings) == 1


def test_phase5_llm_parse_success(monkeypatch) -> None:
    monkeypatch.setattr("backend.phases.phase5.service.settings.llm_api_key", "dummy-key")

    def fake_call(_: str, timeout_seconds: float = 30.0) -> str:
        return (
            '[{"rank":1,"restaurant_id":"r1","restaurant_name":"Aroma","cuisine":["north-indian"],'
            '"rating":4.5,"estimated_cost":1200,"ai_explanation":"great fit","fit_highlights":["family-friendly"]}]'
        )

    monkeypatch.setattr("backend.phases.phase5.service._call_groq", fake_call)
    recommendations, source, warnings = rank_with_llm(_sample_pref(), _sample_candidates(), top_k=1)
    assert source == "llm"
    assert warnings == []
    assert recommendations[0].restaurant_id == "r1"


def test_phase5_retries_then_fallback(monkeypatch) -> None:
    monkeypatch.setattr("backend.phases.phase5.service.settings.llm_api_key", "dummy-key")

    def bad_call(_: str, timeout_seconds: float = 30.0) -> str:
        return "not-json"

    monkeypatch.setattr("backend.phases.phase5.service._call_groq", bad_call)
    recommendations, source, warnings = rank_with_llm(_sample_pref(), _sample_candidates(), top_k=2)
    assert source == "rule_based_fallback"
    assert len(recommendations) == 2
    assert len(warnings) == 1
