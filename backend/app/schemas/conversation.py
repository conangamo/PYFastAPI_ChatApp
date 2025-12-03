"""
Conversation schemas
"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import datetime
from uuid import UUID
from enum import Enum


class ConversationType(str, Enum):
    """Conversation type enum"""
    direct = "direct"
    group = "group"


class ConversationBase(BaseModel):
    """Base conversation schema"""
    type: ConversationType
    title: Optional[str] = None


class ConversationCreate(BaseModel):
    """Schema for creating a conversation"""
    type: ConversationType
    title: Optional[str] = Field(None, max_length=200)
    participant_ids: List[UUID] = Field(..., min_length=1)


class ConversationUpdate(BaseModel):
    """Schema for updating a conversation"""
    title: Optional[str] = Field(None, max_length=200)


class ConversationParticipantResponse(BaseModel):
    """Participant info in conversation"""
    user_id: UUID
    username: str
    display_name: str
    joined_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class ConversationResponse(BaseModel):
    """Conversation schema for API responses"""
    id: UUID
    type: ConversationType
    title: Optional[str] = None
    created_by: UUID
    created_at: datetime
    updated_at: datetime
    participants: Optional[List[ConversationParticipantResponse]] = None
    last_message: Optional[str] = None
    unread_count: Optional[int] = 0
    
    model_config = ConfigDict(from_attributes=True)


class Conversation(ConversationResponse):
    """Alias for ConversationResponse"""
    pass

