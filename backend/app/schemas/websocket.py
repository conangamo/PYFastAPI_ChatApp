"""
WebSocket message schemas
"""
from pydantic import BaseModel, Field
from typing import Optional, Any, Dict
from datetime import datetime
from uuid import UUID
from enum import Enum


class WSMessageType(str, Enum):
    """WebSocket message types"""
    # Chat messages
    NEW_MESSAGE = "new_message"
    MESSAGE_DELIVERED = "message_delivered"
    MESSAGE_READ = "message_read"
    MESSAGE_EDITED = "message_edited"
    MESSAGE_DELETED = "message_deleted"
    
    # Conversations
    NEW_CONVERSATION = "new_conversation"
    
    # Reactions
    REACTION_ADDED = "reaction_added"
    REACTION_REMOVED = "reaction_removed"
    
    # Typing indicators
    TYPING = "typing"
    
    # User status
    USER_ONLINE = "user_online"
    USER_OFFLINE = "user_offline"
    
    # System
    CONNECTED = "connected"
    ERROR = "error"
    PING = "ping"
    PONG = "pong"


class WSMessage(BaseModel):
    """Base WebSocket message"""
    type: WSMessageType
    data: Dict[str, Any]
    timestamp: Optional[datetime] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v)
        }


class WSChatMessage(BaseModel):
    """Chat message data for WebSocket"""
    conversation_id: UUID
    message_id: UUID
    sender_id: Optional[UUID] = None  # None for system messages
    sender_username: str
    sender_display_name: str
    content: str
    message_type: str = "text"
    file_url: Optional[str] = None
    created_at: datetime


class WSTypingIndicator(BaseModel):
    """Typing indicator data"""
    conversation_id: UUID
    user_id: UUID
    username: str
    is_typing: bool


class WSUserStatus(BaseModel):
    """User online/offline status"""
    user_id: UUID
    username: str
    status: str  # "online" or "offline"
    last_seen_at: Optional[datetime] = None


class WSMessageRead(BaseModel):
    """Message read receipt"""
    conversation_id: UUID
    message_id: UUID
    read_by_user_id: UUID
    read_by_username: str
    read_at: datetime


class WSError(BaseModel):
    """Error message"""
    message: str
    code: str
    details: Optional[Dict[str, Any]] = None


class WSConnected(BaseModel):
    """Connection success message"""
    user_id: UUID
    username: str
    message: str = "Connected successfully"


class WSMessageEdited(BaseModel):
    """Message edited event"""
    conversation_id: UUID
    message_id: UUID
    sender_id: UUID
    content: str
    edited_at: datetime


class WSMessageDeleted(BaseModel):
    """Message deleted event"""
    conversation_id: UUID
    message_id: UUID
    sender_id: UUID


class WSReactionAdded(BaseModel):
    """Reaction added event"""
    conversation_id: UUID
    message_id: UUID
    user_id: UUID
    username: str
    emoji: str
    created_at: datetime


class WSReactionRemoved(BaseModel):
    """Reaction removed event"""
    conversation_id: UUID
    message_id: UUID
    user_id: UUID
    emoji: str

