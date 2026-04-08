from backend.phases.phase3.models import RecommendationRequest
from backend.phases.phase6.service import orchestrate_recommendations


def test_phase6_response_contract_contains_metadata(monkeypatch) -> None:
    # Avoid file/network dependency for this unit test.
    monkeypatch.setattr(
        "backend.phases.phase6.service.select_candidates",
        lambda _: type("R", (), {"candidates": [], "warnings": []})(),
    )
    payload = RecommendationRequest(location="delhi")
    response = orchestrate_recommendations(payload)
    assert response.request_id
    assert response.applied_preferences is not None
    assert response.ranking_source in {"llm", "rule_based_fallback"}
    assert response.latency_ms >= 0


def test_phase6_handles_retrieval_timeout(monkeypatch) -> None:
    class TimeoutFuture:
        def result(self, timeout=None):  # noqa: ANN001
            import concurrent.futures

            raise concurrent.futures.TimeoutError()

    class FakeExecutor:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):  # noqa: ANN001
            return False

        def submit(self, fn, *args, **kwargs):  # noqa: ANN001
            return TimeoutFuture()

    monkeypatch.setattr("backend.phases.phase6.service.concurrent.futures.ThreadPoolExecutor", lambda max_workers=1: FakeExecutor())
    payload = RecommendationRequest(location="delhi")
    response = orchestrate_recommendations(payload)
    assert response.ranking_source == "rule_based_fallback"
    assert any("Retrieval timeout" in w for w in response.warnings)
