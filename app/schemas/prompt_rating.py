from pydantic import BaseModel, Field
from datetime import datetime
from uuid import UUID

class PromptRatingBase(BaseModel):
    rating: int = Field(..., ge=1, le=5)

class PromptRatingCreate(PromptRatingBase):
    prompt_id: UUID

class PromptRatingUpdate(BaseModel):
    rating: int = Field(..., ge=1, le=5)

class PromptRatingResponse(PromptRatingBase):
    id: UUID
    prompt_id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
