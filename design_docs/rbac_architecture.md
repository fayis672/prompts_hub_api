# Role-Based Access Control (RBAC) Design

## Overview
The Prompts Hub API implements a robust Application-Level RBAC system. This design ensures that users can only access resources they are authorized for, while providing Administrators with elevated privileges to manage the platform.

## Architecture

### 1. Identity & Authentication
- **Provider**: Supabase Auth (JWT).
- **Process**:
    1.  Client logs in and receives a JWT.
    2.  Client sends JWT in `Authorization` header.
    3.  `app/core/security.py` verifies the JWT with Supabase.

### 2. Role Storage
- **Location**: `public.users` table.
- **Field**: `role` (Enum: `guest`, `user`, `admin`).
- **Mechanism**: After verifying the JWT, the API fetches the corresponding user record from the `users` table to retrieve their assigned role.

### 3. Authorization Levels

#### Level 1: Public Access
- **Endpoints**: Health checks, Public Prompt listings (future).
- **Requirement**: No mechanism strictly required, but usually basic valid token for rate limiting.

#### Level 2: Authenticated User (Self)
- **Endpoints**: `POST /prompts`, `PUT /users/me`, `GET /users/me`.
- **Requirement**: Valid JWT.
- **Logic**: Users can unlimitedly create resources. Updates/Deletes are restricted to resources where `user_id` matches the current user's ID.

#### Level 3: Administrator
- **Endpoints**: `GET /users/` (List all), `PUT /users/{id}` (Role updates).
- **Requirement**: Valid JWT + `role == 'admin'`.
- **Logic**: 
    -   Global Read access.
    -   Global Write/Delete access (Can override ownership checks).

## Security Implementation
- **Dependency Injection**:
    -   `get_current_user`: Returns user profile. Used for identifying the requester.
    -   `get_current_admin`: Enforces `role == 'admin'`. Used for protecting sensitive routes.
- **Endpoint Logic**:
    -   In `update_prompt` and `delete_prompt`, we explicitly check:
        ```python
        if resource.owner_id != current_user.id and current_user.role != 'admin':
            raise 403 Forbidden
        ```

## Trade-offs vs Database RLS
- **Current Approach (Application Level)**: 
    -   **Pros**: Easier to debug, explicit logic in Python, simpler for complex business rules (e.g., "Editor" role can update but not delete).
    -   **Cons**: If a developer forgets the check in a new endpoint, data is exposed.
- **Database RLS (Row Level Security)**:
    -   **Pros**: Secure by default even if API fails.
    -   **Cons**: Logic split between Python and SQL, harder to unit test/debug.

**Verdict**: For a FastAPI backend where all access is mediated by the API (no direct DB access for clients), the current Application-Level RBAC is standard, secure, and maintainable.
