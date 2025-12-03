"""
Friendship Model
Represents friend relationships between users
"""

from sqlalchemy import Column, String, DateTime, CheckConstraint, UniqueConstraint, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid

from .base import Base


class Friendship(Base):
    """
    Friendship model for managing friend relationships
    
    Status flow:
    - pending: Friend request sent, awaiting response
    - accepted: Friends
    - rejected: Request rejected
    - blocked: User blocked
    """
    __tablename__ = "friendships"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    friend_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    status = Column(String(20), nullable=False, default="pending", index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    __table_args__ = (
        CheckConstraint("user_id != friend_id", name="check_not_self"),
        CheckConstraint(
            "status IN ('pending', 'accepted', 'rejected', 'blocked')",
            name="check_valid_status"
        ),
        UniqueConstraint("user_id", "friend_id", name="unique_friendship"),
        Index("idx_friendships_user_status", "user_id", "status"),
        Index("idx_friendships_friend_status", "friend_id", "status"),
    )
    
    def __repr__(self):
        return f"<Friendship {self.user_id} -> {self.friend_id} ({self.status})>"

