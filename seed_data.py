import os
import sys
import random
import time
from typing import List, Dict
from dotenv import load_dotenv
from supabase import create_client, Client
from datetime import datetime

# Load environment variables
load_dotenv()

# Setup Supabase client
# Setup Supabase client
url = os.environ.get("SUPABASE_URL", "").strip().strip("'").strip('"')
key = os.environ.get("SUPABASE_KEY", "").strip().strip("'").strip('"')

if not url or not key:
    print("Error: SUPABASE_URL or SUPABASE_KEY not set.")
    sys.exit(1)

print(f"DEBUG: URL being used: '{url}'")
print(f"DEBUG: Key being used (masked): {key[:5]}...{key[-5:] if len(key)>5 else ''}")
print(f"DEBUG: Key Length: {len(key)}")

if key.startswith("sb_"):
    print("\n[CRITICAL WARNING] The SUPABASE_KEY starts with 'sb_'.")
    print("This looks like a Database Secret or internal token, NOT the 'anon' public API key.")
    print("The 'anon' key is a JWT and typically starts with 'ey...'.")
    print("Please check your Supabase Dashboard -> Settings -> API -> Project API keys -> anon/public.\n")

try:
    supabase: Client = create_client(url, key)
except Exception as e:
    print(f"CRITICAL ERROR initializing client: {e}")
    sys.exit(1)


# Helper to print steps
def step(msg):
    print(f"\n[STEP] {msg}")

# --- Data Definitions ---

CATEGORIES = [
    {"name": "Writing", "slug": "writing", "description": "Prompts for creative writing and storytelling.", "icon_url": "https://example.com/icons/writing.png", "color_code": "#FF5733"},
    {"name": "Coding", "slug": "coding", "description": "Code generation and debugging prompts.", "icon_url": "https://example.com/icons/coding.png", "color_code": "#33FF57"},
    {"name": "Art", "slug": "art", "description": "AI Art generation prompts (Midjourney, DALL-E).", "icon_url": "https://example.com/icons/art.png", "color_code": "#3357FF"},
    {"name": "Business", "slug": "business", "description": "Professional and business related prompts.", "icon_url": "https://example.com/icons/business.png", "color_code": "#F1C40F"},
    {"name": "Education", "slug": "education", "description": "Learning and educational prompts.", "icon_url": "https://example.com/icons/education.png", "color_code": "#9B59B6"},
]

TAGS = [
    {"name": "GPT-4", "slug": "gpt-4"},
    {"name": "Python", "slug": "python"},
    {"name": "Javascript", "slug": "javascript"},
    {"name": "Fantasy", "slug": "fantasy"},
    {"name": "Sci-Fi", "slug": "sci-fi"},
    {"name": "Marketing", "slug": "marketing"},
    {"name": "SEO", "slug": "seo"},
    {"name": "Midjourney v5", "slug": "midjourney-v5"},
]

USERS = [
    {"email": "alice@testdomain.com", "password": "password123", "username": "alice", "display_name": "Alice Wonderland"},
    {"email": "bob@testdomain.com", "password": "password123", "username": "bobbuilder", "display_name": "Bob Builder"},
    {"email": "charlie@testdomain.com", "password": "password123", "username": "charlie", "display_name": "Charlie Chaplin"},
    # Admin user if you want to test RBAC (Role usually needs manual DB update or admin endpoint)
    {"email": "admin@testdomain.com", "password": "password123", "username": "admin_user", "display_name": "Admin User"},  
]

PROMPTS = [
    {
        "title": "Creative Story Generator",
        "slug": "creative-story-generator",
        "prompt_text": "Write a short story about a time traveler who gets stuck in 1999.",
        "description": "A fun prompt for creative writing.",
        "prompt_type": "text_generation"
    },
    {
        "title": "Python API Boilerplate",
        "slug": "python-api-boilerplate",
        "prompt_text": "Generate a FastAPI boilerplate with Supabase auth.",
        "description": "Quick start for Python backends.",
        "prompt_type": "code_generation"
    },
    {
        "title": "Cyberpunk Cityscape",
        "slug": "cyberpunk-cityscape",
        "prompt_text": "/imagine prompt: futuristic cyberpunk city with neon lights, rain, high detail --v 5",
        "description": "Midjourney prompt for cool cities.",
        "prompt_type": "image_generation"
    },
    {
        "title": "SEO Blog Post Writer",
        "slug": "seo-blog-post-writer",
        "prompt_text": "Write an SEO optimized blog post about the benefits of drinking water.",
        "description": "Rank high on Google with this prompt.",
        "prompt_type": "text_generation"


    }
]

# --- Seeding Logic ---

def seed():
    # 1. Categories (Admin usually creates these, but we'll insert directly if permitted, or just skip auth for public tables if RLS allows anon insert - unlikely. We'll Sign Up an admin first).
    
    # We will sign up users and keep their session tokens
    user_sessions = {} # email -> session
    
    step("Creating Users...")
    for u in USERS:
        try:
            print(f"  Registering {u['email']}...")
            res = supabase.auth.sign_up({
                "email": u["email"],
                "password": u["password"],
                "options": {
                    "data": {
                        "username": u["username"],
                        "display_name": u["display_name"]
                    }
                }
            })
            if res.user:
                # If auto-confirm is enabled, we might get a session immediately.
                # If not, we can't really proceed easily without manual confirmation or using a service role key.
                # Assuming auto-confirm IS enabled for development.
                if res.session:
                    user_sessions[u['email']] = res.session
                    
                    # Ensure public.users entry exists (Sync Auth -> Public)
                    user_id = res.user.id
                    try:
                        supabase.table("users").upsert({
                            "id": user_id,
                            "email": u["email"],
                            "username": u["username"],
                            "display_name": u["display_name"],
                            "password_hash": "managed_by_supabase_auth",
                            "role": "admin" if "admin" in u["username"] else "user"
                        }).execute()
                        print(f"  Synced public profile for {u['email']}")
                    except Exception as e_profile:
                        print(f"  Could not sync profile for {u['email']}: {e_profile}")
                        
                else:
                    print(f"  WARNING: Created {u['email']} but no session returned. Is email confirmation on?")
                    # Try signing in immediately just in case
                    try:
                         # Wait a bit
                         time.sleep(1)
                         res_login = supabase.auth.sign_in_with_password({"email": u["email"], "password": u["password"]})
                         if res_login.session:
                             user_sessions[u['email']] = res_login.session
                             
                             # Ensure public.users entry exists
                             user_id = res_login.user.id
                             try:
                                supabase.table("users").upsert({
                                    "id": user_id,
                                    "email": u["email"],
                                    "username": u["username"],
                                    "display_name": u["display_name"],
                                    "role": "admin" if "admin" in u["username"] else "user"
                                }).execute()
                                print(f"  Synced public profile for {u['email']}")
                             except Exception as e_profile:
                                print(f"  Could not sync profile for {u['email']}: {e_profile}")

                    except Exception as e:
                        print(f"  Could not sign in {u['email']}: {e}")
            
        except Exception as e:
            # User might already exist, try login
            print(f"  User {u['email']} might already exist: {e}")
            try:
                 print(f"  Attempting login for {u['email']}...")
                 res_login = supabase.auth.sign_in_with_password({"email": u["email"], "password": u["password"]})
                 if res_login.session:
                     user_sessions[u['email']] = res_login.session
                     
                     # Sync Profile
                     user_id = res_login.user.id
                     try:
                        supabase.table("users").upsert({
                            "id": user_id,
                            "email": u["email"],
                            "username": u["username"],
                            "display_name": u["display_name"],
                            "password_hash": "managed_by_supabase_auth",
                            "role": "admin" if "admin" in u["username"] else "user"
                        }).execute()
                        print(f"  Synced/Restored public profile for {u['email']}")
                     except Exception as e_profile:
                        print(f"  Could not sync profile for {u['email']}: {e_profile}")
                 else:
                     print(f"  Login successful but no session for {u['email']}")

            except Exception as e_login:
                print(f"  Login failed for {u['email']}: {e_login}")

    if not user_sessions:
        print("CRITICAL: No acting users available. Cannot seed restricted tables.")
        return

    # Pick a random user to act as admin/creator for shared resources
    actor_email = list(user_sessions.keys())[0]
    actor_session = user_sessions[actor_email]
    
    # We need a client that acts as this user
    # supabase.auth.set_session(actor_session.access_token, actor_session.refresh_token) # This sets global session?
    # Better to create a new client or just set headers if possible. 
    # supabase-py doesn't easily support multiple active user clients without re-init.
    # We will just set the session on the global client for now, or use postgrest directly.
    
    # Let's try setting DB session
    supabase.postgrest.auth(actor_session.access_token)

    step("Creating Categories...")
    for cat in CATEGORIES:
        try:
            # Check exist
            existing = supabase.table("categories").select("id").eq("slug", cat["slug"]).execute()
            if not existing.data:
                supabase.table("categories").insert(cat).execute()
                print(f"  Inserted category: {cat['name']}")
            else:
                print(f"  Category exists: {cat['name']}")
        except Exception as e:
            print(f"  Error creating category {cat['name']}: {e}")

    step("Creating Tags...")
    for tag in TAGS:
        try:
            existing = supabase.table("tags").select("id").eq("slug", tag["slug"]).execute()
            if not existing.data:
                supabase.table("tags").insert(tag).execute()
                print(f"  Inserted tag: {tag['name']}")
            else:
                print(f"  Tag exists: {tag['name']}")
        except Exception as e:
            print(f"  Error creating tag {tag['name']}: {e}")

    step("Creating Prompts...")
    # Get IDs for foreign keys using the acting user
    cat_ids = [c['id'] for c in supabase.table("categories").select("id").execute().data]
    tag_ids = [t['id'] for t in supabase.table("tags").select("id").execute().data]
    
    # For prompts, iterate users to simulate content density
    for email, session in user_sessions.items():
        # Switch auth context
        supabase.postgrest.auth(session.access_token)
        user = supabase.auth.get_user(session.access_token).user
        
        # Create 1-2 prompts per user
        for i in range(2):
            p = random.choice(PROMPTS).copy()
            # Randomize slug to allow duplicates
            p["slug"] = f"{p['slug']}-{random.randint(1000, 9999)}"
            p["user_id"] = user.id
            
            # Random category
            if cat_ids:
                p["category_id"] = random.choice(cat_ids)
                
            try:
                res = supabase.table("prompts").insert(p).execute()
                if res.data:
                    prompt_id = res.data[0]['id']
                    print(f"  User {email} created prompt: {p['title']}")
                    
                    # Add some tags
                    if tag_ids:
                        for _ in range(random.randint(1, 3)):
                             t_id = random.choice(tag_ids)
                             try:
                                 supabase.table("prompt_tags").insert({"prompt_id": prompt_id, "tag_id": t_id}).execute()
                             except: pass # Ignore duplicates
                             
                    # Add some ratings/comments from OTHER users
                    other_emails = [e for e in user_sessions.keys() if e != email]
                    if other_emails:
                        commenter_email = random.choice(other_emails)
                        commenter_session = user_sessions[commenter_email]
                        
                        # Use a separate client or headers for commenter? 
                        # Changing auth on the fly in the same client loop:
                        print("hello")
                        client_commenter = create_client(url, key)
                        client_commenter.postgrest.auth(commenter_session.access_token)
                        
                        # Comment
                        client_commenter.table("comments").insert({
                            "content": "Great prompt! strict and useful.",
                            "prompt_id": prompt_id,
                            "user_id": client_commenter.auth.get_user(commenter_session.access_token).user.id
                        }).execute()
                        
                        # Rate
                        client_commenter.table("prompt_ratings").insert({
                            "rating": random.randint(3, 5),
                            "prompt_id": prompt_id,
                            "user_id": client_commenter.auth.get_user(commenter_session.access_token).user.id
                        }).execute()
                        print(f"    -> Commented/Rated by {commenter_email}")
                        
            except Exception as e:
                print(f"  Error creating prompt: {e}")

    step("Seeding Complete!")

if __name__ == "__main__":
    seed()
