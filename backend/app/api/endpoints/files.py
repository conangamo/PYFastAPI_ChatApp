from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from pathlib import Path
import os

from ...database import get_db
from ...models.user import User
from ...core.deps import get_current_active_user
from ...core.file_utils import (
    validate_file_type,
    validate_file_size,
    generate_unique_filename,
    get_storage_path,
    save_upload_file,
    generate_thumbnail,
    detect_mime_type,
    FileCategory
)
from ...schemas.file import FileUploadResponse, FileValidationError

router = APIRouter()


@router.post("/upload", response_model=FileUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_file(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    content_type = file.content_type or "application/octet-stream"
    
    is_valid, error_msg, category = validate_file_type(file.filename, content_type)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_msg
        )
    
    unique_filename = generate_unique_filename(file.filename)
    storage_path = get_storage_path(category, unique_filename)
    
    # Save file
    try:
        file_size = await save_upload_file(file, storage_path)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save file: {str(e)}"
        )
    
    is_valid_size, size_error = validate_file_size(file_size, category)
    if not is_valid_size:
        storage_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=size_error
        )
    
    actual_mime = detect_mime_type(storage_path)
    file_url = f"/api/files/download/{category.value}s/{unique_filename}"
    
    thumbnail_url = None
    if category == FileCategory.IMAGE:
        thumb_path = generate_thumbnail(storage_path)
        if thumb_path:
            thumbnail_url = f"/api/files/download/{category.value}s/{thumb_path.name}"
    
    return FileUploadResponse(
        file_url=file_url,
        file_name=file.filename,
        file_type=actual_mime,
        file_size=file_size,
        file_category=category,
        thumbnail_url=thumbnail_url
    )


@router.get("/download/{category}/{filename}")
async def download_file(
    category: str,
    filename: str
):
    """
    Download a file
    
    - **category**: File category directory (images, documents, audios, videos, others)
    - **filename**: Filename to download
    
    **Returns:**
    File content with appropriate Content-Type header
    """
    # Security: Prevent path traversal
    if ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid filename"
        )
    
    # Construct file path
    file_path = Path(f"/app/uploads/{category}/{filename}")
    
    # Check if file exists
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )
    
    # Detect MIME type
    mime_type = detect_mime_type(file_path)
    
    # Return file
    return FileResponse(
        path=file_path,
        media_type=mime_type,
        filename=filename
    )


@router.delete("/delete/{category}/{filename}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_file(
    category: str,
    filename: str,
    current_user: User = Depends(get_current_active_user)
):
    """
    Delete a file
    
    - **category**: File category directory
    - **filename**: Filename to delete
    
    **Note**: Only admins or file owners can delete files (for now, any authenticated user can delete)
    """
    # Security: Prevent path traversal
    if ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid filename"
        )
    
    # Construct file path
    file_path = Path(f"/app/uploads/{category}/{filename}")
    
    # Check if file exists
    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )
    
    # Delete file
    try:
        file_path.unlink()
        
        # Also delete thumbnail if it's an image
        if category == "images":
            thumb_name = filename.replace(".", "_thumb.")
            thumb_path = file_path.parent / thumb_name
            thumb_path.unlink(missing_ok=True)
        
        return None
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete file: {str(e)}"
        )


@router.get("/stats")
async def get_upload_stats(
    current_user: User = Depends(get_current_active_user)
):
    """
    Get upload statistics
    
    Returns count and total size of uploaded files by category
    """
    from pathlib import Path
    
    stats = {}
    upload_dir = Path("/app/uploads")
    
    categories = ["images", "documents", "audios", "videos", "others"]
    
    for cat in categories:
        cat_dir = upload_dir / cat
        if cat_dir.exists():
            files = list(cat_dir.glob("*"))
            # Exclude thumbnails
            files = [f for f in files if "_thumb" not in f.name]
            
            total_size = sum(f.stat().st_size for f in files if f.is_file())
            
            stats[cat] = {
                "count": len(files),
                "total_size_bytes": total_size,
                "total_size_mb": round(total_size / (1024 * 1024), 2)
            }
    
    return {
        "categories": stats,
        "total_files": sum(s["count"] for s in stats.values()),
        "total_size_mb": sum(s["total_size_mb"] for s in stats.values())
    }

