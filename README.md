# Prompts Hub API Backend

The central REST API serving both the Prompts Hub Client and the Standalone Admin Portal. Built with Python 3, FastAPI, and integrated directly atop the physical Supabase PostgreSQL Database.

## Overview
This backend acts as the secure intermediary layer to execute complex aggregation, recommendation logic, metrics logging, and database triggers that would be unsafe or inefficient to expose natively to the browser via RLS.

## Core Capabilities
- **FastAPI Core:** Extremely fast async endpoint processing and automatic OpenAPI/Swagger `docs` generation.
- **Session Decoding:** Verifies Supabase Bearer Auth JWTs on protected routes using dependencies.
- **Recommendation Engine:** Calculates advanced sorting pipelines for 'Trending' and 'Most Liked' prompts based on bookmark tracking arrays and viewership velocity.
- **Administration Actions:** Handles elevated user permission modifications and category generation.

## Environment Configuration
Create an `.env` file in this directory with the following configuration:
```env
SUPABASE_URL=https://vxlxlbffjlryuanijbec.supabase.co
SUPABASE_KEY=<your_supabase_service_role_key>
ENVIRONMENT=development
```
*Note: The API requires the Service Role Key to bypass strict row level security when serving aggregated metrics.*

## Start the API
Ensure a virtual environment is active:
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Start natively:
uvicorn app.main:app --reload --port 8000
```
Or start all applications simultaneously leveraging the `run_project.sh` root bash script!
