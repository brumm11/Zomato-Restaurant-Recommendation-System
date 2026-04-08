from pydantic import BaseModel, Field, field_validator

from backend.phases.phase4.models import CandidateRestaurant
from backend.phases.phase5.models import RankedRecommendation


class RecommendationRequest(BaseModel):
    location: str = Field(min_length=1)
    budget: str | None = Field(default=None, pattern="^(low|medium|high)$")
    cuisine: str | list[str] | None = None
    min_rating: float | None = Field(default=None, ge=0.0, le=5.0)
    additional_preferences: str | None = None
    top_k: int = Field(default=5, ge=1, le=10)

    @field_validator("location")
    @classmethod
    def _normalize_location(cls, value: str) -> str:
        return value.strip().lower()

    @field_validator("budget")
    @classmethod
    def _normalize_budget(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip().lower()

    @field_validator("additional_preferences")
    @classmethod
    def _normalize_preferences(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip().lower()
        return cleaned if cleaned else None


class UserPreference(BaseModel):
    location: str
    budget: str | None
    budget_cost_range: dict[str, int] | None
    cuisines: list[str]
    min_rating: float | None
    additional_preferences: str | None
    preference_keywords: list[str]
    top_k: int


class RecommendationResponse(BaseModel):
    request_id: str = ""
    applied_preferences: UserPreference | None = None
    user_preferences: UserPreference
    message: str
    candidates: list[CandidateRestaurant] = Field(default_factory=list)
    recommendations: list[RankedRecommendation] = Field(default_factory=list)
    ranking_source: str = "rule_based_fallback"
    latency_ms: int = 0
    warnings: list[str] = Field(default_factory=list)
