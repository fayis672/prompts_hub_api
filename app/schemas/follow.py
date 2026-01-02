from pydantic import BaseModel
from datetime import datetime
from uuid import UUID

class FollowBase(BaseModel):
    following_id: UUID

class FollowCreate(FollowBase):
    pass

class FollowResponse(FollowBase):
    id: UUID
    follower_id: UUID
    created_at: datetime

    class Config:
        from_attributes = True
