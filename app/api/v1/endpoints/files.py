from fastapi import APIRouter, UploadFile, File, HTTPException
from app.db.supabase import get_supabase
from app.core.config import settings
import uuid
import mimetypes

router = APIRouter()

@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """
    Upload a file to Supabase storage and return the public URL.
    """
    supabase = get_supabase()
    bucket_name = settings.SUPABASE_STORAGE_BUCKET

    # Generate a unique filename
    file_ext = mimetypes.guess_extension(file.content_type) or ""
    if not file_ext and file.filename:
         import os
         _, file_ext = os.path.splitext(file.filename)
    
    file_name = f"{uuid.uuid4()}{file_ext}"
    
    try:
        file_content = await file.read()
        
        # Upload file to Supabase Storage
        res = supabase.storage.from_(bucket_name).upload(
            path=file_name,
            file=file_content,
            file_options={"content-type": file.content_type}
        )
        
        # Get public URL
        public_url_res = supabase.storage.from_(bucket_name).get_public_url(file_name)
        
        return {"url": public_url_res}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
