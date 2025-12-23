from sqlalchemy import Column, String, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
import enum

from .base import Base


class ConversationType(str, enum.Enum):
    direct = "direct"
    group = "group"


class Conversation(Base):
    __tablename__ = "conversations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    type = Column(SQLEnum(ConversationType, name='conversation_type'), nullable=False)
    title = Column(String(200), nullable=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
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
    __tablename__ = "conversation_participants"
    
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
    joined_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_read_message_id = Column(
        UUID(as_uuid=True),
        ForeignKey("messages.id", ondelete="SET NULL"),
        nullable=True
    )
    
    conversation = relationship("Conversation", back_populates="participants")
    user = relationship("User", back_populates="conversation_participants")
    last_read_message = relationship("Message", foreign_keys=[last_read_message_id])
    
    def __repr__(self):
        return f"<Participant user={self.user_id} conv={self.conversation_id}>"

