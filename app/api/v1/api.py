from fastapi import APIRouter
from app.api.v1.endpoints import prompts, users, categories, tags, comments, files

api_router = APIRouter()

@api_router.get("/health", tags=["health"])
async def health_check():
    return {"status": "ok"}

api_router.include_router(prompts.router, prefix="/prompts", tags=["prompts"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(categories.router, prefix="/categories", tags=["categories"])
api_router.include_router(tags.router, prefix="/tags", tags=["tags"])
api_router.include_router(comments.router, prefix="/comments", tags=["comments"])
api_router.include_router(files.router, prefix="/files", tags=["files"])




