from pydantic import BaseModel, Field


class CandidateRestaurant(BaseModel):
    restaurant_id: str
    name: str
    city: str
    area: str | None = None
    cuisines: list[str] = Field(default_factory=list)
    avg_cost_for_two: float | None = None
    budget_tier: str | None = None
    rating: float | None = None
    tags: list[str] = Field(default_factory=list)
    score: float
    score_trace: dict[str, float]


class CandidateSelectionResult(BaseModel):
    candidates: list[CandidateRestaurant]
    ranking_source: str
    warnings: list[str] = Field(default_factory=list)
