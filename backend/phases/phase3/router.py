from fastapi import APIRouter

from backend.phases.phase3.models import RecommendationRequest, RecommendationResponse
from backend.phases.phase6.service import orchestrate_recommendations

router = APIRouter(tags=["recommendations"])


@router.post("/recommendations", response_model=RecommendationResponse)
def create_recommendation_request(payload: RecommendationRequest) -> RecommendationResponse:
    return orchestrate_recommendations(payload)
