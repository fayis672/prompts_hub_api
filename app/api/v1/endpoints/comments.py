from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from app.schemas.comment import CommentCreate, CommentUpdate, CommentResponse
from app.schemas.comment_vote import CommentVoteCreate, CommentVoteResponse, VoteType
from app.core.security import get_current_user, get_current_admin
from app.db.supabase import get_supabase

router = APIRouter()

@router.post("/", response_model=CommentResponse, status_code=status.HTTP_201_CREATED)
def create_comment(
    comment_in: CommentCreate,
    current_user = Depends(get_current_user)
):
    """
    Create a new comment.
    """
    supabase = get_supabase()
    user_id = current_user["id"]
    
    data = comment_in.model_dump()
    data["user_id"] = user_id
    
    # Optional: Verify prompt_id exists and parent_comment_id (if provided) exists
    
    response = supabase.table("comments").insert(data).execute()
    
    if not response.data:
        raise HTTPException(status_code=400, detail="Could not create comment")
        
    return response.data[0]

@router.get("/prompt/{prompt_id}", response_model=List[CommentResponse])
def read_comments_for_prompt(
    prompt_id: UUID,
    skip: int = 0,
    limit: int = 100
):
    """
    Retrieve comments for a specific prompt.
    """
    supabase = get_supabase()
    # Order by created_at desc or asc? Usually threads need structure.
    # For flat list we can filter by prompt_id.
    query = supabase.table("comments").select("*").eq("prompt_id", str(prompt_id))
    query = query.range(skip, skip + limit - 1)
    
    response = query.execute()
    return response.data

@router.put("/{comment_id}", response_model=CommentResponse)
def update_comment(
    comment_id: UUID,
    comment_in: CommentUpdate,
    current_user = Depends(get_current_user)
):
    """
    Update a comment. Owner or Admin.
    """
    supabase = get_supabase()
    user_id = current_user["id"]
    is_admin = current_user.get("role") == "admin"
    
    # Ownership check
    existing = supabase.table("comments").select("user_id").eq("id", str(comment_id)).execute()
    if not existing.data:
        raise HTTPException(status_code=404, detail="Comment not found")
        
    if existing.data[0]["user_id"] != user_id and not is_admin:
        raise HTTPException(status_code=403, detail="Not authorized")
        
    update_data = comment_in.model_dump(exclude_unset=True)
    if not is_admin:
        # Prevent regular users from approving/moderating via update
        update_data.pop("is_approved", None)
        
    if not update_data:
        return existing.data[0]

    update_data["is_edited"] = True
    
    response = supabase.table("comments").update(update_data).eq("id", str(comment_id)).execute()
    
    if not response.data:
         raise HTTPException(status_code=400, detail="Could not update comment")
         
    return response.data[0]

@router.delete("/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_comment(
    comment_id: UUID,
    current_user = Depends(get_current_user)
):
    """
    Delete a comment. Owner or Admin.
    """
    supabase = get_supabase()
    user_id = current_user["id"]
    is_admin = current_user.get("role") == "admin"
    
    # Ownership check
    existing = supabase.table("comments").select("user_id").eq("id", str(comment_id)).execute()
    if not existing.data:
        raise HTTPException(status_code=404, detail="Comment not found")
        
    if existing.data[0]["user_id"] != user_id and not is_admin:
        raise HTTPException(status_code=403, detail="Not authorized")
        
    supabase.table("comments").delete().eq("id", str(comment_id)).execute()
    return None

@router.post("/{comment_id}/vote", response_model=CommentVoteResponse)
def vote_comment(
    comment_id: UUID,
    vote_in: CommentVoteCreate,
    current_user = Depends(get_current_user)
):
    """
    Upvote/Downvote a comment. Upserts.
    """
    supabase = get_supabase()
    user_id = current_user["id"]
    
    # Check if vote exists (UNIQUE constraint on user_id, comment_id)
    data = {
        "user_id": user_id,
        "comment_id": str(comment_id),
        "vote_type": vote_in.vote_type
    }
    
    response = supabase.table("comment_votes").upsert(data, on_conflict="user_id, comment_id").execute()
    
    if not response.data:
        raise HTTPException(status_code=400, detail="Could not vote")
        
    return response.data[0]
