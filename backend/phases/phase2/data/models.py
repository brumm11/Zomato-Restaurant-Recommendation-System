from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class NormalizedRestaurant(BaseModel):
    restaurant_id: str
    name: str
    city: str
    area: str | None = None
    cuisines: list[str] = Field(default_factory=list)
    avg_cost_for_two: float | None = None
    budget_tier: Literal["low", "medium", "high"] | None = None
    rating: float | None = None
    votes: int | None = None
    tags: list[str] = Field(default_factory=list)
    source_last_updated: datetime


class DataQualityReport(BaseModel):
    source: str
    rows_seen: int
    rows_written: int
    dropped_missing_name_or_city: int
    duplicate_rows_removed: int
    null_rating_count: int
