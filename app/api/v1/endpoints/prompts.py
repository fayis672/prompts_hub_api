from typing import List, Optional
from uuid import UUID
from enum import Enum
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request, BackgroundTasks
from app.schemas.prompt import PromptCreate, PromptUpdate, PromptResponse, PromptType
from app.schemas.prompt_rating import PromptRatingCreate, PromptRatingResponse
from app.schemas.bookmark import BookmarkCreate, BookmarkResponse
from app.schemas.prompt_like import PromptLikeResponse, PromptLikeToggleResponse
from app.core.security import get_current_user, get_current_user_optional
from app.db.supabase import get_supabase




class SortOrder(str, Enum):
    new = "new"
    most_liked = "most_liked"
    most_viewed = "most_viewed"
    most_bookmarked = "most_bookmarked"


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
                      out = out.model_dump(mode='json')
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
                      out = out.model_dump(mode='json')
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
    skip: int = Query(0, ge=0),
    limit: int = Query(20, gt=0, le=100),
    sort: SortOrder = Query(SortOrder.new, description="Sort order: new, most_liked, most_viewed, most_bookmarked"),
    user_id: Optional[UUID] = Query(None, description="Filter by author user ID"),
    category_id: Optional[UUID] = Query(None, description="Filter by category ID"),
    prompt_type: Optional[PromptType] = Query(None, description="Filter by prompt type"),
    status: Optional[str] = Query(None, description="Filter by status (draft, published, archived)"),
):
    """
    Retrieve prompts with sorting and filtering.

    - **sort=new** – newest first (default)
    - **sort=most_liked** – highest average rating first
    - **sort=most_viewed** – most views first
    - **sort=most_bookmarked** – most bookmarks first
    """
    supabase = get_supabase()
    query = supabase.table("prompts").select("*, prompt_outputs(*)")

    # --- Filters ---
    if user_id:
        query = query.eq("user_id", str(user_id))
    if category_id:
        query = query.eq("category_id", str(category_id))
    if prompt_type:
        query = query.eq("prompt_type", prompt_type.value)
    if status:
        query = query.eq("status", status)

    # --- Sorting ---
    if sort == SortOrder.most_liked:
        query = query.order("like_count", desc=True)
    elif sort == SortOrder.most_viewed:
        query = query.order("view_count", desc=True)
    elif sort == SortOrder.most_bookmarked:
        query = query.order("bookmark_count", desc=True)
    else:  # SortOrder.new
        query = query.order("created_at", desc=True)

    # --- Pagination ---
    query = query.range(skip, skip + limit - 1)

    response = query.execute()
    return response.data

@router.get("/search", response_model=List[PromptResponse])
def search_prompts(
    q: str = Query(..., min_length=1, description="Search query string"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, gt=0, le=100),
    sort: SortOrder = Query(SortOrder.new),
    category_id: Optional[UUID] = Query(None),
    prompt_type: Optional[PromptType] = Query(None),
):
    """
    Search prompts by title or description using a keyword query.

    - **q** – Required search keyword
    - **sort** – Sort order: new, most_liked, most_viewed, most_bookmarked
    - **category_id** – Optional category filter
    - **prompt_type** – Optional type filter (text, image, etc.)
    """
    supabase = get_supabase()

    # Search across title and description using ilike (case insensitive)
    query = (
        supabase.table("prompts")
        .select("*, prompt_outputs(*)")
        .or_(f"title.ilike.%{q}%,description.ilike.%{q}%")
        .eq("status", "published")
    )

    if category_id:
        query = query.eq("category_id", str(category_id))
    if prompt_type:
        query = query.eq("prompt_type", prompt_type.value)

    if sort == SortOrder.most_liked:
        query = query.order("like_count", desc=True)
    elif sort == SortOrder.most_viewed:
        query = query.order("view_count", desc=True)
    elif sort == SortOrder.most_bookmarked:
        query = query.order("bookmark_count", desc=True)
    else:
        query = query.order("created_at", desc=True)

    query = query.range(skip, skip + limit - 1)

    response = query.execute()
    return response.data

@router.get("/{prompt_id}", response_model=PromptResponse)
def read_prompt(
    prompt_id: UUID, 
    request: Request,
    background_tasks: BackgroundTasks,
    current_user = Depends(get_current_user_optional)
):
    """
    Get prompt by ID. Records a view in the background.
    """
    supabase = get_supabase()
    response = supabase.table("prompts").select("*, prompt_outputs(*)").eq("id", str(prompt_id)).execute()
    
    if not response.data:
        raise HTTPException(status_code=404, detail="Prompt not found")
        
    prompt = response.data[0]

    # Record view in background
    user_id = current_user["id"] if current_user else None
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    referrer = request.headers.get("referer")
    
    background_tasks.add_task(
        record_prompt_view, 
        prompt_id=str(prompt_id), 
        user_id=user_id,
        ip_address=ip_address,
        user_agent=user_agent,
        referrer=referrer
    )
        
    return prompt

def record_prompt_view(
    prompt_id: str, 
    user_id: Optional[str] = None, 
    ip_address: Optional[str] = None, 
    user_agent: Optional[str] = None, 
    referrer: Optional[str] = None
):
    """
    Helper to record a view and increment count in the background.
    """
    supabase = get_supabase()
    
    try:
        # 1. Insert into prompt_views
        view_data = {
            "prompt_id": prompt_id,
        }
        if user_id: view_data["user_id"] = user_id
        if ip_address: view_data["ip_address"] = ip_address
        if user_agent: view_data["user_agent"] = user_agent
        if referrer: view_data["referrer"] = referrer
        
        supabase.table("prompt_views").insert(view_data).execute()
        
        # 2. Increment view_count in prompts table
        prompt_res = supabase.table("prompts").select("view_count").eq("id", prompt_id).execute()
        if prompt_res.data:
            current_count = prompt_res.data[0].get("view_count") or 0
            supabase.table("prompts").update({"view_count": current_count + 1}).eq("id", prompt_id).execute()
    except Exception as e:
        print(f"Error recording view: {e}")


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
    
    update_data = prompt_in.model_dump(mode='json', exclude_unset=True)
    
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

    return None

# Engagement Endpoints

@router.post("/{prompt_id}/like", response_model=PromptLikeToggleResponse)
def like_prompt(
    prompt_id: UUID,
    current_user = Depends(get_current_user)
):
    """
    Like a prompt.
    """
    supabase = get_supabase()
    user_id = current_user["id"]
    
    # Check if already liked
    existing = supabase.table("prompt_likes").select("*").eq("user_id", user_id).eq("prompt_id", str(prompt_id)).execute()
    if existing.data:
        # Already liked. Return current count
        prompt_res = supabase.table("prompts").select("like_count").eq("id", str(prompt_id)).execute()
        return {"has_liked": True, "like_count": prompt_res.data[0].get("like_count") or 0}
        
    data = {
        "user_id": user_id,
        "prompt_id": str(prompt_id)
    }
    
    supabase.table("prompt_likes").insert(data).execute()
    
    prompt_res = supabase.table("prompts").select("like_count").eq("id", str(prompt_id)).execute()
    current_count = prompt_res.data[0].get("like_count") or 0 if prompt_res.data else 0
    new_count = current_count + 1
    
    supabase.table("prompts").update({"like_count": new_count}).eq("id", str(prompt_id)).execute()
    
    return {"has_liked": True, "like_count": new_count}

@router.delete("/{prompt_id}/like", response_model=PromptLikeToggleResponse)
def unlike_prompt(
    prompt_id: UUID,
    current_user = Depends(get_current_user)
):
    """
    Remove like from a prompt.
    """
    supabase = get_supabase()
    user_id = current_user["id"]
    
    existing = supabase.table("prompt_likes").select("*").eq("user_id", user_id).eq("prompt_id", str(prompt_id)).execute()
    if not existing.data:
        prompt_res = supabase.table("prompts").select("like_count").eq("id", str(prompt_id)).execute()
        count = prompt_res.data[0].get("like_count") or 0 if prompt_res.data else 0
        return {"has_liked": False, "like_count": count}
    
    supabase.table("prompt_likes").delete().eq("user_id", user_id).eq("prompt_id", str(prompt_id)).execute()
    
    prompt_res = supabase.table("prompts").select("like_count").eq("id", str(prompt_id)).execute()
    current_count = prompt_res.data[0].get("like_count") or 0 if prompt_res.data else 0
    new_count = max(0, current_count - 1)
    
    supabase.table("prompts").update({"like_count": new_count}).eq("id", str(prompt_id)).execute()
    
    return {"has_liked": False, "like_count": new_count}

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


@router.get("/category/{category_id}", response_model=List[PromptResponse])
def get_prompts_by_category(
    category_id: UUID,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, gt=0, le=100),
    sort: SortOrder = Query(SortOrder.new, description="Sort order: new, most_liked, most_viewed, most_bookmarked"),
    status: Optional[str] = Query(None, description="Filter by status (draft, published, archived)"),
):
    """
    Get all prompts belonging to a specific category.

    Supports the same `sort` options as the main prompts list:
    - **new** – newest first (default)
    - **most_liked** – highest average rating first
    - **most_viewed** – most views first
    - **most_bookmarked** – most bookmarks first
    """
    supabase = get_supabase()

    # Verify the category exists
    cat_res = supabase.table("categories").select("id").eq("id", str(category_id)).execute()
    if not cat_res.data:
        raise HTTPException(status_code=404, detail="Category not found")

    query = supabase.table("prompts").select("*, prompt_outputs(*)").eq("category_id", str(category_id))

    if status:
        query = query.eq("status", status)

    if sort == SortOrder.most_liked:
        query = query.order("like_count", desc=True)
    elif sort == SortOrder.most_viewed:
        query = query.order("view_count", desc=True)
    elif sort == SortOrder.most_bookmarked:
        query = query.order("bookmark_count", desc=True)
    else:
        query = query.order("created_at", desc=True)

    query = query.range(skip, skip + limit - 1)
    response = query.execute()
    return response.data


@router.get("/tag/{tag}", response_model=List[PromptResponse])
def get_prompts_by_tag(
    tag: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, gt=0, le=100),
    sort: SortOrder = Query(SortOrder.new, description="Sort order: new, most_liked, most_viewed, most_bookmarked"),
    status: Optional[str] = Query(None, description="Filter by status (draft, published, archived)"),
):
    """
    Get all prompts associated with a specific tag.

    The `tag` path parameter is matched against the tag **slug** first,
    then falls back to a case-insensitive **name** match.

    Supports the same `sort` options as the main prompts list.
    """
    supabase = get_supabase()

    # Resolve tag — try slug first, then name
    tag_res = supabase.table("tags").select("id, slug, name").eq("slug", tag).execute()
    if not tag_res.data:
        tag_res = supabase.table("tags").select("id, slug, name").ilike("name", tag).execute()
    if not tag_res.data:
        raise HTTPException(status_code=404, detail=f"Tag '{tag}' not found")

    tag_id = tag_res.data[0]["id"]

    # Fetch prompt IDs linked to this tag via the prompt_tags join table
    pt_res = supabase.table("prompt_tags").select("prompt_id").eq("tag_id", tag_id).execute()
    if not pt_res.data:
        return []

    prompt_ids = [row["prompt_id"] for row in pt_res.data]

    query = supabase.table("prompts").select("*, prompt_outputs(*)").in_("id", prompt_ids)

    if status:
        query = query.eq("status", status)

    if sort == SortOrder.most_liked:
        query = query.order("like_count", desc=True)
    elif sort == SortOrder.most_viewed:
        query = query.order("view_count", desc=True)
    elif sort == SortOrder.most_bookmarked:
        query = query.order("bookmark_count", desc=True)
    else:
        query = query.order("created_at", desc=True)

    query = query.range(skip, skip + limit - 1)
    response = query.execute()
    return response.data


@router.get("/trending", response_model=List[PromptResponse])
def get_trending_prompts(
    limit: int = Query(20, gt=0, le=100),
):
    """
    Get currently trending prompts.

    Returns prompts from the pre-calculated `trending_prompts` table, ordered
    by rank (ascending). The trending score is computed based on views,
    ratings, and bookmarks in the last 24 hours.
    """
    supabase = get_supabase()

    # Fetch active trending records ordered by rank
    trending_res = (
        supabase.table("trending_prompts")
        .select("prompt_id, rank")
        .order("rank", desc=False)
        .limit(limit)
        .execute()
    )

    if not trending_res.data:
        return []

    prompt_ids = [row["prompt_id"] for row in trending_res.data]

    # Fetch the full prompt details for those IDs
    prompts_res = (
        supabase.table("prompts")
        .select("*, prompt_outputs(*)")
        .in_("id", prompt_ids)
        .execute()
    )

    # Re-order results to match the rank order from trending_prompts
    prompts_by_id = {p["id"]: p for p in prompts_res.data}
    ordered = [prompts_by_id[pid] for pid in prompt_ids if pid in prompts_by_id]

    return ordered


@router.get("/recommendations/prompts", response_model=List[PromptResponse])
def get_recommended_prompts(
    limit: int = Query(10, gt=0, le=50),
    current_user = Depends(get_current_user)
):
    """
    Get recommended prompts for the current user.
    Prioritizes popular prompts in categories the user has previously engaged with.
    """
    supabase = get_supabase()
    user_id = current_user["id"]

    # 1. Identify categories of interest from ratings and bookmarks
    rated = supabase.table("prompt_ratings").select("prompts(category_id)").eq("user_id", user_id).gte("rating", 4).execute()
    bookmarked = supabase.table("bookmarks").select("prompts(category_id)").eq("user_id", user_id).execute()

    category_ids = {r["prompts"]["category_id"] for r in rated.data if r.get("prompts")}
    category_ids.update({b["prompts"]["category_id"] for b in bookmarked.data if b.get("prompts")})

    # 2. Identify prompts already interacted with to exclude them
    interacted_res = supabase.table("prompt_ratings").select("prompt_id").eq("user_id", user_id).execute()
    excluded_ids = {i["prompt_id"] for i in interacted_res.data}

    bookmark_ids = supabase.table("bookmarks").select("prompt_id").eq("user_id", user_id).execute()
    excluded_ids.update({b["prompt_id"] for b in bookmark_ids.data})

    query = supabase.table("prompts").select("*, prompt_outputs(*)").eq("status", "published").neq("user_id", user_id)

    if category_ids:
        query = query.in_("category_id", list(category_ids))

    # Order by popularity/quality
    query = query.order("average_rating", desc=True).order("view_count", desc=True).limit(limit)

    response = query.execute()

    # Filter out already interacted prompts in Python for simplicity
    recommended = [p for p in response.data if p["id"] not in excluded_ids]

    if len(recommended) < limit:
        # Fallback: fill with globally popular prompts that are not in exclusion list
        fallback_query = supabase.table("prompts").select("*, prompt_outputs(*)").eq("status", "published").neq("user_id", user_id).order("average_rating", desc=True).limit(limit * 2)
        fallback_res = fallback_query.execute()
        for p in fallback_res.data:
            if p["id"] not in excluded_ids and p["id"] not in [r["id"] for r in recommended]:
                recommended.append(p)
                if len(recommended) >= limit:
                    break

    return recommended[:limit]


