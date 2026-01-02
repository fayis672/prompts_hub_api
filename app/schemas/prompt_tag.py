from pydantic import BaseModel
from datetime import datetime
from uuid import UUID

class PromptTagBase(BaseModel):
    prompt_id: UUID
    tag_id: UUID

class PromptTagCreate(PromptTagBase):
    pass

class PromptTagResponse(PromptTagBase):
    id: UUID
    created_at: datetime

    class Config:
        from_attributes = True
