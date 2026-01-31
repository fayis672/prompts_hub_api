
import os
import sys
import requests
import random
import string
from dotenv import load_dotenv
from supabase import create_client, Client

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

load_dotenv()

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")

if not url or not key:
    print("Error: Env vars missing")
    sys.exit(1)

supabase: Client = create_client(url, key)

def random_string(length=10):
    return ''.join(random.choices(string.ascii_lowercase, k=length))

def verify():
    # 1. Sign up a new user (to act as user who might not have a profile yet, or does)
    email = f"test_check_{random_string()}@example.com"
    password = "password123"
    username = f"user_{random_string()}"
    
    print(f"1. Signing up {email}...")
    try:
        res = supabase.auth.sign_up({"email": email, "password": password})
        session = res.session
        
        if not session:
             print("   No session, trying login...")
             res = supabase.auth.sign_in_with_password({"email": email, "password": password})
             session = res.session
             
        if not session:
            print("CRITICAL: No session.")
            return

        token = session.access_token
        print(f"   Got token for ID: {res.user.id}")

        # 2. Check Exists (Should be FALSE initially)
        api_url = "http://127.0.0.1:8000/api/v1/users/check-exists"
        headers = {"Authorization": f"Bearer {token}"}
        
        print(f"2. Checking existence (Expect FALSE)...")
        resp = requests.get(api_url, headers=headers)
        if resp.status_code == 200:
            print(f"   Response: {resp.json()}")
            if resp.json()['exists'] == False:
                print("   PASSED: User does not exist yet.")
            else:
                print("   FAILED: Says user exists (but shouldn't).")
        else:
            print(f"   FAILED: Status {resp.status_code}, {resp.text}")

        # 3. Create Profile
        print(f"3. Creating profile...")
        create_url = "http://127.0.0.1:8000/api/v1/users/"
        resp_create = requests.post(create_url, json={"username": username, "display_name": "Test"}, headers=headers)
        if resp_create.status_code == 200:
            print("   Profile created.")
        else:
            print(f"   FAILED to create profile: {resp_create.text}")
            return
            
        # 4. Check Exists (Should be TRUE now)
        print(f"4. Checking existence again (Expect TRUE)...")
        resp = requests.get(api_url, headers=headers)
        if resp.status_code == 200:
            print(f"   Response: {resp.json()}")
            if resp.json()['exists'] == True:
                print("   PASSED: User exists now.")
            else:
                print("   FAILED: Says user does not exist (but should).")
        else:
             print(f"   FAILED: Status {resp.status_code}, {resp.text}")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    verify()
