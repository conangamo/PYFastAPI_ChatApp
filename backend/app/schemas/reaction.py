"""
Message Reaction schemas
"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict
from datetime import datetime
from uuid import UUID


class ReactionCreate(BaseModel):
    """Schema for adding a reaction"""
    emoji: str = Field(..., min_length=1, max_length=10)


class ReactionResponse(BaseModel):
    """Schema for reaction API response"""
    id: UUID
    message_id: UUID
    user_id: UUID
    user_username: Optional[str] = None
    user_display_name: Optional[str] = None
    emoji: str
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class ReactionSummary(BaseModel):
    """Schema for aggregated reaction counts"""
    emoji: str
    count: int
    users: List[Dict[str, str]]  # List of {user_id, username, display_name}
    reacted_by_me: bool = False


class MessageWithReactions(BaseModel):
    """Message with reaction summary"""
    message_id: UUID
    reactions: List[ReactionSummary]
    total_reactions: int

