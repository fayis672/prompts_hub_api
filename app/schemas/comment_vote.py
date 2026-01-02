from pydantic import BaseModel
from enum import Enum
from datetime import datetime
from uuid import UUID

class VoteType(str, Enum):
    UPVOTE = "upvote"
    DOWNVOTE = "downvote"

class CommentVoteBase(BaseModel):
    vote_type: VoteType

class CommentVoteCreate(CommentVoteBase):
    comment_id: UUID

class CommentVoteResponse(CommentVoteBase):
    id: UUID
    comment_id: UUID
    user_id: UUID
    created_at: datetime

    class Config:
        from_attributes = True
