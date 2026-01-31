from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.db.supabase import get_supabase

security = HTTPBearer()

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    Verifies the JWT token using Supabase's client (or you can do local validation).
    For now, this is a placeholder that passes the token to Supabase to get the user.
    """
    token = credentials.credentials
    supabase = get_supabase()
    
    try:
        auth_response = supabase.auth.get_user(token)
        if not auth_response or not auth_response.user:
             raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        user_id = auth_response.user.id
        
        # Fetch profile from public.users to get role and other details
        # We use .single() because we expect one record
        profile_response = supabase.table("users").select("*").eq("id", user_id).execute()
        
        if not profile_response.data:
            # If user exists in Auth but not in public.users, this is an edge case.
            # You might want to auto-create it or raise an error.
            # For strictness, we'll raise 401/403 or just 404.
             raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User profile not found",
            )
            
        return profile_response.data[0] # Return the dictionary from the DB
        
    except Exception as e:
        # Catch specific supabase errors if possible, or general exceptions
        print(f"Auth specific error: {e}") # Simple logging
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

async def get_current_auth_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    Verifies the JWT token using Supabase's client and returns the Auth User object.
    Does NOT check the public.users table.
    """
    token = credentials.credentials
    supabase = get_supabase()
    
    try:
        auth_response = supabase.auth.get_user(token)
        if not auth_response or not auth_response.user:
             raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return auth_response.user
        
    except Exception as e:
        print(f"Auth specific error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

def get_current_admin(current_user: dict = Depends(get_current_user)):
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user doesn't have enough privileges"
        )
    return current_user

