from __future__ import annotations

import json

import httpx

from backend.phases.phase1.core.config import settings
from backend.phases.phase1.core.logging import get_logger
from backend.phases.phase3.models import UserPreference
from backend.phases.phase4.models import CandidateRestaurant
from backend.phases.phase5.models import RankedRecommendation

logger = get_logger(__name__)


def rank_with_llm(
    user_preference: UserPreference,
    candidates: list[CandidateRestaurant],
    top_k: int,
    llm_timeout_seconds: float = 30.0,
) -> tuple[list[RankedRecommendation], str, list[str]]:
    if not candidates:
        return [], "rule_based_fallback", ["No candidates available for LLM ranking."]

    if not settings.llm_api_key:
        return fallback_rank(candidates, top_k), "rule_based_fallback", ["GROQ_API_KEY not configured."]

    prompt = _build_prompt(user_preference, candidates, top_k)
    try:
        content = _call_groq(prompt, timeout_seconds=llm_timeout_seconds)
        ranked = _parse_llm_output(content, candidates, top_k)
        return ranked, "llm", []
    except Exception as exc:
        logger.exception("Phase 5 LLM ranking failed on first attempt: %s", str(exc))

    # Retry once with stronger correction instruction.
    try:
        retry_prompt = prompt + "\nReturn ONLY strict JSON array as specified. No markdown."
        content = _call_groq(retry_prompt, timeout_seconds=llm_timeout_seconds)
        ranked = _parse_llm_output(content, candidates, top_k)
        return ranked, "llm", ["Recovered after one LLM output-format retry."]
    except Exception as exc:
        logger.exception("Phase 5 LLM ranking retry failed: %s", str(exc))
        return fallback_rank(candidates, top_k), "rule_based_fallback", ["LLM ranking failed, fallback applied."]


def _build_prompt(user_preference: UserPreference, candidates: list[CandidateRestaurant], top_k: int) -> str:
    candidate_lines = []
    for c in candidates:
        candidate_lines.append(
            {
                "restaurant_id": c.restaurant_id,
                "name": c.name,
                "cuisines": c.cuisines,
                "rating": c.rating,
                "avg_cost_for_two": c.avg_cost_for_two,
                "tags": c.tags,
                "phase4_score": c.score,
            }
        )
    return (
        "You are a restaurant recommendation assistant.\n"
        "Use only provided candidates. Do not invent restaurants.\n"
        "Rank the best matches and explain why for the user preferences.\n"
        "Output must be JSON array with objects containing keys:\n"
        "rank, restaurant_id, restaurant_name, cuisine, rating, estimated_cost, ai_explanation, fit_highlights.\n"
        f"Return at most {top_k} items.\n\n"
        f"User preferences:\n{json.dumps(user_preference.model_dump(), ensure_ascii=True)}\n\n"
        f"Candidates:\n{json.dumps(candidate_lines, ensure_ascii=True)}"
    )


def _call_groq(prompt: str, timeout_seconds: float = 30.0) -> str:
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.llm_api_key}",
        "Content-Type": "application/json",
        "User-Agent": "restaurant-recommendation-service/1.0",
    }
    payload = {
        "model": settings.llm_model,
        "temperature": 0.1,
        "max_tokens": 1000,
        "messages": [
            {"role": "system", "content": "Return strict JSON only."},
            {"role": "user", "content": prompt},
        ],
    }
    with httpx.Client(timeout=timeout_seconds, headers=headers) as client:
        response = client.post(url, json=payload)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]


def _parse_llm_output(content: str, candidates: list[CandidateRestaurant], top_k: int) -> list[RankedRecommendation]:
    parsed = json.loads(content)
    if not isinstance(parsed, list):
        raise ValueError("LLM output is not a list.")

    allowed_ids = {c.restaurant_id for c in candidates}
    items: list[RankedRecommendation] = []
    for idx, raw in enumerate(parsed[:top_k], start=1):
        restaurant_id = str(raw.get("restaurant_id", "")).strip()
        if restaurant_id not in allowed_ids:
            raise ValueError("LLM returned restaurant outside candidate list.")
        items.append(
            RankedRecommendation(
                rank=int(raw.get("rank", idx)),
                restaurant_id=restaurant_id,
                restaurant_name=str(raw.get("restaurant_name", "")).strip(),
                cuisine=list(raw.get("cuisine", [])) if isinstance(raw.get("cuisine", []), list) else [],
                rating=_as_float(raw.get("rating")),
                estimated_cost=_as_float(raw.get("estimated_cost")),
                ai_explanation=str(raw.get("ai_explanation", "")).strip(),
                fit_highlights=list(raw.get("fit_highlights", [])),
            )
        )
    if not items:
        raise ValueError("LLM output list empty.")
    return items


def fallback_rank(candidates: list[CandidateRestaurant], top_k: int) -> list[RankedRecommendation]:
    ranked: list[RankedRecommendation] = []
    for i, c in enumerate(candidates[:top_k], start=1):
        ranked.append(
            RankedRecommendation(
                rank=i,
                restaurant_id=c.restaurant_id,
                restaurant_name=c.name,
                cuisine=c.cuisines,
                rating=c.rating,
                estimated_cost=c.avg_cost_for_two,
                ai_explanation="Selected by deterministic Phase 4 scoring fallback.",
                fit_highlights=["high-phase4-score"],
            )
        )
    return ranked


def _as_float(value: object) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
