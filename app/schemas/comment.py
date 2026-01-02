from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from uuid import UUID

class CommentBase(BaseModel):
    content: str = Field(..., min_length=1)
    parent_comment_id: Optional[UUID] = None

class CommentCreate(CommentBase):
    prompt_id: UUID

class CommentUpdate(BaseModel):
    content: Optional[str] = Field(None, min_length=1)
    is_approved: Optional[bool] = None

class CommentResponse(CommentBase):
    id: UUID
    prompt_id: UUID
    user_id: UUID
    is_approved: bool
    is_edited: bool
    upvote_count: int
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None

    class Config:
        from_attributes = True
