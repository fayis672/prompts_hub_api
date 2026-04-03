from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from uuid import UUID

class PromptLikeResponse(BaseModel):
    id: UUID
    prompt_id: UUID
    user_id: UUID
    created_at: datetime
    
    class Config:
        from_attributes = True

class PromptLikeToggleResponse(BaseModel):
    has_liked: bool
    like_count: int
