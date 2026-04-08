from __future__ import annotations

import concurrent.futures
import time
import uuid

from backend.phases.phase1.core.logging import get_logger
from backend.phases.phase3.models import RecommendationRequest, RecommendationResponse
from backend.phases.phase3.service import build_user_preference, validate_location_or_suggestions
from backend.phases.phase4.service import select_candidates
from backend.phases.phase5.service import fallback_rank, rank_with_llm

logger = get_logger(__name__)


def orchestrate_recommendations(payload: RecommendationRequest) -> RecommendationResponse:
    started = time.perf_counter()
    request_id = str(uuid.uuid4())
    warnings: list[str] = []

    user_preference = build_user_preference(payload)
    valid, suggestions = validate_location_or_suggestions(user_preference.location)
    if not valid:
        from fastapi import HTTPException

        raise HTTPException(
            status_code=404,
            detail={
                "code": "LOCATION_NOT_FOUND",
                "message": f"No matching location found for '{user_preference.location}'.",
                "suggestions": suggestions,
            },
        )

    selected_candidates = []
    # Retrieval timeout boundary
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
        fut = ex.submit(select_candidates, user_preference)
        try:
            phase4_result = fut.result(timeout=5.0)
            selected_candidates = phase4_result.candidates[: max(15, min(30, payload.top_k * 3))]
            warnings.extend(phase4_result.warnings)
        except concurrent.futures.TimeoutError:
            warnings.append("Retrieval timeout reached; continuing with empty candidate set.")
            logger.warning("request_id=%s retrieval timeout", request_id)

    # LLM timeout boundary + fallback
    recommendations = []
    ranking_source = "rule_based_fallback"
    if selected_candidates:
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
            fut = ex.submit(rank_with_llm, user_preference, selected_candidates, payload.top_k, 20.0)
            try:
                recommendations, ranking_source, llm_warnings = fut.result(timeout=25.0)
                warnings.extend(llm_warnings)
            except concurrent.futures.TimeoutError:
                warnings.append("LLM timeout reached; deterministic fallback applied.")
                recommendations = fallback_rank(selected_candidates, payload.top_k)
                ranking_source = "rule_based_fallback"
                logger.warning("request_id=%s llm timeout", request_id)
    else:
        warnings.append("No candidates available for LLM ranking.")

    latency_ms = int((time.perf_counter() - started) * 1000)
    return RecommendationResponse(
        request_id=request_id,
        applied_preferences=user_preference,
        user_preferences=user_preference,
        message="Orchestration complete: validated input, selected candidates, ranked recommendations.",
        candidates=selected_candidates,
        recommendations=recommendations,
        ranking_source=ranking_source,
        latency_ms=latency_ms,
        warnings=warnings,
    )
