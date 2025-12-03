"""
Message schemas
"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime
from uuid import UUID


class MessageBase(BaseModel):
    """Base message schema"""
    content: str = Field(..., min_length=1)


class MessageCreate(MessageBase):
    """Schema for creating a message"""
    conversation_id: UUID
    file_url: Optional[str] = None
    file_type: Optional[str] = None
    file_name: Optional[str] = None


class MessageUpdate(BaseModel):
    """Schema for updating a message"""
    content: str = Field(..., min_length=1)


class MessageResponse(MessageBase):
    """Message schema for API responses"""
    id: UUID
    conversation_id: UUID
    sender_id: Optional[UUID] = None
    sender_username: Optional[str] = None
    sender_display_name: Optional[str] = None
    content: str
    file_url: Optional[str] = None
    file_type: Optional[str] = None
    file_name: Optional[str] = None
    created_at: datetime
    edited_at: Optional[datetime] = None
    is_deleted: str = "false"
    
    # Read Receipts
    delivered_at: Optional[datetime] = None
    read_at: Optional[datetime] = None
    read_by_user_id: Optional[UUID] = None
    
    model_config = ConfigDict(from_attributes=True)


class Message(MessageResponse):
    """Alias for MessageResponse"""
    pass


class MessageMarkAsRead(BaseModel):
    """Schema for marking a message as read"""
    message_id: UUID
    read_at: Optional[datetime] = None


class MessageReadResponse(BaseModel):
    """Response after marking message as read"""
    message_id: UUID
    read_at: datetime
    read_by_user_id: UUID
    
    model_config = ConfigDict(from_attributes=True)

