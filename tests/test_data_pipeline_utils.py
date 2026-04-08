from backend.phases.phase2.data.pipeline import (
    _clamp_rating,
    _derive_budget_tier,
    _normalize_cuisines,
)


def test_clamp_rating_bounds() -> None:
    assert _clamp_rating(-3) == 0.0
    assert _clamp_rating(6.2) == 5.0
    assert _clamp_rating(4.26) == 4.3


def test_budget_tier_derivation() -> None:
    assert _derive_budget_tier(500) == "low"
    assert _derive_budget_tier(1500) == "medium"
    assert _derive_budget_tier(2500) == "high"


def test_normalize_cuisines() -> None:
    output = _normalize_cuisines("North Indian, Chinese, North Indian")
    assert output == ["north-indian", "chinese"]
