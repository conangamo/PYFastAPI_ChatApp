"""
File utility functions
"""
import os
import uuid
import aiofiles
from pathlib import Path
from typing import Tuple, Optional
from PIL import Image
import magic

from ..schemas.file import FileCategory


# Configuration
UPLOAD_DIR = Path("/app/uploads")
MAX_FILE_SIZE = {
    FileCategory.IMAGE: 10 * 1024 * 1024,      # 10 MB
    FileCategory.DOCUMENT: 20 * 1024 * 1024,   # 20 MB
    FileCategory.AUDIO: 50 * 1024 * 1024,      # 50 MB
    FileCategory.VIDEO: 100 * 1024 * 1024,     # 100 MB
    FileCategory.OTHER: 50 * 1024 * 1024,      # 50 MB
}

ALLOWED_MIME_TYPES = {
    FileCategory.IMAGE: [
        "image/jpeg", "image/png", "image/gif", "image/webp", "image/bmp"
    ],
    FileCategory.DOCUMENT: [
        "application/pdf",
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.ms-excel",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "text/plain",
        "text/csv"
    ],
    FileCategory.AUDIO: [
        "audio/mpeg", "audio/mp3", "audio/wav", "audio/ogg", "audio/webm"
    ],
    FileCategory.VIDEO: [
        "video/mp4", "video/mpeg", "video/quicktime", "video/x-msvideo", "video/webm"
    ],
    FileCategory.OTHER: [
        "application/zip",
        "application/x-rar-compressed",
        "application/x-7z-compressed"
    ]
}

ALLOWED_EXTENSIONS = {
    FileCategory.IMAGE: [".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"],
    FileCategory.DOCUMENT: [".pdf", ".doc", ".docx", ".xls", ".xlsx", ".txt", ".csv"],
    FileCategory.AUDIO: [".mp3", ".wav", ".ogg", ".webm"],
    FileCategory.VIDEO: [".mp4", ".mpeg", ".mov", ".avi", ".webm"],
    FileCategory.OTHER: [".zip", ".rar", ".7z"]
}


def get_file_category(mime_type: str) -> Optional[FileCategory]:
    """
    Determine file category from MIME type
    
    Args:
        mime_type: MIME type string
        
    Returns:
        FileCategory or None
    """
    for category, mime_types in ALLOWED_MIME_TYPES.items():
        if mime_type in mime_types:
            return category
    return None


def validate_file_type(filename: str, mime_type: str) -> Tuple[bool, Optional[str], Optional[FileCategory]]:
    """
    Validate file type based on extension and MIME type
    
    Args:
        filename: Original filename
        mime_type: MIME type
        
    Returns:
        Tuple of (is_valid, error_message, category)
    """
    # Get file extension
    ext = Path(filename).suffix.lower()
    
    # Check if extension is allowed
    category = None
    for cat, extensions in ALLOWED_EXTENSIONS.items():
        if ext in extensions:
            category = cat
            break
    
    if not category:
        return False, f"File extension {ext} not allowed", None
    
    # Check if MIME type matches category
    if mime_type not in ALLOWED_MIME_TYPES[category]:
        return False, f"MIME type {mime_type} not allowed for {category.value} files", None
    
    return True, None, category


def validate_file_size(file_size: int, category: FileCategory) -> Tuple[bool, Optional[str]]:
    """
    Validate file size
    
    Args:
        file_size: File size in bytes
        category: File category
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    max_size = MAX_FILE_SIZE.get(category, MAX_FILE_SIZE[FileCategory.OTHER])
    
    if file_size > max_size:
        max_mb = max_size / (1024 * 1024)
        return False, f"File size exceeds maximum {max_mb}MB for {category.value} files"
    
    return True, None


def generate_unique_filename(original_filename: str) -> str:
    """
    Generate unique filename with UUID prefix
    
    Args:
        original_filename: Original filename
        
    Returns:
        Unique filename
    """
    ext = Path(original_filename).suffix.lower()
    unique_id = uuid.uuid4().hex[:12]
    # Sanitize original filename
    safe_name = Path(original_filename).stem[:50]  # Limit length
    safe_name = "".join(c for c in safe_name if c.isalnum() or c in "._- ")
    
    return f"{unique_id}_{safe_name}{ext}"


def get_storage_path(category: FileCategory, filename: str) -> Path:
    """
    Get full storage path for file
    
    Args:
        category: File category
        filename: Filename
        
    Returns:
        Full path
    """
    category_dir = UPLOAD_DIR / (category.value + "s")  # images, documents, etc.
    category_dir.mkdir(parents=True, exist_ok=True)
    return category_dir / filename


async def save_upload_file(upload_file, dest_path: Path) -> int:
    """
    Save uploaded file to destination
    
    Args:
        upload_file: FastAPI UploadFile
        dest_path: Destination path
        
    Returns:
        File size in bytes
    """
    file_size = 0
    async with aiofiles.open(dest_path, 'wb') as f:
        while chunk := await upload_file.read(1024 * 1024):  # Read 1MB at a time
            await f.write(chunk)
            file_size += len(chunk)
    
    return file_size


def generate_thumbnail(image_path: Path, max_size=(300, 300)) -> Optional[Path]:
    """
    Generate thumbnail for image
    
    Args:
        image_path: Path to original image
        max_size: Maximum thumbnail size (width, height)
        
    Returns:
        Path to thumbnail or None if failed
    """
    try:
        with Image.open(image_path) as img:
            # Convert RGBA to RGB if necessary
            if img.mode == 'RGBA':
                rgb_img = Image.new('RGB', img.size, (255, 255, 255))
                rgb_img.paste(img, mask=img.split()[3])
                img = rgb_img
            
            # Generate thumbnail
            img.thumbnail(max_size, Image.Resampling.LANCZOS)
            
            # Create thumbnail filename
            thumb_filename = image_path.stem + "_thumb" + image_path.suffix
            thumb_path = image_path.parent / thumb_filename
            
            # Save thumbnail
            img.save(thumb_path, quality=85, optimize=True)
            
            return thumb_path
    except Exception as e:
        print(f"Error generating thumbnail: {e}")
        return None


def detect_mime_type(file_path: Path) -> str:
    """
    Detect MIME type of file using python-magic
    
    Args:
        file_path: Path to file
        
    Returns:
        MIME type string
    """
    try:
        mime = magic.Magic(mime=True)
        return mime.from_file(str(file_path))
    except:
        # Fallback to extension-based detection
        ext = file_path.suffix.lower()
        mime_map = {
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.gif': 'image/gif',
            '.pdf': 'application/pdf',
            '.txt': 'text/plain',
            '.mp3': 'audio/mpeg',
            '.mp4': 'video/mp4',
        }
        return mime_map.get(ext, 'application/octet-stream')


def init_upload_directories():
    """Initialize upload directories"""
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    
    for category in FileCategory:
        category_dir = UPLOAD_DIR / (category.value + "s")
        category_dir.mkdir(parents=True, exist_ok=True)
    
    # Create thumbnails directory
    thumbnails_dir = UPLOAD_DIR / "thumbnails"
    thumbnails_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"✅ Upload directories initialized at {UPLOAD_DIR}")

