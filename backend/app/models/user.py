from sqlalchemy import Column, String, Boolean, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid

from .base import Base


class User(Base):
    __tablename__ = "users"
    
    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    
    display_name = Column(String(100), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_seen_at = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    
    created_conversations = relationship(
        "Conversation",
        back_populates="creator",
        foreign_keys="Conversation.created_by"
    )
    
    conversation_participants = relationship(
        "ConversationParticipant",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    
    messages = relationship(
        "Message",
        back_populates="sender",
        foreign_keys="Message.sender_id"
    )
    
    def __repr__(self):
        return f"<User {self.username}>"

