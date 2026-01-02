from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from uuid import UUID

class TrendingPromptBase(BaseModel):
    trending_score: float
    views_last_24h: int = 0
    ratings_last_24h: int = 0
    bookmarks_last_24h: int = 0
    rank: int
    expires_at: datetime

class TrendingPromptCreate(TrendingPromptBase):
    prompt_id: UUID

class TrendingPromptResponse(TrendingPromptBase):
    id: UUID
    prompt_id: UUID
    calculated_at: datetime

    class Config:
        from_attributes = True
