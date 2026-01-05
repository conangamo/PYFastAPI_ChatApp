from fastapi import WebSocket
from typing import Dict, List, Set, Optional
from uuid import UUID
from dataclasses import dataclass, field
import json
import logging
from datetime import datetime

from ..schemas.websocket import WSMessage, WSMessageType

logger = logging.getLogger(__name__)


@dataclass
class CallSession:
    call_id: str
    caller_id: UUID
    callee_id: UUID
    state: str = "ringing"  # ringing, active, ended, rejected
    created_at: datetime = field(default_factory=datetime.utcnow)
    ended_at: Optional[datetime] = None


class ConnectionManager:
    
    def __init__(self):
        self.active_connections: Dict[UUID, WebSocket] = {}
        self.user_conversations: Dict[UUID, Set[UUID]] = {}
        
        # Store active call sessions: {call_id: CallSession}
        self.active_calls: Dict[str, CallSession] = {}
    
    async def connect(self, websocket: WebSocket, user_id: UUID):
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
        if user_id in self.active_connections:
            del self.active_connections[user_id]
            logger.info(f"User {user_id} disconnected. Total connections: {len(self.active_connections)}")
        
        # Clean up conversation tracking
        if user_id in self.user_conversations:
            del self.user_conversations[user_id]
    
    def add_user_to_conversation(self, user_id: UUID, conversation_id: UUID):
        if user_id not in self.user_conversations:
            self.user_conversations[user_id] = set()
        self.user_conversations[user_id].add(conversation_id)
    
    def remove_user_from_conversation(self, user_id: UUID, conversation_id: UUID):
        if user_id in self.user_conversations:
            self.user_conversations[user_id].discard(conversation_id)
    
    async def send_personal_message(self, message: WSMessage, user_id: UUID):
        if user_id in self.active_connections:
            websocket = self.active_connections[user_id]
            try:
                if not message.timestamp:
                    message.timestamp = datetime.utcnow()
                
                message_dict = message.model_dump(mode='json')
                await websocket.send_json(message_dict)
                logger.info(f"Sent message to user {user_id}: {message.type}")
            except Exception as e:
                logger.error(f"Error sending message to user {user_id}: {e}")
                import traceback
                logger.error(traceback.format_exc())
                self.disconnect(user_id)
        else:
            logger.warning(f"User {user_id} not connected, cannot send {message.type} message")
    
    async def broadcast_to_conversation(
        self, 
        message: WSMessage, 
        conversation_id: UUID, 
        exclude_user_id: UUID = None
    ):
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
        for user_id in user_ids:
            await self.send_personal_message(message, user_id)
    
    async def broadcast_to_all(self, message: WSMessage, exclude_user_id: UUID = None):
        for user_id in list(self.active_connections.keys()):
            if user_id != exclude_user_id:
                await self.send_personal_message(message, user_id)
    
    def is_user_online(self, user_id: UUID) -> bool:
        return user_id in self.active_connections
    
    def get_online_users(self) -> List[UUID]:
        return list(self.active_connections.keys())
    
    def get_connection_count(self) -> int:
        return len(self.active_connections)
    
    async def send_to_user(self, message: WSMessage, user_id: UUID):
        await self.send_personal_message(message, user_id)


# Global connection manager instance
manager = ConnectionManager()

