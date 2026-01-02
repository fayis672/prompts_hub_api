from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from app.schemas.tag import TagCreate, TagUpdate, TagResponse
from app.core.security import get_current_user, get_current_admin
from app.db.supabase import get_supabase

router = APIRouter()

@router.post("/", response_model=TagResponse, status_code=status.HTTP_201_CREATED)
def create_tag(
    tag_in: TagCreate,
    current_user = Depends(get_current_user) # Authenticated users can create tags
):
    """
    Create a new tag. Checks for duplicates.
    """
    supabase = get_supabase()
    
    # Check existence
    existing = supabase.table("tags").select("*").eq("slug", tag_in.slug).execute()
    if existing.data:
        # Instead of error, maybe return existing?
        # For now, let's return existing to avoid duplication errors client side
        return existing.data[0]
        
    response = supabase.table("tags").insert(tag_in.model_dump()).execute()
    
    if not response.data:
        raise HTTPException(status_code=400, detail="Could not create tag")
        
    return response.data[0]

@router.get("/", response_model=List[TagResponse])
def read_tags(
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None
):
    """
    Retrieve tags. Public.
    """
    supabase = get_supabase()
    query = supabase.table("tags").select("*")
    
    if search:
        query = query.ilike("name", f"%{search}%")
        
    query = query.order("usage_count", desc=True).range(skip, skip + limit - 1)
    
    response = query.execute()
    return response.data

@router.put("/{tag_id}", response_model=TagResponse)
def update_tag(
    tag_id: UUID,
    tag_in: TagUpdate,
    current_user = Depends(get_current_admin) # Admin only
):
    """
    Update a tag. Admin only.
    """
    supabase = get_supabase()
    
    update_data = tag_in.model_dump(exclude_unset=True)
    
    response = supabase.table("tags").update(update_data).eq("id", str(tag_id)).execute()
    
    if not response.data:
         raise HTTPException(status_code=400, detail="Could not update tag")
         
    return response.data[0]

@router.delete("/{tag_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_tag(
    tag_id: UUID,
    current_user = Depends(get_current_admin) # Admin only
):
    """
    Delete a tag. Admin only.
    """
    supabase = get_supabase()
    supabase.table("tags").delete().eq("id", str(tag_id)).execute()
    return None
