from pydantic import BaseModel, Field


class RankedRecommendation(BaseModel):
    rank: int
    restaurant_id: str
    restaurant_name: str
    cuisine: list[str] = Field(default_factory=list)
    rating: float | None = None
    estimated_cost: float | None = None
    ai_explanation: str
    fit_highlights: list[str] = Field(default_factory=list)
