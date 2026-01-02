from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from app.schemas.user import UserCreate, UserUpdate, UserResponse, UserRole
from app.core.security import get_current_user, get_current_admin
from app.db.supabase import get_supabase

router = APIRouter()

@router.get("/me", response_model=UserResponse)
def read_user_me(
    current_user = Depends(get_current_user)
):
    """
    Get current user profile.
    """
    return current_user

@router.put("/me", response_model=UserResponse)
def update_user_me(
    user_in: UserUpdate,
    current_user = Depends(get_current_user)
):
    """
    Update current user profile.
    """
    supabase = get_supabase()
    user_id = current_user["id"]
    
    update_data = user_in.model_dump(exclude_unset=True)
    
    if not update_data:
        return current_user
        
    response = supabase.table("users").update(update_data).eq("id", user_id).execute()
    
    if not response.data:
        raise HTTPException(status_code=400, detail="Could not update profile")
        
    return response.data[0]

@router.get("/", response_model=List[UserResponse])
def read_users(
    skip: int = 0,
    limit: int = 100,
    current_user = Depends(get_current_admin) # Admin only
):
    """
    Retrieve users. Admin only.
    """
    supabase = get_supabase()
    query = supabase.table("users").select("*").range(skip, skip + limit - 1)
    response = query.execute()
    return response.data

@router.get("/{user_id}", response_model=UserResponse)
def read_user_by_id(
    user_id: UUID,
    current_user = Depends(get_current_user) # Any auth user can view public profiles?
):
    """
    Get a specific user by ID.
    """
    supabase = get_supabase()
    response = supabase.table("users").select("*").eq("id", str(user_id)).execute()
    
    if not response.data:
        raise HTTPException(status_code=404, detail="User not found")
        
    user = response.data[0]
    # Check basic privacy/existence if user is deleted etc?
    return user

@router.put("/{user_id}", response_model=UserResponse)
def update_user_by_id(
    user_id: UUID,
    user_in: UserUpdate, # Note: Normal update schema. Role update might need separate schema or param.
    role: Optional[UserRole] = None, # Allow admin to update role via query param or switch to a specific schema
    current_user = Depends(get_current_admin) # Admin only
):
    """
    Update a user. Admin only. Can update role.
    """
    supabase = get_supabase()
    
    # Check if user exists
    existing = supabase.table("users").select("*").eq("id", str(user_id)).execute()
    if not existing.data:
        raise HTTPException(status_code=404, detail="User not found")
    
    update_data = user_in.model_dump(exclude_unset=True)
    
    if role:
        update_data["role"] = role
        
    if not update_data:
        return existing.data[0]
        
    response = supabase.table("users").update(update_data).eq("id", str(user_id)).execute()
    
    if not response.data:
         raise HTTPException(status_code=400, detail="Could not update user")
         
    return response.data[0]
