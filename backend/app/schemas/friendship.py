"""
Friendship Schemas for API validation
"""

from pydantic import BaseModel, UUID4, Field
from datetime import datetime
from typing import Literal, Optional


class FriendshipBase(BaseModel):
    """Base friendship schema"""
    pass


class FriendRequestCreate(BaseModel):
    """Schema for creating a friend request"""
    friend_id: UUID4 = Field(..., description="ID of user to send friend request to")


class FriendRequestResponse(BaseModel):
    """Schema for responding to a friend request"""
    friendship_id: UUID4 = Field(..., description="ID of the friendship record")
    action: Literal["accept", "reject", "block"] = Field(..., description="Action to take on request")


class FriendshipOut(BaseModel):
    """Schema for friendship output"""
    id: UUID4
    user_id: UUID4
    friend_id: UUID4
    status: Literal["pending", "accepted", "rejected", "blocked"]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class FriendWithUser(BaseModel):
    """Schema for friend with user details (also used for search results)"""
    friendship_id: Optional[UUID4] = None  # None if not friends yet
    user_id: UUID4
    username: str
    display_name: str
    email: str
    last_seen_at: Optional[datetime]
    is_active: bool
    status: Optional[Literal["pending", "accepted", "rejected", "blocked"]] = None  # None if not friends
    created_at: Optional[datetime] = None  # None if not friends yet
    
    class Config:
        from_attributes = True


class FriendshipStatus(BaseModel):
    """Schema for checking friendship status between two users"""
    are_friends: bool
    status: Optional[Literal["pending", "accepted", "rejected", "blocked"]]
    friendship_id: Optional[UUID4]
    initiated_by: Optional[UUID4]  # Who sent the friend request

