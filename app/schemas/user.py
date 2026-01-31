from pydantic import BaseModel, EmailStr, HttpUrl, Field
from typing import Optional
from enum import Enum
from datetime import datetime
from uuid import UUID

class UserRole(str, Enum):
    GUEST = "guest"
    USER = "user"
    ADMIN = "admin"

class UserBase(BaseModel):
    username: str = Field(..., max_length=50)
    email: EmailStr
    display_name: Optional[str] = Field(None, max_length=100)
    avatar_url: Optional[str] = Field(None, max_length=500)
    bio: Optional[str] = None
    role: UserRole = UserRole.USER
    
    # Profile info
    website_url: Optional[str] = Field(None, max_length=500)
    twitter_handle: Optional[str] = Field(None, max_length=50)
    github_handle: Optional[str] = Field(None, max_length=50)
    linkedin_url: Optional[str] = Field(None, max_length=500)

class UserCreate(UserBase):
    password: str = Field(..., min_length=8, description="Raw password to be hashed")

class UserCreateRequest(BaseModel):
    username: str = Field(..., max_length=50)
    # email is optional here as it will be taken from the auth token, 
    # but client can send it for validation if desired.
    # However, if we strongly trust the token, we ignore body email.
    # Let's keep profile fields generally available.
    display_name: Optional[str] = Field(None, max_length=100)
    avatar_url: Optional[str] = Field(None, max_length=500)
    bio: Optional[str] = None
    
    website_url: Optional[str] = Field(None, max_length=500)
    twitter_handle: Optional[str] = Field(None, max_length=50)
    github_handle: Optional[str] = Field(None, max_length=50)
    linkedin_url: Optional[str] = Field(None, max_length=500)

class UserExistsResponse(BaseModel):
    exists: bool
    conflict_field: Optional[str] = None

class UserUpdate(BaseModel):
    display_name: Optional[str] = Field(None, max_length=100)
    avatar_url: Optional[str] = Field(None, max_length=500)
    bio: Optional[str] = None
    
    website_url: Optional[str] = None
    twitter_handle: Optional[str] = None
    github_handle: Optional[str] = None
    linkedin_url: Optional[str] = None

class UserResponse(UserBase):
    id: UUID
    is_verified: bool
    is_active: bool
    
    total_prompts: int
    total_followers: int
    total_following: int
    total_views_received: int
    
    created_at: datetime
    updated_at: datetime
    last_login_at: Optional[datetime] = None
    email_verified_at: Optional[datetime] = None

    class Config:
        from_attributes = True
