from pydantic import BaseModel, Field, HttpUrl
from typing import Optional, Dict, Any
from enum import Enum
from datetime import datetime
from uuid import UUID

class OutputType(str, Enum):
    TEXT = "text"
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    CODE = "code"

class PromptOutputBase(BaseModel):
    title: Optional[str] = Field(None, max_length=255)
    output_text: Optional[str] = None
    output_url: Optional[str] = Field(None, max_length=500)
    output_type: OutputType
    variable_values: Optional[Dict[str, Any]] = None
    display_order: int = 0
    is_approved: bool = True

class PromptOutputCreate(PromptOutputBase):
    prompt_id: UUID

class PromptOutputCreateRequest(PromptOutputBase):
    pass

class PromptOutputUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=255)
    output_text: Optional[str] = None
    output_url: Optional[str] = Field(None, max_length=500)
    output_type: Optional[OutputType] = None
    variable_values: Optional[Dict[str, Any]] = None
    display_order: Optional[int] = None
    is_approved: Optional[bool] = None

class PromptOutputResponse(PromptOutputBase):
    id: UUID
    prompt_id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
