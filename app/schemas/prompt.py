from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum
from datetime import datetime
from uuid import UUID
from app.schemas.prompt_variable import PromptVariableCreateRequest
from app.schemas.prompt_output import PromptOutputCreateRequest

class PromptType(str, Enum):
    TEXT_GENERATION = "text_generation"
    IMAGE_GENERATION = "image_generation"
    VIDEO_GENERATION = "video_generation"
    CODE_GENERATION = "code_generation"
    AUDIO_GENERATION = "audio_generation"
    OTHER = "other"

class PrivacyStatus(str, Enum):
    PUBLIC = "public"
    PRIVATE = "private"
    UNLISTED = "unlisted"

class PromptStatus(str, Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"

class PromptBase(BaseModel):
    title: str = Field(..., max_length=255)
    description: Optional[str] = None
    prompt_text: str
    
    prompt_type: PromptType
    category_id: UUID
    
    privacy_status: PrivacyStatus = PrivacyStatus.PUBLIC
    status: PromptStatus = PromptStatus.DRAFT
    
    slug: Optional[str] = Field(None, max_length=300)
    meta_description: Optional[str] = None

class PromptCreate(PromptBase):
    variables: Optional[List[PromptVariableCreateRequest]] = None
    tags: Optional[List[str]] = None
    prompt_outputs: Optional[List[PromptOutputCreateRequest]] = None

class PromptUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    prompt_text: Optional[str] = None
    
    prompt_type: Optional[PromptType] = None
    category_id: Optional[UUID] = None
    
    privacy_status: Optional[PrivacyStatus] = None
    status: Optional[PromptStatus] = None
    
    is_featured: Optional[bool] = None
    
    slug: Optional[str] = Field(None, max_length=300)
    meta_description: Optional[str] = None

class PromptResponse(PromptBase):
    id: UUID
    user_id: UUID
    
    is_featured: bool
    featured_at: Optional[datetime] = None
    
    view_count: int
    bookmark_count: int
    rating_count: int
    rating_sum: int
    average_rating: float
    fork_count: int
    comment_count: int
    
    version: int
    parent_prompt_id: Optional[UUID] = None
    forked_from_id: Optional[UUID] = None
    
    published_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None

    class Config:
        from_attributes = True
