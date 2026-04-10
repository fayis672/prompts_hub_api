from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from app.schemas.prompt_view import PromptHistoryResponse
from app.core.security import get_current_user
from app.db.supabase import get_supabase

router = APIRouter()

@router.get("/", response_model=List[PromptHistoryResponse])
def get_user_history(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, gt=0, le=100),
    current_user = Depends(get_current_user)
):
    """
    Get the current user's prompt visit history.
    Returns prompts visited by the user, ordered by most recent visit.
    """
    supabase = get_supabase()
    user_id = current_user["id"]

    # Fetch recent views with joined prompt data
    # Note: This will return multiple entries if the same prompt is visited multiple times.
    # To get unique prompts, we rely on the client or could potentially use a more complex query.
    response = (
        supabase.table("prompt_views")
        .select("*, prompt:prompts(*, prompt_outputs(*))")
        .eq("user_id", user_id)
        .order("viewed_at", desc=True)
        .range(skip, skip + limit - 1)
        .execute()
    )
    
    # Filter out any entries where prompt might be missing (e.g. deleted but view remains)
    return [view for view in response.data if view.get("prompt")]

@router.delete("/", status_code=status.HTTP_204_NO_CONTENT)
def clear_history(
    current_user = Depends(get_current_user)
):
    """
    Clear all visit history for the current user.
    """
    supabase = get_supabase()
    user_id = current_user["id"]
    
    try:
        supabase.table("prompt_views").delete().eq("user_id", user_id).execute()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to clear history: {str(e)}")
        
    return None

@router.delete("/{prompt_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_from_history(
    prompt_id: UUID,
    current_user = Depends(get_current_user)
):
    """
    Remove all visit records for a specific prompt from the user's history.
    """
    supabase = get_supabase()
    user_id = current_user["id"]
    
    try:
        supabase.table("prompt_views").delete().eq("user_id", user_id).eq("prompt_id", str(prompt_id)).execute()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to remove from history: {str(e)}")
        
    return None
