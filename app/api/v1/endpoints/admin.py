from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from app.core.security import get_current_admin
from app.db.supabase import get_supabase

router = APIRouter()


# ─────────────────────────────────────────────
# Dashboard Stats
# ─────────────────────────────────────────────

@router.get("/stats")
def get_admin_stats(current_user=Depends(get_current_admin)):
    """
    Get aggregate platform stats for the admin dashboard. Admin only.
    """
    supabase = get_supabase()

    try:
        total_users = supabase.table("users").select("id", count="exact").execute()
        total_prompts = supabase.table("prompts").select("id", count="exact").execute()
        total_comments = supabase.table("comments").select("id", count="exact").execute()
        total_tags = supabase.table("tags").select("id", count="exact").execute()
        total_reports = supabase.table("reports").select("id", count="exact").execute()
        pending_reports = (
            supabase.table("reports")
            .select("id", count="exact")
            .eq("status", "pending")
            .execute()
        )
        published_prompts = (
            supabase.table("prompts")
            .select("id", count="exact")
            .eq("status", "published")
            .execute()
        )
        featured_prompts = (
            supabase.table("prompts")
            .select("id", count="exact")
            .eq("is_featured", True)
            .execute()
        )

        # Recent users (last 5)
        recent_users_res = (
            supabase.table("users")
            .select("id, username, display_name, avatar_url, role, created_at, is_active")
            .order("created_at", desc=True)
            .limit(5)
            .execute()
        )

        # Recent prompts (last 5)
        recent_prompts_res = (
            supabase.table("prompts")
            .select("id, title, status, created_at, view_count, like_count, author:users(username, display_name)")
            .order("created_at", desc=True)
            .limit(5)
            .execute()
        )

        return {
            "total_users": total_users.count or 0,
            "total_prompts": total_prompts.count or 0,
            "total_comments": total_comments.count or 0,
            "total_tags": total_tags.count or 0,
            "total_reports": total_reports.count or 0,
            "pending_reports": pending_reports.count or 0,
            "published_prompts": published_prompts.count or 0,
            "featured_prompts": featured_prompts.count or 0,
            "recent_users": recent_users_res.data or [],
            "recent_prompts": recent_prompts_res.data or [],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch stats: {str(e)}")


# ─────────────────────────────────────────────
# User Management
# ─────────────────────────────────────────────

@router.get("/users")
def list_all_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, gt=0, le=100),
    search: Optional[str] = Query(None),
    role: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    current_user=Depends(get_current_admin),
):
    """
    List all users with pagination, search, and filters. Admin only.
    """
    supabase = get_supabase()
    query = supabase.table("users").select(
        "id, username, email, display_name, avatar_url, role, is_active, is_verified, "
        "total_prompts, total_followers, total_following, created_at, last_login_at"
    )

    if search:
        query = query.or_(f"username.ilike.%{search}%,email.ilike.%{search}%,display_name.ilike.%{search}%")
    if role:
        query = query.eq("role", role)
    if is_active is not None:
        query = query.eq("is_active", is_active)

    query = query.order("created_at", desc=True).range(skip, skip + limit - 1)
    response = query.execute()
    return response.data


@router.put("/users/{user_id}/role")
def update_user_role(
    user_id: UUID,
    role: str = Query(..., description="New role: user or admin"),
    current_user=Depends(get_current_admin),
):
    """
    Update a user's role. Admin only.
    """
    if role not in ("user", "admin"):
        raise HTTPException(status_code=400, detail="Role must be 'user' or 'admin'")

    supabase = get_supabase()
    existing = supabase.table("users").select("id").eq("id", str(user_id)).execute()
    if not existing.data:
        raise HTTPException(status_code=404, detail="User not found")

    response = supabase.table("users").update({"role": role}).eq("id", str(user_id)).execute()
    if not response.data:
        raise HTTPException(status_code=400, detail="Could not update role")
    return response.data[0]


@router.put("/users/{user_id}/status")
def toggle_user_status(
    user_id: UUID,
    is_active: bool = Query(...),
    current_user=Depends(get_current_admin),
):
    """
    Activate or deactivate a user. Admin only.
    """
    supabase = get_supabase()
    existing = supabase.table("users").select("id").eq("id", str(user_id)).execute()
    if not existing.data:
        raise HTTPException(status_code=404, detail="User not found")

    response = (
        supabase.table("users")
        .update({"is_active": is_active})
        .eq("id", str(user_id))
        .execute()
    )
    if not response.data:
        raise HTTPException(status_code=400, detail="Could not update user status")
    return response.data[0]


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(user_id: UUID, current_user=Depends(get_current_admin)):
    """
    Permanently delete a user. Admin only.
    """
    supabase = get_supabase()
    existing = supabase.table("users").select("id").eq("id", str(user_id)).execute()
    if not existing.data:
        raise HTTPException(status_code=404, detail="User not found")

    supabase.table("users").delete().eq("id", str(user_id)).execute()
    return None


# ─────────────────────────────────────────────
# Prompt Management
# ─────────────────────────────────────────────

@router.get("/prompts")
def list_all_prompts(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, gt=0, le=100),
    search: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    prompt_type: Optional[str] = Query(None),
    is_featured: Optional[bool] = Query(None),
    current_user=Depends(get_current_admin),
):
    """
    List all prompts (all statuses) with filters. Admin only.
    """
    supabase = get_supabase()
    query = supabase.table("prompts").select(
        "id, title, status, prompt_type, privacy_status, is_featured, "
        "view_count, like_count, bookmark_count, comment_count, average_rating, "
        "created_at, published_at, author:users(id, username, display_name, avatar_url)"
    )

    if search:
        query = query.or_(f"title.ilike.%{search}%,description.ilike.%{search}%")
    if status:
        query = query.eq("status", status)
    if prompt_type:
        query = query.eq("prompt_type", prompt_type)
    if is_featured is not None:
        query = query.eq("is_featured", is_featured)

    query = query.order("created_at", desc=True).range(skip, skip + limit - 1)
    response = query.execute()
    return response.data


@router.put("/prompts/{prompt_id}/feature")
def toggle_prompt_feature(
    prompt_id: UUID,
    is_featured: bool = Query(...),
    current_user=Depends(get_current_admin),
):
    """
    Feature or un-feature a prompt. Admin only.
    """
    from datetime import datetime

    supabase = get_supabase()
    existing = supabase.table("prompts").select("id").eq("id", str(prompt_id)).execute()
    if not existing.data:
        raise HTTPException(status_code=404, detail="Prompt not found")

    update_data = {"is_featured": is_featured}
    if is_featured:
        update_data["featured_at"] = datetime.utcnow().isoformat()

    response = (
        supabase.table("prompts")
        .update(update_data)
        .eq("id", str(prompt_id))
        .execute()
    )
    if not response.data:
        raise HTTPException(status_code=400, detail="Could not update prompt")
    return response.data[0]


@router.put("/prompts/{prompt_id}/status")
def update_prompt_status(
    prompt_id: UUID,
    status: str = Query(..., description="New status: draft, published, archived"),
    current_user=Depends(get_current_admin),
):
    """
    Update prompt status. Admin only.
    """
    if status not in ("draft", "published", "archived"):
        raise HTTPException(status_code=400, detail="Invalid status")

    supabase = get_supabase()
    existing = supabase.table("prompts").select("id").eq("id", str(prompt_id)).execute()
    if not existing.data:
        raise HTTPException(status_code=404, detail="Prompt not found")

    response = (
        supabase.table("prompts")
        .update({"status": status})
        .eq("id", str(prompt_id))
        .execute()
    )
    if not response.data:
        raise HTTPException(status_code=400, detail="Could not update prompt status")
    return response.data[0]


@router.delete("/prompts/{prompt_id}", status_code=status.HTTP_204_NO_CONTENT)
def admin_delete_prompt(prompt_id: UUID, current_user=Depends(get_current_admin)):
    """
    Delete any prompt. Admin only.
    """
    supabase = get_supabase()
    existing = supabase.table("prompts").select("id").eq("id", str(prompt_id)).execute()
    if not existing.data:
        raise HTTPException(status_code=404, detail="Prompt not found")

    supabase.table("prompts").delete().eq("id", str(prompt_id)).execute()
    return None


# ─────────────────────────────────────────────
# Comments Moderation
# ─────────────────────────────────────────────

@router.get("/comments")
def list_all_comments(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, gt=0, le=100),
    is_approved: Optional[bool] = Query(None),
    current_user=Depends(get_current_admin),
):
    """
    List all comments with approval status. Admin only.
    """
    supabase = get_supabase()
    query = supabase.table("comments").select(
        "id, content, is_approved, is_edited, upvote_count, created_at, "
        "author:users(id, username, display_name, avatar_url), "
        "prompt:prompts(id, title)"
    )

    if is_approved is not None:
        query = query.eq("is_approved", is_approved)

    query = query.order("created_at", desc=True).range(skip, skip + limit - 1)
    response = query.execute()
    return response.data


@router.put("/comments/{comment_id}/approve")
def approve_comment(
    comment_id: UUID,
    is_approved: bool = Query(...),
    current_user=Depends(get_current_admin),
):
    """
    Approve or disapprove a comment. Admin only.
    """
    supabase = get_supabase()
    existing = supabase.table("comments").select("id").eq("id", str(comment_id)).execute()
    if not existing.data:
        raise HTTPException(status_code=404, detail="Comment not found")

    response = (
        supabase.table("comments")
        .update({"is_approved": is_approved})
        .eq("id", str(comment_id))
        .execute()
    )
    if not response.data:
        raise HTTPException(status_code=400, detail="Could not update comment")
    return response.data[0]


@router.delete("/comments/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
def admin_delete_comment(comment_id: UUID, current_user=Depends(get_current_admin)):
    """
    Delete a comment. Admin only.
    """
    supabase = get_supabase()
    existing = supabase.table("comments").select("id").eq("id", str(comment_id)).execute()
    if not existing.data:
        raise HTTPException(status_code=404, detail="Comment not found")

    supabase.table("comments").delete().eq("id", str(comment_id)).execute()
    return None


# ─────────────────────────────────────────────
# Reports Moderation
# ─────────────────────────────────────────────

@router.get("/reports")
def list_reports(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, gt=0, le=100),
    report_status: Optional[str] = Query(None, alias="status"),
    current_user=Depends(get_current_admin),
):
    """
    List all reports with details. Admin only.
    """
    supabase = get_supabase()
    query = supabase.table("reports").select(
        "id, reportable_type, reportable_id, reason, description, status, "
        "resolution_notes, resolved_at, created_at, "
        "reporter:users!reporter_id(id, username, display_name, avatar_url)"
    )

    if report_status:
        query = query.eq("status", report_status)

    query = query.order("created_at", desc=True).range(skip, skip + limit - 1)
    response = query.execute()
    return response.data


@router.put("/reports/{report_id}")
def update_report(
    report_id: UUID,
    report_status: str = Query(..., alias="status", description="reviewing, resolved, dismissed"),
    resolution_notes: Optional[str] = Query(None),
    current_user=Depends(get_current_admin),
):
    """
    Update report status. Admin only.
    """
    if report_status not in ("reviewing", "resolved", "dismissed"):
        raise HTTPException(status_code=400, detail="Invalid status")

    supabase = get_supabase()
    existing = supabase.table("reports").select("id").eq("id", str(report_id)).execute()
    if not existing.data:
        raise HTTPException(status_code=404, detail="Report not found")

    from datetime import datetime

    update_data = {
        "status": report_status,
        "reviewed_by": current_user["id"],
    }
    if resolution_notes:
        update_data["resolution_notes"] = resolution_notes
    if report_status in ("resolved", "dismissed"):
        update_data["resolved_at"] = datetime.utcnow().isoformat()

    response = (
        supabase.table("reports")
        .update(update_data)
        .eq("id", str(report_id))
        .execute()
    )
    if not response.data:
        raise HTTPException(status_code=400, detail="Could not update report")
    return response.data[0]


# ─────────────────────────────────────────────
# Tag Management
# ─────────────────────────────────────────────

@router.get("/tags")
def list_all_tags(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, gt=0, le=200),
    search: Optional[str] = Query(None),
    current_user=Depends(get_current_admin),
):
    """
    List all tags with usage counts. Admin only.
    """
    supabase = get_supabase()
    query = supabase.table("tags").select("id, name, slug, usage_count, created_at")

    if search:
        query = query.ilike("name", f"%{search}%")

    query = query.order("usage_count", desc=True).range(skip, skip + limit - 1)
    response = query.execute()
    return response.data


@router.delete("/tags/{tag_id}", status_code=status.HTTP_204_NO_CONTENT)
def admin_delete_tag(tag_id: UUID, current_user=Depends(get_current_admin)):
    """
    Delete a tag. Admin only.
    """
    supabase = get_supabase()
    existing = supabase.table("tags").select("id").eq("id", str(tag_id)).execute()
    if not existing.data:
        raise HTTPException(status_code=404, detail="Tag not found")

    supabase.table("tags").delete().eq("id", str(tag_id)).execute()
    return None
