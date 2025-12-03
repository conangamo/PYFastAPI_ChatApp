"""
Conversation and ConversationParticipant models
"""
from sqlalchemy import Column, String, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
import enum

from .base import Base


class ConversationType(str, enum.Enum):
    """Conversation type enum"""
    direct = "direct"
    group = "group"


class Conversation(Base):
    """Conversation model - represents a chat conversation"""
    
    __tablename__ = "conversations"
    
    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Type
    type = Column(SQLEnum(ConversationType, name='conversation_type'), nullable=False)
    
    # Group info (NULL for direct conversations)
    title = Column(String(200), nullable=True)
    
    # Creator
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    creator = relationship("User", back_populates="created_conversations", foreign_keys=[created_by])
    
    participants = relationship(
        "ConversationParticipant",
        back_populates="conversation",
        cascade="all, delete-orphan"
    )
    
    messages = relationship(
        "Message",
        back_populates="conversation",
        cascade="all, delete-orphan"
    )
    
    def __repr__(self):
        return f"<Conversation {self.type.value} {self.id}>"


class ConversationParticipant(Base):
    """Conversation participant - many-to-many relationship between users and conversations"""
    
    __tablename__ = "conversation_participants"
    
    # Composite Primary Key
    conversation_id = Column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        primary_key=True
    )
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True
    )
    
    # Metadata
    joined_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Last read message (for read receipts)
    last_read_message_id = Column(
        UUID(as_uuid=True),
        ForeignKey("messages.id", ondelete="SET NULL"),
        nullable=True
    )
    
    # Relationships
    conversation = relationship("Conversation", back_populates="participants")
    user = relationship("User", back_populates="conversation_participants")
    last_read_message = relationship("Message", foreign_keys=[last_read_message_id])
    
    def __repr__(self):
        return f"<Participant user={self.user_id} conv={self.conversation_id}>"

