from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from datetime import datetime
from app.schemas.user import UserCreate, UserUpdate, UserResponse, UserRole, UserExistsResponse, UserCreateRequest, UserProfileDetails, UserFollowResponse
from app.schemas.prompt import PromptResponse
from app.core.security import get_current_user, get_current_admin, get_current_auth_user, get_current_user_optional

from app.db.supabase import get_supabase

router = APIRouter()

@router.get("/check-exists", response_model=UserExistsResponse)
def check_user_exists(
    current_auth_user = Depends(get_current_auth_user)
):
    """
    Check if the authenticated user has a profile in the users table.
    Requires a valid JWT token.
    """
    supabase = get_supabase()
    user_id = current_auth_user.id
    
    # Check ID
    response = supabase.table("users").select("id").eq("id", user_id).execute()
    if response.data:
        return UserExistsResponse(exists=True, conflict_field="id")
            
    return UserExistsResponse(exists=False)

@router.post("/", response_model=UserResponse)
def create_user(
    user_in: UserCreateRequest,
    current_auth_user = Depends(get_current_auth_user)
):
    """
    Create a new user profile.
    This should be called after Supabase Auth signup.
    Requires a valid JWT token. 
    User ID and Email are extracted from the token.
    """
    supabase = get_supabase()
    
    # Extract ID and Email from the verified token
    user_id = current_auth_user.id
    user_email = current_auth_user.email
    
    if not user_id or not user_email:
        raise HTTPException(status_code=400, detail="Token missing user ID or email")
    
    # Check if user already exists
    # We check by ID primarily as it's the specific record key
    existing_id = supabase.table("users").select("id").eq("id", user_id).execute()
    if existing_id.data:
         raise HTTPException(status_code=400, detail="User profile already exists")
    
    # Check username uniqueness (since username is set by user)
    existing_username = supabase.table("users").select("id").eq("username", user_in.username).execute()
    if existing_username.data:
         raise HTTPException(status_code=400, detail="User with this username already exists")
         
    user_data = user_in.model_dump(mode='json')
    user_data["id"] = user_id
    user_data["email"] = user_email
    user_data["password_hash"] = "managed_by_supabase_auth"
    user_data["role"] = "user" # Default role
    user_data["created_at"] = datetime.utcnow().isoformat()
    user_data["updated_at"] = datetime.utcnow().isoformat()
    
    response = supabase.table("users").insert(user_data).execute()
    
    if not response.data:
        raise HTTPException(status_code=400, detail="Could not create user")
        
    return response.data[0]

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
    
    update_data = user_in.model_dump(mode='json', exclude_unset=True)
    
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
    
    update_data = user_in.model_dump(mode='json', exclude_unset=True)
    
    if role:
        update_data["role"] = role
        
    if not update_data:
        return existing.data[0]
        
    response = supabase.table("users").update(update_data).eq("id", str(user_id)).execute()
    
    if not response.data:
         raise HTTPException(status_code=400, detail="Could not update user")
         
    return response.data[0]


@router.get("/recommendations/prompters", response_model=List[UserResponse])
def get_recommended_prompters(
    limit: int = Query(5, gt=0, le=20),
    current_user = Depends(get_current_user)
):
    """
    Get recommended prompters (creators) based on current user's engagements.
    Identifies users whose prompts the current user has rated highly, bookmarked, or commented on.
    """
    supabase = get_supabase()
    user_id = current_user["id"]

    # 1. Get creator IDs from ratings
    # We join with prompts to get user_id of the creator
    ratings = supabase.table("prompt_ratings").select("prompts(user_id)").eq("user_id", user_id).gte("rating", 4).execute()
    creator_ids = [r["prompts"]["user_id"] for r in ratings.data if r.get("prompts")]

    # 2. Get creator IDs from bookmarks
    bookmarks = supabase.table("bookmarks").select("prompts(user_id)").eq("user_id", user_id).execute()
    creator_ids.extend([b["prompts"]["user_id"] for b in bookmarks.data if b.get("prompts")])

    # 3. Get creator IDs from comments
    comments = supabase.table("comments").select("prompts(user_id)").eq("user_id", user_id).execute()
    creator_ids.extend([c["prompts"]["user_id"] for c in comments.data if c.get("prompts")])

    # Filter out current user and count frequencies
    from collections import Counter
    creator_counts = Counter([cid for cid in creator_ids if cid != user_id])
    
    top_creator_ids = [cid for cid, count in creator_counts.most_common(limit)]

    if not top_creator_ids:
        # Fallback: Just return some active public users (excluding me)
        response = supabase.table("users").select("*").neq("id", user_id).limit(limit).execute()
        return response.data

    # Fetch full user details for the top creators
    response = supabase.table("users").select("*").in_("id", top_creator_ids).execute()
    return response.data


@router.post("/profile/{target_username}/follow", response_model=UserFollowResponse)
def follow_user(
    target_username: str,
    current_user = Depends(get_current_user)
):
    """
    Follow a user by username.
    """
    supabase = get_supabase()
    follower_id = current_user["id"]
    
    # Get target user ID from username
    target_res = supabase.table("users").select("id, total_followers").eq("username", target_username).execute()
    if not target_res.data:
        raise HTTPException(status_code=404, detail="User not found")
        
    following_id = target_res.data[0]["id"]
    
    if follower_id == following_id:
        raise HTTPException(status_code=400, detail="Cannot follow yourself")
        
    # Check if already following
    existing = supabase.table("follows").select("*").eq("follower_id", str(follower_id)).eq("following_id", str(following_id)).execute()
    if existing.data:
        # Already followed
        return {"has_followed": True, "follower_count": target_res.data[0].get("total_followers") or 0}
        
    # Insert follow
    try:
        supabase.table("follows").insert({
            "follower_id": str(follower_id),
            "following_id": str(following_id)
        }).execute()
        
        # Increment total_followers for target
        new_count = (target_res.data[0].get("total_followers") or 0) + 1
        supabase.table("users").update({"total_followers": new_count}).eq("id", str(following_id)).execute()
        
        # Increment total_following for current user
        current_res = supabase.table("users").select("total_following").eq("id", str(follower_id)).execute()
        if current_res.data:
            new_following = (current_res.data[0].get("total_following") or 0) + 1
            supabase.table("users").update({"total_following": new_following}).eq("id", str(follower_id)).execute()
            
        return {"has_followed": True, "follower_count": new_count}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/profile/{target_username}/follow", response_model=UserFollowResponse)
def unfollow_user(
    target_username: str,
    current_user = Depends(get_current_user)
):
    """
    Unfollow a user by username.
    """
    supabase = get_supabase()
    follower_id = current_user["id"]
    
    target_res = supabase.table("users").select("id, total_followers").eq("username", target_username).execute()
    if not target_res.data:
        raise HTTPException(status_code=404, detail="User not found")
        
    following_id = target_res.data[0]["id"]
    
    existing = supabase.table("follows").select("*").eq("follower_id", str(follower_id)).eq("following_id", str(following_id)).execute()
    if not existing.data:
        return {"has_followed": False, "follower_count": target_res.data[0].get("total_followers") or 0}
        
    try:
        supabase.table("follows").delete().eq("follower_id", str(follower_id)).eq("following_id", str(following_id)).execute()
        
        # Decrement total_followers for target
        new_count = max(0, (target_res.data[0].get("total_followers") or 0) - 1)
        supabase.table("users").update({"total_followers": new_count}).eq("id", str(following_id)).execute()
        
        # Decrement total_following for current user
        current_res = supabase.table("users").select("total_following").eq("id", str(follower_id)).execute()
        if current_res.data:
            new_following = max(0, (current_res.data[0].get("total_following") or 0) - 1)
            supabase.table("users").update({"total_following": new_following}).eq("id", str(follower_id)).execute()
            
        return {"has_followed": False, "follower_count": new_count}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/profile/{username}", response_model=UserProfileDetails)
def get_user_profile(
    username: str,
    current_user = Depends(get_current_user_optional)
):
    """
    Get a user's public profile by username, including follow status.
    """
    supabase = get_supabase()
    response = supabase.table("users").select("*").eq("username", username).execute()
    
    if not response.data:
        raise HTTPException(status_code=404, detail="User not found")
        
    user = response.data[0]
    
    is_following = False
    if current_user:
        follower_id = current_user["id"]
        following_id = user["id"]
        if str(follower_id) != str(following_id):
            follow_check = supabase.table("follows").select("id").eq("follower_id", str(follower_id)).eq("following_id", str(following_id)).execute()
            if follow_check.data:
                is_following = True
                
    user["is_following"] = is_following
    return user

@router.get("/profile/{username}/prompts", response_model=List[PromptResponse])
def get_user_prompts(
    username: str,
    skip: int = 0,
    limit: int = 20
):
    """
    Get a list of published prompts created by this user.
    """
    supabase = get_supabase()
    
    # 1. Resolve username to user_id
    user_res = supabase.table("users").select("id").eq("username", username).execute()
    if not user_res.data:
        raise HTTPException(status_code=404, detail="User not found")
        
    target_user_id = user_res.data[0]["id"]
    
    # 2. Fetch published prompts by user_id
    query = (
        supabase.table("prompts")
        .select("*, prompt_outputs(*), author:users(*)")
        .eq("user_id", str(target_user_id))
        .eq("status", "published")
        .order("created_at", desc=True)
        .range(skip, skip + limit - 1)
    )
    
    response = query.execute()
    return response.data

