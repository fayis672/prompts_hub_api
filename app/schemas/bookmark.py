from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from uuid import UUID

class BookmarkBase(BaseModel):
    notes: Optional[str] = None
    collection_id: Optional[UUID] = None

class BookmarkCreate(BookmarkBase):
    prompt_id: UUID

class BookmarkUpdate(BaseModel):
    notes: Optional[str] = None
    collection_id: Optional[UUID] = None

class BookmarkResponse(BookmarkBase):
    id: UUID
    user_id: UUID
    prompt_id: UUID
    created_at: datetime

    class Config:
        from_attributes = True
