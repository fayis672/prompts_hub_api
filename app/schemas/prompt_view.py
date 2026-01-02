from pydantic import BaseModel, Field, IPvAnyAddress
from typing import Optional
from datetime import datetime
from uuid import UUID

class PromptViewBase(BaseModel):
    ip_address: Optional[str] = Field(None, max_length=45)
    user_agent: Optional[str] = None
    referrer: Optional[str] = Field(None, max_length=500)
    country_code: Optional[str] = Field(None, min_length=2, max_length=2)
    city: Optional[str] = Field(None, max_length=100)

class PromptViewCreate(PromptViewBase):
    prompt_id: UUID
    user_id: Optional[UUID] = None

class PromptViewResponse(PromptViewBase):
    id: UUID
    prompt_id: UUID
    user_id: Optional[UUID] = None
    viewed_at: datetime

    class Config:
        from_attributes = True
