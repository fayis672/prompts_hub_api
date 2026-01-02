import os
import sys
import random
import re
from dotenv import load_dotenv
from supabase import create_client, Client
from typing import List, Dict

# Apply to root path to find .env if run from scripts/
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()

url = os.environ.get("SUPABASE_URL", "").strip().strip("'").strip('"')
key = os.environ.get("SUPABASE_KEY", "").strip().strip("'").strip('"')

if not url or not key:
    print("Error: SUPABASE_URL or SUPABASE_KEY not set.")
    sys.exit(1)

try:
    supabase: Client = create_client(url, key)
except Exception as e:
    print(f"CRITICAL ERROR initializing client: {e}")
    sys.exit(1)

def step(msg):
    print(f"\n[STEP] {msg}")

def get_variable_type(var_name):
    if "count" in var_name or "number" in var_name:
        return "number"
    if "image" in var_name or "style" in var_name:
        return "text" # Could be select if we had options
    return "text"

def seed_prompt_variables_tags_outputs():
    step("Fetching existing prompts...")
    prompts_res = supabase.table("prompts").select("*").execute()
    prompts = prompts_res.data
    
    if not prompts:
        print("No prompts found.")
        return

    print(f"Found {len(prompts)} prompts.")

    # Fetch/Create some default tags
    default_tags = ["General", "Creative", "Utility", "Draft"]
    tag_map = {} # slug -> id
    
    step("Ensuring default tags exist...")
    for tag_name in default_tags:
        slug = tag_name.lower()
        res = supabase.table("tags").select("id").eq("slug", slug).execute()
        if res.data:
            tag_map[slug] = res.data[0]["id"]
        else:
            new_tag = supabase.table("tags").insert({"name": tag_name, "slug": slug}).execute()
            if new_tag.data:
                tag_map[slug] = new_tag.data[0]["id"]
                print(f"  Created tag: {tag_name}")

    for p in prompts:
        pid = p["id"]
        p_text = p.get("prompt_text", "")
        uid = p["user_id"]
        
        print(f"Processing prompt: {p.get('title', pid)}")

        # 1. Variables
        # Check if exists
        vars_res = supabase.table("prompt_variables").select("id").eq("prompt_id", pid).execute()
        if not vars_res.data:
            # Parse variables from {{variable_name}}
            found_vars = re.findall(r'\{\{([^}]+)\}\}', p_text)
            if found_vars:
                print(f"  Found variables in text: {found_vars}")
                new_vars = []
                for v in set(found_vars): # Unique
                    v_clean = v.strip()
                    new_vars.append({
                        "prompt_id": pid,
                        "variable_name": v_clean.replace("_", " ").title(),
                        "variable_key": v_clean,
                        "data_type": get_variable_type(v_clean),
                        "description": f"Variable for {v_clean}"
                    })
                if new_vars:
                    supabase.table("prompt_variables").insert(new_vars).execute()
                    print(f"  Inserted {len(new_vars)} variables.")
            else:
                 # Add a dummy variable if none found, just for demo? No, better not clutter if not needed.
                 # But task said "seed data". Let's add one if it's a "template" style prompt.
                 pass

        # 2. Tags
        tags_res = supabase.table("prompt_tags").select("id").eq("prompt_id", pid).execute()
        if not tags_res.data:
            # Assign random tag
            if tag_map:
                t_slug = random.choice(list(tag_map.keys()))
                t_id = tag_map[t_slug]
                supabase.table("prompt_tags").insert({"prompt_id": pid, "tag_id": t_id}).execute()
                print(f"  Assigned tag: {t_slug}")

        # 3. Outputs
        out_res = supabase.table("prompt_outputs").select("id").eq("prompt_id", pid).execute()
        if not out_res.data:
            # Add a sample output
            # Check prompt type
            p_type = p.get("prompt_type", "text_generation")
            
            output_data = {
                "prompt_id": pid,
                "user_id": uid,
                "title": "Sample Output",
                "is_approved": True
            }
            
            if p_type == "image_generation":
                output_data["output_type"] = "image"
                output_data["output_url"] = "https://placehold.co/600x400?text=AI+Generated+Image"
            else:
                 output_data["output_type"] = "text"
                 output_data["output_text"] = "This is a sample generated output for the prompt. It demonstrates what the result might look like."
            
            supabase.table("prompt_outputs").insert(output_data).execute()
            print(f"  Inserted sample output.")

    step("Seeding existing prompts complete.")

if __name__ == "__main__":
    seed_prompt_variables_tags_outputs()
