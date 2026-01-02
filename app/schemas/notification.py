from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum
from datetime import datetime
from uuid import UUID

class NotificationType(str, Enum):
    NEW_FOLLOWER = "new_follower"
    PROMPT_RATED = "prompt_rated"
    PROMPT_COMMENTED = "prompt_commented"
    PROMPT_FEATURED = "prompt_featured"
    MENTION = "mention"
    SYSTEM = "system"

class NotificationBase(BaseModel):
    type: NotificationType
    title: str = Field(..., max_length=255)
    message: Optional[str] = None
    related_entity_type: Optional[str] = Field(None, max_length=50)
    related_entity_id: Optional[UUID] = None
    action_url: Optional[str] = Field(None, max_length=500)
    is_read: bool = False

class NotificationCreate(NotificationBase):
    user_id: UUID

class NotificationUpdate(BaseModel):
    is_read: Optional[bool] = None
    read_at: Optional[datetime] = None

class NotificationResponse(NotificationBase):
    id: UUID
    user_id: UUID
    read_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True
