"""
File upload/download schemas
"""
from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum


class FileCategory(str, Enum):
    """File category enum"""
    IMAGE = "image"
    DOCUMENT = "document"
    AUDIO = "audio"
    VIDEO = "video"
    OTHER = "other"


class FileUploadResponse(BaseModel):
    """Response after successful file upload"""
    file_url: str = Field(..., description="URL to download the file")
    file_name: str = Field(..., description="Original filename")
    file_type: str = Field(..., description="MIME type")
    file_size: int = Field(..., description="File size in bytes")
    file_category: FileCategory = Field(..., description="File category")
    thumbnail_url: Optional[str] = Field(None, description="Thumbnail URL (for images)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "file_url": "/api/files/download/abc123_vacation.jpg",
                "file_name": "vacation.jpg",
                "file_type": "image/jpeg",
                "file_size": 1234567,
                "file_category": "image",
                "thumbnail_url": "/api/files/download/abc123_vacation_thumb.jpg"
            }
        }


class FileValidationError(BaseModel):
    """File validation error"""
    error: str
    details: Optional[str] = None

