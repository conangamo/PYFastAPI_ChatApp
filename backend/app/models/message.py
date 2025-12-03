"""
Message model
"""
from sqlalchemy import Column, String, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid

from .base import Base


class Message(Base):
    """Message model - represents a chat message"""
    
    __tablename__ = "messages"
    
    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Foreign Keys
    conversation_id = Column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    sender_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    
    # Content
    content = Column(Text, nullable=False)
    
    # File attachment (optional)
    file_url = Column(String(500), nullable=True)
    file_type = Column(String(50), nullable=True)
    file_name = Column(String(255), nullable=True)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    edited_at = Column(DateTime(timezone=True), nullable=True)
    is_deleted = Column(String(10), default="false", nullable=False)  # "false" or "true" for soft delete
    
    # Read Receipts (for 1-1 chat)
    delivered_at = Column(DateTime(timezone=True), nullable=True)
    read_at = Column(DateTime(timezone=True), nullable=True)
    read_by_user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    
    # Relationships
    conversation = relationship("Conversation", back_populates="messages")
    sender = relationship("User", back_populates="messages", foreign_keys=[sender_id])
    reactions = relationship("MessageReaction", back_populates="message", cascade="all, delete-orphan")
    read_by_user = relationship("User", foreign_keys=[read_by_user_id])
    
    def __repr__(self):
        return f"<Message {self.id} from {self.sender_id}>"

