from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from app.schemas.prompt import PromptCreate, PromptUpdate, PromptResponse
from app.schemas.prompt_rating import PromptRatingCreate, PromptRatingResponse
from app.schemas.bookmark import BookmarkCreate, BookmarkResponse
from app.core.security import get_current_user
from app.db.supabase import get_supabase


router = APIRouter()

@router.post("/", response_model=PromptResponse, status_code=status.HTTP_201_CREATED)
def create_prompt(
    prompt_in: PromptCreate,
    current_user = Depends(get_current_user)
):
    """
    Create a new prompt.
    """
    supabase = get_supabase()
    # Extract user ID from the Auth response
    # Supabase get_user returns UserResponse, accessing .user property
    user_id = current_user["id"]



    prompt_data = prompt_in.model_dump(mode='json')
    variables_data = prompt_data.pop("variables", None)
    tags_data = prompt_data.pop("tags", None)
    outputs_data = prompt_data.pop("prompt_outputs", None)

    prompt_data["user_id"] = user_id
    
    try:
        # In a real app, you might want to handle slug generation here or in DB
        
        response = supabase.table("prompts").insert(prompt_data).execute()
        
        if not response.data:
            raise HTTPException(status_code=400, detail="Could not create prompt")
        
        new_prompt = response.data[0]
        prompt_id = new_prompt["id"]

        # Handle Variables
        if variables_data:
            for out in variables_data:
                 # Check if loop variable is dict
                 if not isinstance(out, dict):
                      out = out.model_dump()
                 out["prompt_id"] = prompt_id
            supabase.table("prompt_variables").insert(variables_data).execute()

        # Handle Tags
        if tags_data:
            for tag_name in tags_data:
                slug = tag_name.lower().strip().replace(" ", "-")
                
                tag_res = supabase.table("tags").select("id").eq("slug", slug).execute()
                
                tag_id = None
                if tag_res.data:
                    tag_id = tag_res.data[0]["id"]
                else:
                    new_tag = {"name": tag_name.strip(), "slug": slug}
                    tag_create_res = supabase.table("tags").insert(new_tag).execute()
                    if tag_create_res.data:
                        tag_id = tag_create_res.data[0]["id"]
                
                if tag_id:
                    link_data = {"prompt_id": prompt_id, "tag_id": tag_id}
                    supabase.table("prompt_tags").insert(link_data).execute()

        # Handle Outputs
        if outputs_data:
            for out in outputs_data:
                 if not isinstance(out, dict):
                      out = out.model_dump()
                 out["prompt_id"] = prompt_id
                 out["user_id"] = user_id
            supabase.table("prompt_outputs").insert(outputs_data).execute()
            
        return new_prompt

    except Exception as e:
        print(f"Error creating prompt: {e}")
        # Return error as detail for debugging
        raise HTTPException(status_code=500, detail=f"Creation failed: {str(e)}")

@router.get("/", response_model=List[PromptResponse])
def read_prompts(
    skip: int = 0,
    limit: int = 100,
    user_id: Optional[UUID] = None,
    # Add other filters as needed
):
    """
    Retrieve prompts.
    """
    supabase = get_supabase()
    query = supabase.table("prompts").select("*")
    
    if user_id:
        query = query.eq("user_id", str(user_id))
        
    # Pagination
    # Supabase range is 0-indexed, inclusive? 
    # range(from, to)
    query = query.range(skip, skip + limit - 1)
    
    response = query.execute()
    return response.data

@router.get("/{prompt_id}", response_model=PromptResponse)
def read_prompt(prompt_id: UUID):
    """
    Get prompt by ID.
    """
    supabase = get_supabase()
    response = supabase.table("prompts").select("*").eq("id", str(prompt_id)).execute()
    
    if not response.data:
        raise HTTPException(status_code=404, detail="Prompt not found")
        
    return response.data[0]

@router.put("/{prompt_id}", response_model=PromptResponse)
def update_prompt(
    prompt_id: UUID,
    prompt_in: PromptUpdate,
    current_user = Depends(get_current_user)
):
    """
    Update a prompt.
    """
    supabase = get_supabase()
    today = current_user
    user_id = current_user["id"]
    is_admin = current_user.get("role") == "admin"
    
    # Verify ownership
    existing = supabase.table("prompts").select("user_id").eq("id", str(prompt_id)).execute()
    if not existing.data:
        raise HTTPException(status_code=404, detail="Prompt not found")
        
    if existing.data[0]["user_id"] != user_id and not is_admin:
        raise HTTPException(status_code=403, detail="Not authorized to update this prompt")
    
    update_data = prompt_in.model_dump(exclude_unset=True)
    
    response = supabase.table("prompts").update(update_data).eq("id", str(prompt_id)).execute()
    
    if not response.data:
         raise HTTPException(status_code=400, detail="Could not update prompt")
         
    return response.data[0]


@router.delete("/{prompt_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_prompt(
    prompt_id: UUID,
    current_user = Depends(get_current_user)
):
    """
    Delete a prompt.
    """
    supabase = get_supabase()
    user_id = current_user["id"]
    is_admin = current_user.get("role") == "admin"
    
    # Verify ownership
    existing = supabase.table("prompts").select("user_id").eq("id", str(prompt_id)).execute()
    if not existing.data:
        raise HTTPException(status_code=404, detail="Prompt not found")
        
    if existing.data[0]["user_id"] != user_id and not is_admin:
        raise HTTPException(status_code=403, detail="Not authorized to delete this prompt")
        
    supabase.table("prompts").delete().eq("id", str(prompt_id)).execute()
    
    supabase.table("prompts").delete().eq("id", str(prompt_id)).execute()
    
    return None

# Engagement Endpoints

@router.post("/{prompt_id}/rate", response_model=PromptRatingResponse)
def rate_prompt(
    prompt_id: UUID,
    rating_in: PromptRatingCreate,
    current_user = Depends(get_current_user)
):
    """
    Rate a prompt (1-5). Upserts (updates if already rated).
    """
    supabase = get_supabase()
    user_id = current_user["id"]
    
    # Check bounds (handled by Pydantic but good to be safe)
    if not (1 <= rating_in.rating <= 5):
        raise HTTPException(status_code=400, detail="Rating must be between 1 and 5")
        
    # Check if user already rated this prompt
    # In Supabase/Postgres we can use upsert if we have a unique constraint on (user_id, prompt_id)
    # The schema has UNIQUE(user_id, prompt_id)
    
    data = {
        "user_id": user_id,
        "prompt_id": str(prompt_id),
        "rating": rating_in.rating
    }
    
    # Using upsert
    response = supabase.table("prompt_ratings").upsert(data, on_conflict="user_id, prompt_id").execute()
    
    if not response.data:
        raise HTTPException(status_code=400, detail="Could not rate prompt")
        
    return response.data[0]

@router.post("/{prompt_id}/bookmark", response_model=BookmarkResponse)
def bookmark_prompt(
    prompt_id: UUID,
    current_user = Depends(get_current_user)
):
    """
    Bookmark a prompt. Idempotent (if already bookmarked, returns existing).
    """
    supabase = get_supabase()
    user_id = current_user["id"]
    
    # Check if already bookmarked
    existing = supabase.table("bookmarks").select("*").eq("user_id", user_id).eq("prompt_id", str(prompt_id)).execute()
    if existing.data:
        return existing.data[0]
        
    data = {
        "user_id": user_id,
        "prompt_id": str(prompt_id)
    }
    
    response = supabase.table("bookmarks").insert(data).execute()
    
    if not response.data:
         raise HTTPException(status_code=400, detail="Could not bookmark prompt")
         
    return response.data[0]

@router.delete("/{prompt_id}/bookmark", status_code=status.HTTP_204_NO_CONTENT)
def unbookmark_prompt(
    prompt_id: UUID,
    current_user = Depends(get_current_user)
):
    """
    Remove bookmark.
    """
    supabase = get_supabase()
    user_id = current_user["id"]
    
    supabase.table("bookmarks").delete().eq("user_id", user_id).eq("prompt_id", str(prompt_id)).execute()
    return None


