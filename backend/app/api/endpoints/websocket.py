"""
WebSocket endpoint for real-time messaging
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import Optional
from uuid import UUID
import json
import logging
from datetime import datetime

from ...database import get_db
from ...models.user import User
from ...models.conversation import Conversation, ConversationParticipant
from ...core.security import decode_access_token
from ...websocket import manager
from ...schemas.websocket import (
    WSMessage,
    WSMessageType,
    WSConnected,
    WSError,
    WSUserStatus,
    WSTypingIndicator
)

router = APIRouter()
logger = logging.getLogger(__name__)


async def get_user_from_token(token: str, db: AsyncSession) -> Optional[User]:
    """
    Validate JWT token and get user
    
    Args:
        token: JWT access token
        db: Database session
        
    Returns:
        User object if token is valid, None otherwise
    """
    try:
        # Decode token
        payload = decode_access_token(token)
        if not payload:
            return None
        
        user_id = payload.get("sub")
        if not user_id:
            return None
        
        # Get user from database
        result = await db.execute(
            select(User).where(User.id == UUID(user_id), User.is_active == True)
        )
        user = result.scalar_one_or_none()
        
        return user
    except Exception as e:
        logger.error(f"Error validating token: {e}")
        return None


async def load_user_conversations(user_id: UUID, db: AsyncSession):
    """
    Load all conversations for a user and register them with the connection manager
    
    Args:
        user_id: User's UUID
        db: Database session
    """
    try:
        # Get all conversations user is part of
        result = await db.execute(
            select(ConversationParticipant.conversation_id)
            .where(ConversationParticipant.user_id == user_id)
        )
        conversation_ids = [row[0] for row in result.all()]
        
        # Register user to all their conversations
        for conv_id in conversation_ids:
            manager.add_user_to_conversation(user_id, conv_id)
        
        logger.info(f"Loaded {len(conversation_ids)} conversations for user {user_id}")
    except Exception as e:
        logger.error(f"Error loading conversations for user {user_id}: {e}")


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str = Query(..., description="JWT access token"),
    db: AsyncSession = Depends(get_db)
):
    """
    WebSocket endpoint for real-time messaging
    
    Connection URL: ws://localhost:8000/api/ws?token=YOUR_JWT_TOKEN
    
    Message Format (Client -> Server):
    {
        "type": "typing",
        "data": {
            "conversation_id": "uuid",
            "is_typing": true
        }
    }
    
    Message Format (Server -> Client):
    {
        "type": "new_message",
        "data": {
            "conversation_id": "uuid",
            "message_id": "uuid",
            "sender_id": "uuid",
            "sender_username": "alice",
            "content": "Hello!",
            ...
        },
        "timestamp": "2025-10-19T..."
    }
    """
    # Authenticate user
    user = await get_user_from_token(token, db)
    
    if not user:
        # Authentication failed
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Authentication failed")
        logger.warning("WebSocket connection rejected: Invalid token")
        return
    
    # Accept connection
    await manager.connect(websocket, user.id)
    
    # Load user's conversations
    await load_user_conversations(user.id, db)
    
    # Send connection success message
    connected_msg = WSMessage(
        type=WSMessageType.CONNECTED,
        data=WSConnected(
            user_id=user.id,
            username=user.username,
            message=f"Connected successfully as {user.username}"
        ).model_dump(mode='json'),
        timestamp=datetime.utcnow()
    )
    await manager.send_personal_message(connected_msg, user.id)
    
    # Broadcast user online status to others
    online_msg = WSMessage(
        type=WSMessageType.USER_ONLINE,
        data=WSUserStatus(
            user_id=user.id,
            username=user.username,
            status="online"
        ).model_dump(mode='json'),
        timestamp=datetime.utcnow()
    )
    await manager.broadcast_to_all(online_msg, exclude_user_id=user.id)
    
    logger.info(f"User {user.username} ({user.id}) connected via WebSocket")
    
    try:
        # Listen for messages
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            
            try:
                # Parse message
                message_data = json.loads(data)
                message_type = message_data.get("type")
                message_payload = message_data.get("data", {})
                
                logger.debug(f"Received WebSocket message from {user.username}: {message_type}")
                
                # Handle different message types
                if message_type == "typing":
                    # Typing indicator
                    conversation_id = UUID(message_payload.get("conversation_id"))
                    is_typing = message_payload.get("is_typing", False)
                    
                    typing_msg = WSMessage(
                        type=WSMessageType.TYPING,
                        data=WSTypingIndicator(
                            conversation_id=conversation_id,
                            user_id=user.id,
                            username=user.username,
                            is_typing=is_typing
                        ).model_dump(mode='json'),
                        timestamp=datetime.utcnow()
                    )
                    
                    # Broadcast to conversation participants (except sender)
                    await manager.broadcast_to_conversation(
                        typing_msg,
                        conversation_id,
                        exclude_user_id=user.id
                    )
                
                elif message_type == "ping":
                    # Heartbeat ping
                    pong_msg = WSMessage(
                        type=WSMessageType.PONG,
                        data={"message": "pong"},
                        timestamp=datetime.utcnow()
                    )
                    await manager.send_personal_message(pong_msg, user.id)
                
                else:
                    # Unknown message type
                    logger.warning(f"Unknown WebSocket message type: {message_type}")
                    error_msg = WSMessage(
                        type=WSMessageType.ERROR,
                        data=WSError(
                            message=f"Unknown message type: {message_type}",
                            code="UNKNOWN_MESSAGE_TYPE"
                        ).model_dump(mode='json'),
                        timestamp=datetime.utcnow()
                    )
                    await manager.send_personal_message(error_msg, user.id)
            
            except json.JSONDecodeError:
                logger.error(f"Invalid JSON received from {user.username}")
                error_msg = WSMessage(
                    type=WSMessageType.ERROR,
                    data=WSError(
                        message="Invalid JSON format",
                        code="INVALID_JSON"
                    ).model_dump(mode='json'),
                    timestamp=datetime.utcnow()
                )
                await manager.send_personal_message(error_msg, user.id)
            
            except Exception as e:
                logger.error(f"Error processing WebSocket message from {user.username}: {e}")
                error_msg = WSMessage(
                    type=WSMessageType.ERROR,
                    data=WSError(
                        message="Error processing message",
                        code="PROCESSING_ERROR",
                        details={"error": str(e)}
                    ).model_dump(mode='json'),
                    timestamp=datetime.utcnow()
                )
                await manager.send_personal_message(error_msg, user.id)
    
    except WebSocketDisconnect:
        # Client disconnected
        manager.disconnect(user.id)
        
        # Broadcast user offline status
        offline_msg = WSMessage(
            type=WSMessageType.USER_OFFLINE,
            data=WSUserStatus(
                user_id=user.id,
                username=user.username,
                status="offline",
                last_seen_at=datetime.utcnow()
            ).model_dump(mode='json'),
            timestamp=datetime.utcnow()
        )
        await manager.broadcast_to_all(offline_msg)
        
        logger.info(f"User {user.username} ({user.id}) disconnected from WebSocket")
    
    except Exception as e:
        logger.error(f"Unexpected error in WebSocket connection for {user.username}: {e}")
        manager.disconnect(user.id)

