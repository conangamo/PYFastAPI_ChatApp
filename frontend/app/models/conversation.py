"""
Conversation model
"""
from dataclasses import dataclass, field
from typing import List, Optional
from enum import Enum


class ConversationType(str, Enum):
    """Conversation type"""
    DIRECT = "direct"
    GROUP = "group"


@dataclass
class ConversationParticipant:
    """Conversation participant"""
    user_id: str
    username: str
    display_name: str
    joined_at: str
    
    @classmethod
    def from_dict(cls, data: dict) -> "ConversationParticipant":
        """Create from dictionary"""
        return cls(
            user_id=data["user_id"],
            username=data["username"],
            display_name=data["display_name"],
            joined_at=data["joined_at"]
        )


@dataclass
class Conversation:
    """Conversation data model"""
    id: str
    type: ConversationType
    title: Optional[str]
    created_by: str
    created_at: str
    updated_at: str
    participants: List[ConversationParticipant] = field(default_factory=list)
    last_message: Optional[str] = None
    unread_count: int = 0
    
    @classmethod
    def from_dict(cls, data: dict) -> "Conversation":
        """Create Conversation from dictionary"""
        # Parse participants
        participants = []
        if "participants" in data and data["participants"]:
            participants = [
                ConversationParticipant.from_dict(p)
                for p in data["participants"]
            ]
        
        return cls(
            id=data["id"],
            type=ConversationType(data["type"]),
            title=data.get("title"),
            created_by=data["created_by"],
            created_at=data["created_at"],
            updated_at=data["updated_at"],
            participants=participants,
            last_message=data.get("last_message"),
            unread_count=data.get("unread_count", 0)
        )
    
    def get_display_name(self, current_user_id: str) -> str:
        """
        Get display name for conversation
        For direct chats, show other user's name
        For group chats, show title
        """
        if self.type == ConversationType.GROUP:
            return self.title or "Group Chat"
        
        # Direct chat - find other user
        for participant in self.participants:
            if participant.user_id != current_user_id:
                return participant.display_name
        
        return "Unknown User"
    
    def get_other_user(self, current_user_id: str) -> Optional[ConversationParticipant]:
        """Get the other user in direct chat"""
        if self.type == ConversationType.DIRECT:
            for participant in self.participants:
                if participant.user_id != current_user_id:
                    return participant
        return None

