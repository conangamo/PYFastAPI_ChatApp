"""
Pydantic schemas for request/response validation
"""
from .user import User, UserCreate, UserUpdate, UserInDB, UserResponse
from .token import Token, TokenData
from .message import Message, MessageCreate, MessageResponse
from .conversation import (
    Conversation,
    ConversationCreate,
    ConversationUpdate,
    ConversationResponse,
    ConversationType
)
from .websocket import (
    WSMessageType,
    WSMessage,
    WSChatMessage,
    WSTypingIndicator,
    WSUserStatus,
    WSMessageRead,
    WSError,
    WSConnected
)

__all__ = [
    "User",
    "UserCreate", 
    "UserUpdate",
    "UserInDB",
    "UserResponse",
    "Token",
    "TokenData",
    "Message",
    "MessageCreate",
    "MessageResponse",
    "Conversation",
    "ConversationCreate",
    "ConversationUpdate",
    "ConversationResponse",
    "ConversationType",
    "WSMessageType",
    "WSMessage",
    "WSChatMessage",
    "WSTypingIndicator",
    "WSUserStatus",
    "WSMessageRead",
    "WSError",
    "WSConnected",
]

