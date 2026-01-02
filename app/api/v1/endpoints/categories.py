from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from app.schemas.category import CategoryCreate, CategoryUpdate, CategoryResponse
from app.core.security import get_current_admin, get_current_user
from app.db.supabase import get_supabase

router = APIRouter()

@router.post("/", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
def create_category(
    category_in: CategoryCreate,
    current_user = Depends(get_current_admin) # Admin only
):
    """
    Create a new category. Admin only.
    """
    supabase = get_supabase()
    
    # Check if slug exists
    existing = supabase.table("categories").select("id").eq("slug", category_in.slug).execute()
    if existing.data:
        raise HTTPException(status_code=400, detail="Category with this slug already exists")
        
    response = supabase.table("categories").insert(category_in.model_dump()).execute()
    
    if not response.data:
        raise HTTPException(status_code=400, detail="Could not create category")
        
    return response.data[0]

@router.get("/", response_model=List[CategoryResponse])
def read_categories(
    skip: int = 0,
    limit: int = 100,
    is_active: bool = True
):
    """
    Retrieve categories. Public.
    """
    supabase = get_supabase()
    query = supabase.table("categories").select("*")
    
    if is_active:
        query = query.eq("is_active", "true")
        
    query = query.order("display_order", desc=False).range(skip, skip + limit - 1)
    
    response = query.execute()
    return response.data

@router.get("/{category_id}", response_model=CategoryResponse)
def read_category(category_id: UUID):
    """
    Get category by ID. Public.
    """
    supabase = get_supabase()
    response = supabase.table("categories").select("*").eq("id", str(category_id)).execute()
    
    if not response.data:
        raise HTTPException(status_code=404, detail="Category not found")
        
    return response.data[0]

@router.put("/{category_id}", response_model=CategoryResponse)
def update_category(
    category_id: UUID,
    category_in: CategoryUpdate,
    current_user = Depends(get_current_admin) # Admin only
):
    """
    Update a category. Admin only.
    """
    supabase = get_supabase()
    
    update_data = category_in.model_dump(exclude_unset=True)
    
    if not update_data:
        # Fetch existing to return
        existing = supabase.table("categories").select("*").eq("id", str(category_id)).execute()
        if not existing.data:
             raise HTTPException(status_code=404, detail="Category not found")
        return existing.data[0]
        
    response = supabase.table("categories").update(update_data).eq("id", str(category_id)).execute()
    
    if not response.data:
         raise HTTPException(status_code=400, detail="Could not update category")
         
    return response.data[0]

@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_category(
    category_id: UUID,
    current_user = Depends(get_current_admin) # Admin only
):
    """
    Delete a category. Admin only.
    """
    supabase = get_supabase()
    
    # Check if category exists
    existing = supabase.table("categories").select("id").eq("id", str(category_id)).execute()
    if not existing.data:
        raise HTTPException(status_code=404, detail="Category not found")
        
    supabase.table("categories").delete().eq("id", str(category_id)).execute()
    return None
