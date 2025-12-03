"""
User schemas for validation
"""
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import Optional
from datetime import datetime
from uuid import UUID


class UserBase(BaseModel):
    """Base user schema"""
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)
    display_name: str = Field(..., min_length=1, max_length=100)


class UserCreate(UserBase):
    """Schema for user creation (registration)"""
    password: str = Field(..., min_length=6, max_length=100)


class UserUpdate(BaseModel):
    """Schema for user update"""
    display_name: Optional[str] = Field(None, min_length=1, max_length=100)
    email: Optional[EmailStr] = None


class UserInDB(UserBase):
    """User schema with password hash (internal use)"""
    id: UUID
    password_hash: str
    created_at: datetime
    last_seen_at: Optional[datetime] = None
    is_active: bool = True
    
    model_config = ConfigDict(from_attributes=True)


class UserResponse(BaseModel):
    """User schema for API responses (no password)"""
    id: UUID
    email: EmailStr
    username: str
    display_name: str
    created_at: datetime
    last_seen_at: Optional[datetime] = None
    is_active: bool
    
    model_config = ConfigDict(from_attributes=True)


class User(UserResponse):
    """Alias for UserResponse"""
    pass

