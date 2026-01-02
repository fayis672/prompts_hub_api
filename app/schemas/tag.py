from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from uuid import UUID

class TagBase(BaseModel):
    name: str = Field(..., max_length=50)
    slug: str = Field(..., max_length=50)
    usage_count: int = 0

class TagCreate(TagBase):
    pass

class TagUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=50)
    slug: Optional[str] = Field(None, max_length=50)
    usage_count: Optional[int] = None

class TagResponse(TagBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
