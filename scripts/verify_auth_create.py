
import os
import sys
import requests
import random
import string
from dotenv import load_dotenv
from supabase import create_client

# Add parent dir to path to find app if needed, but we use requests for API
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

load_dotenv()

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")

if not url or not key:
    print("Error: Env vars missing")
    sys.exit(1)

supabase = create_client(url, key)

def random_string(length=10):
    return ''.join(random.choices(string.ascii_lowercase, k=length))

def verify():
    # 1. Sign up a new user in Supabase Auth
    email = f"test_{random_string()}@example.com"
    password = "password123"
    username = f"user_{random_string()}"
    
    print(f"1. Signing up {email}...")
    try:
        res = supabase.auth.sign_up({
            "email": email,
            "password": password,
        })
        
        session = res.session
        if not session:
            # Try login if signup didn't return session (auto-confirm might be off, checking login)
            print("   No session from signup, trying login...")
            res = supabase.auth.sign_in_with_password({"email": email, "password": password})
            session = res.session
            
        if not session:
            print("CRITICAL: Could not get a session. Cannot verify token auth.")
            return

        token = session.access_token
        user_id = res.user.id
        print(f"   Got token for ID: {user_id}")

        # 2. Call our API to create the profile
        api_url = "http://127.0.0.1:8000/api/v1/users/"
        headers = {"Authorization": f"Bearer {token}"}
        payload = {
            "username": username,
            "display_name": "Verified User",
            # No ID, No Role, No Email in payload
        }
        
        print(f"2. Calling API {api_url}...")
        resp = requests.post(api_url, json=payload, headers=headers)
        
        if resp.status_code == 200:
            data = resp.json()
            print("   SUCCESS: User created via API!")
            print(f"   Response ID: {data.get('id')}")
            print(f"   Response Email: {data.get('email')}")
            print(f"   Response Role: {data.get('role')}")
            
            if data['id'] == user_id and data['email'] == email and data['role'] == 'user':
                print("   VERIFICATION PASSED: ID and Email match token, Role is default.")
            else:
                print("   VERIFICATION FAILED: Data mismatch.")
        else:
            print(f"   FAILED: Status {resp.status_code}")
            print(f"   Body: {resp.text}")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    verify()
