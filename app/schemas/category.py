from pydantic import BaseModel, Field, HttpUrl
from typing import Optional
from datetime import datetime
from uuid import UUID

class CategoryBase(BaseModel):
    name: str = Field(..., max_length=100)
    slug: str = Field(..., max_length=100)
    description: Optional[str] = None
    icon_url: Optional[str] = Field(None, max_length=500)
    color_code: Optional[str] = Field(None, max_length=7, pattern="^#[0-9a-fA-F]{6}$")
    display_order: int = 0
    is_active: bool = True

class CategoryCreate(CategoryBase):
    pass

class CategoryUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=100)
    slug: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    icon_url: Optional[str] = Field(None, max_length=500)
    color_code: Optional[str] = Field(None, max_length=7)
    display_order: Optional[int] = None
    is_active: Optional[bool] = None

class CategoryResponse(CategoryBase):
    id: UUID
    prompt_count: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
