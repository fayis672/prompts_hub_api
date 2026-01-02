from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from uuid import UUID

class CollectionBase(BaseModel):
    name: str = Field(..., max_length=100)
    description: Optional[str] = None
    slug: Optional[str] = Field(None, max_length=150)
    is_public: bool = False

class CollectionCreate(CollectionBase):
    pass

class CollectionUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    slug: Optional[str] = Field(None, max_length=150)
    is_public: Optional[bool] = None

class CollectionResponse(CollectionBase):
    id: UUID
    user_id: UUID
    prompt_count: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
