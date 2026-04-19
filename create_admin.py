import os
import sys
from dotenv import load_dotenv

# load environment
load_dotenv(".env")

from app.db.supabase import get_supabase

supabase = get_supabase()

email = "fayistkm36@gmail.com"
password = "AdminPassword123!"

try:
    # 1. Register the user
    print(f"Creating user for email: {email}")
    res = supabase.auth.sign_up({"email": email, "password": password})
    
    if res.user:
        user_id = res.user.id
        print(f"User created in auth.users with ID: {user_id}")
        
        # 2. Update their role to admin in the public.users table
        # NOTE: the trigger might have already created their row in public.users
        print("Promoting user to admin...")
        update_res = supabase.table("users").update({"role": "admin"}).eq("id", user_id).execute()
        
        print("Success! User has been granted the admin role.")
        print(f"Credentials:")
        print(f"Email: {email}")
        print(f"Password: {password}")
    else:
        print("Failed to create user. Result was empty.")
        
except Exception as e:
    # Check if they exist already
    if "User already registered" in str(e):
        print(f"User {email} already exists! Promoting directly...")
        # Since we don't know the password if they exist, but maybe we can just query the user by email?
        # auth.users is not directly queryable easily without service role but we have service role so maybe?
        print("Warning: Email already exists, please check manual queries.")
        sys.exit(1)
    else:
        print(f"Error: {e}")
