"""
WebSocket Connection Manager
Manages all active WebSocket connections and message broadcasting
"""
from fastapi import WebSocket
from typing import Dict, List, Set
from uuid import UUID
import json
import logging
from datetime import datetime

from ..schemas.websocket import WSMessage, WSMessageType

logger = logging.getLogger(__name__)


class ConnectionManager:
    """
    Manages WebSocket connections for real-time messaging
    
    Attributes:
        active_connections: Dict mapping user_id to WebSocket connection
        user_conversations: Dict mapping user_id to set of conversation_ids they're in
    """
    
    def __init__(self):
        # Store active connections: {user_id: websocket}
        self.active_connections: Dict[UUID, WebSocket] = {}
        
        # Store user's conversations for efficient broadcasting
        # {user_id: {conversation_id1, conversation_id2, ...}}
        self.user_conversations: Dict[UUID, Set[UUID]] = {}
    
    async def connect(self, websocket: WebSocket, user_id: UUID):
        """
        Accept and store a new WebSocket connection
        
        Args:
            websocket: The WebSocket connection
            user_id: The user's UUID
        """
        await websocket.accept()
        
        # If user already has a connection, close the old one
        if user_id in self.active_connections:
            old_ws = self.active_connections[user_id]
            try:
                await old_ws.close(code=1000, reason="New connection established")
            except Exception as e:
                logger.warning(f"Error closing old connection for user {user_id}: {e}")
        
        # Store new connection
        self.active_connections[user_id] = websocket
        
        logger.info(f"User {user_id} connected. Total connections: {len(self.active_connections)}")
    
    def disconnect(self, user_id: UUID):
        """
        Remove a WebSocket connection
        
        Args:
            user_id: The user's UUID
        """
        if user_id in self.active_connections:
            del self.active_connections[user_id]
            logger.info(f"User {user_id} disconnected. Total connections: {len(self.active_connections)}")
        
        # Clean up conversation tracking
        if user_id in self.user_conversations:
            del self.user_conversations[user_id]
    
    def add_user_to_conversation(self, user_id: UUID, conversation_id: UUID):
        """
        Track which conversations a user is part of
        
        Args:
            user_id: The user's UUID
            conversation_id: The conversation's UUID
        """
        if user_id not in self.user_conversations:
            self.user_conversations[user_id] = set()
        self.user_conversations[user_id].add(conversation_id)
    
    def remove_user_from_conversation(self, user_id: UUID, conversation_id: UUID):
        """
        Remove user from conversation tracking
        
        Args:
            user_id: The user's UUID
            conversation_id: The conversation's UUID
        """
        if user_id in self.user_conversations:
            self.user_conversations[user_id].discard(conversation_id)
    
    async def send_personal_message(self, message: WSMessage, user_id: UUID):
        """
        Send a message to a specific user
        
        Args:
            message: The WebSocket message to send
            user_id: The target user's UUID
        """
        if user_id in self.active_connections:
            websocket = self.active_connections[user_id]
            try:
                # Add timestamp if not present
                if not message.timestamp:
                    message.timestamp = datetime.utcnow()
                
                message_dict = message.model_dump(mode='json')
                await websocket.send_json(message_dict)
                logger.info(f"✅ Sent message to user {user_id}: {message.type}")
            except Exception as e:
                logger.error(f"❌ Error sending message to user {user_id}: {e}")
                import traceback
                logger.error(traceback.format_exc())
                # Connection might be broken, remove it
                self.disconnect(user_id)
        else:
            logger.warning(f"⚠️ User {user_id} not connected, cannot send {message.type} message")
    
    async def broadcast_to_conversation(
        self, 
        message: WSMessage, 
        conversation_id: UUID, 
        exclude_user_id: UUID = None
    ):
        """
        Broadcast a message to all users in a conversation
        
        Args:
            message: The WebSocket message to send
            conversation_id: The conversation's UUID
            exclude_user_id: Optional user_id to exclude from broadcast (e.g., the sender)
        """
        # Find all users in this conversation who are online
        target_users = [
            user_id 
            for user_id, conversations in self.user_conversations.items()
            if conversation_id in conversations and user_id != exclude_user_id
        ]
        
        logger.debug(f"Broadcasting to conversation {conversation_id}: {len(target_users)} users")
        
        # Send to all target users
        for user_id in target_users:
            await self.send_personal_message(message, user_id)
    
    async def broadcast_to_users(self, message: WSMessage, user_ids: List[UUID]):
        """
        Broadcast a message to specific list of users
        
        Args:
            message: The WebSocket message to send
            user_ids: List of user UUIDs to send to
        """
        for user_id in user_ids:
            await self.send_personal_message(message, user_id)
    
    async def broadcast_to_all(self, message: WSMessage, exclude_user_id: UUID = None):
        """
        Broadcast a message to all connected users
        
        Args:
            message: The WebSocket message to send
            exclude_user_id: Optional user_id to exclude from broadcast
        """
        for user_id in list(self.active_connections.keys()):
            if user_id != exclude_user_id:
                await self.send_personal_message(message, user_id)
    
    def is_user_online(self, user_id: UUID) -> bool:
        """
        Check if a user is currently connected
        
        Args:
            user_id: The user's UUID
            
        Returns:
            True if user is online, False otherwise
        """
        return user_id in self.active_connections
    
    def get_online_users(self) -> List[UUID]:
        """
        Get list of all online user IDs
        
        Returns:
            List of user UUIDs that are currently connected
        """
        return list(self.active_connections.keys())
    
    def get_connection_count(self) -> int:
        """
        Get total number of active connections
        
        Returns:
            Number of active WebSocket connections
        """
        return len(self.active_connections)
    
    async def send_to_user(self, message: WSMessage, user_id: UUID):
        """
        Send a message to a specific user (alias for send_personal_message)
        
        Args:
            message: The WebSocket message to send
            user_id: The target user's UUID
        """
        await self.send_personal_message(message, user_id)


# Global connection manager instance
manager = ConnectionManager()

