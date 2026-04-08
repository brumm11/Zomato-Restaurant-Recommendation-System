from __future__ import annotations

import difflib
import re

import httpx

from backend.phases.phase1.core.config import settings
from backend.phases.phase1.core.logging import get_logger
from backend.phases.phase3.models import RecommendationRequest, UserPreference

logger = get_logger(__name__)

CITY_ALIASES = {
    "bengaluru": "bangalore",
    "new delhi": "delhi",
    "bombay": "mumbai",
}

SUPPORTED_CITIES = {
    "bangalore",
    "delhi",
    "mumbai",
    "hyderabad",
    "chennai",
    "pune",
    "kolkata",
}

BUDGET_COST_RANGES = {
    "low": {"min": 0, "max": 800},
    "medium": {"min": 801, "max": 2000},
    "high": {"min": 2001, "max": 10000},
}


def build_user_preference(payload: RecommendationRequest) -> UserPreference:
    location = _normalize_city(payload.location)
    cuisines = _normalize_cuisines(payload.cuisine)
    keywords = _extract_keywords(payload.additional_preferences)

    if payload.additional_preferences and settings.llm_api_key:
        llm_keywords = _extract_keywords_with_groq(payload.additional_preferences)
        if llm_keywords:
            keywords = _merge_unique(keywords, llm_keywords)

    return UserPreference(
        location=location,
        budget=payload.budget,
        budget_cost_range=BUDGET_COST_RANGES.get(payload.budget) if payload.budget else None,
        cuisines=cuisines,
        min_rating=payload.min_rating,
        additional_preferences=payload.additional_preferences,
        preference_keywords=keywords,
        top_k=payload.top_k,
    )


def validate_location_or_suggestions(location: str) -> tuple[bool, list[str]]:
    if location in SUPPORTED_CITIES:
        return True, []
    suggestions = difflib.get_close_matches(location, sorted(SUPPORTED_CITIES), n=3, cutoff=0.4)
    return False, suggestions


def _normalize_city(value: str) -> str:
    lowered = value.strip().lower()
    return CITY_ALIASES.get(lowered, lowered)


def _normalize_cuisines(value: str | list[str] | None) -> list[str]:
    if value is None:
        return []
    raw_parts = value if isinstance(value, list) else value.split(",")
    cleaned = []
    for item in raw_parts:
        token = str(item).strip().lower()
        if not token:
            continue
        cleaned.append(token.replace(" ", "-"))
    return _merge_unique([], cleaned)


def _extract_keywords(text: str | None) -> list[str]:
    if not text:
        return []
    parts = re.findall(r"[a-zA-Z][a-zA-Z\- ]{1,}", text.lower())
    normalized = [p.strip().replace(" ", "-") for p in parts if p.strip()]
    stopwords = {"and", "or", "with", "for", "the", "a", "an", "to"}
    filtered = [w for w in normalized if w not in stopwords and len(w) > 2]
    return _merge_unique([], filtered)[:8]


def _extract_keywords_with_groq(text: str) -> list[str]:
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.llm_api_key}",
        "Content-Type": "application/json",
        "User-Agent": "restaurant-recommendation-service/1.0",
    }
    payload = {
        "model": settings.llm_model,
        "temperature": 0,
        "max_tokens": 80,
        "messages": [
            {
                "role": "system",
                "content": "Extract 3 to 8 short preference keywords from user text. Return CSV only.",
            },
            {"role": "user", "content": text},
        ],
    }
    try:
        with httpx.Client(timeout=15.0, headers=headers) as client:
            resp = client.post(url, json=payload)
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"]
    except Exception:
        logger.exception("Groq keyword extraction failed, fallback to local parser")
        return []
    return _normalize_cuisines(content)


def _merge_unique(base: list[str], extra: list[str]) -> list[str]:
    seen = set(base)
    result = list(base)
    for item in extra:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result
