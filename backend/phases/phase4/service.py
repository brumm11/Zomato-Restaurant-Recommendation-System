from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from backend.phases.phase1.core.config import settings
from backend.phases.phase1.core.logging import get_logger
from backend.phases.phase3.models import UserPreference
from backend.phases.phase4.models import CandidateRestaurant, CandidateSelectionResult

logger = get_logger(__name__)


def select_candidates(user_pref: UserPreference, candidate_pool_size: int = 30) -> CandidateSelectionResult:
    rows = _load_normalized_rows(settings.normalized_data_path)
    if not rows:
        return CandidateSelectionResult(
            candidates=[],
            ranking_source="rule_based_fallback",
            warnings=["No normalized dataset available. Run Phase 2 ingestion first."],
        )

    filtered = [r for r in rows if str(r.get("city", "")).lower() == user_pref.location]

    if user_pref.budget:
        filtered = [r for r in filtered if str(r.get("budget_tier", "")).lower() == user_pref.budget]

    if user_pref.cuisines:
        requested = set(user_pref.cuisines)
        filtered = [r for r in filtered if requested.intersection(set(r.get("cuisines", [])))]

    if user_pref.min_rating is not None:
        filtered = [r for r in filtered if (r.get("rating") or 0) >= user_pref.min_rating]

    scored = [_to_candidate(row, user_pref) for row in filtered]
    scored.sort(key=lambda c: c.score, reverse=True)
    return CandidateSelectionResult(
        candidates=scored[:candidate_pool_size],
        ranking_source="rule_based_fallback",
        warnings=[],
    )


def _to_candidate(row: dict[str, Any], user_pref: UserPreference) -> CandidateRestaurant:
    rating = _as_float(row.get("rating"))
    rating_score = (rating / 5.0) if rating is not None else 0.0

    cuisine_score = _cuisine_match_score(user_pref.cuisines, row.get("cuisines", []))
    budget_score = _budget_fit_score(user_pref.budget, row.get("budget_tier"))
    preference_score = _preference_match_score(user_pref.preference_keywords, row.get("tags", []))

    score = (0.40 * rating_score) + (0.25 * cuisine_score) + (0.20 * budget_score) + (0.15 * preference_score)

    return CandidateRestaurant(
        restaurant_id=str(row.get("restaurant_id", "")),
        name=str(row.get("name", "")),
        city=str(row.get("city", "")),
        area=row.get("area"),
        cuisines=list(row.get("cuisines", [])),
        avg_cost_for_two=_as_float(row.get("avg_cost_for_two")),
        budget_tier=row.get("budget_tier"),
        rating=rating,
        tags=list(row.get("tags", [])),
        score=round(score, 4),
        score_trace={
            "rating_score": round(rating_score, 4),
            "cuisine_match_score": round(cuisine_score, 4),
            "budget_fit_score": round(budget_score, 4),
            "preference_match_score": round(preference_score, 4),
        },
    )


def _load_normalized_rows(path: str) -> list[dict[str, Any]]:
    file_path = Path(path)
    if not file_path.exists():
        logger.warning("Normalized data file not found at path=%s", path)
        return []
    rows = []
    with file_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def _cuisine_match_score(requested: list[str], available: list[str]) -> float:
    if not requested:
        return 1.0
    available_set = set((available or []))
    if not available_set:
        return 0.0
    overlap = set(requested).intersection(available_set)
    return len(overlap) / len(set(requested))


def _budget_fit_score(requested_budget: str | None, candidate_budget: str | None) -> float:
    if requested_budget is None:
        return 1.0
    if not candidate_budget:
        return 0.0
    order = {"low": 0, "medium": 1, "high": 2}
    if requested_budget == candidate_budget:
        return 1.0
    distance = abs(order.get(requested_budget, 10) - order.get(candidate_budget, 10))
    if distance == 1:
        return 0.5
    return 0.0


def _preference_match_score(requested_keywords: list[str], candidate_tags: list[str]) -> float:
    if not requested_keywords:
        return 1.0
    candidate_set = set(candidate_tags or [])
    if not candidate_set:
        return 0.0
    overlap = set(requested_keywords).intersection(candidate_set)
    return len(overlap) / len(set(requested_keywords))


def _as_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
