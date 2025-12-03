"""
Message model
"""
from dataclasses import dataclass, field
from typing import Optional, Dict, List
from datetime import datetime


@dataclass
class Message:
    """Message data model"""
    id: str
    conversation_id: str
    content: str
    created_at: str
    sender_id: Optional[str] = None  # None for system messages
    sender_username: str = "System"
    sender_display_name: str = "System"
    is_read: bool = False
    file_url: Optional[str] = None
    file_type: Optional[str] = None
    file_name: Optional[str] = None
    edited_at: Optional[str] = None
    is_deleted: str = "false"
    reactions: Dict[str, List[Dict[str, str]]] = field(default_factory=dict)  # {emoji: [users]}
    
    # Read Receipts
    delivered_at: Optional[datetime] = None
    read_at: Optional[datetime] = None
    read_by_user_id: Optional[str] = None
    
    @classmethod
    def from_dict(cls, data: dict) -> "Message":
        """Create Message from dictionary"""
        # Parse datetime strings to datetime objects
        delivered_at = None
        read_at = None
        
        if data.get("delivered_at"):
            try:
                delivered_at = datetime.fromisoformat(data["delivered_at"].replace("Z", "+00:00"))
            except:
                pass
        
        if data.get("read_at"):
            try:
                read_at = datetime.fromisoformat(data["read_at"].replace("Z", "+00:00"))
            except:
                pass
        
        return cls(
            id=data["id"],
            conversation_id=data["conversation_id"],
            sender_id=data.get("sender_id"),  # Can be None for system messages
            sender_username=data.get("sender_username", "System"),
            sender_display_name=data.get("sender_display_name", "System"),
            content=data["content"],
            created_at=data["created_at"],
            is_read=data.get("is_read", False),
            file_url=data.get("file_url"),
            file_type=data.get("file_type"),
            file_name=data.get("file_name"),
            edited_at=data.get("edited_at"),
            is_deleted=data.get("is_deleted", "false"),
            reactions=data.get("reactions", {}),
            # Read Receipts
            delivered_at=delivered_at,
            read_at=read_at,
            read_by_user_id=data.get("read_by_user_id")
        )
    
    def is_mine(self, current_user_id: str) -> bool:
        """Check if message is from current user"""
        if self.sender_id is None:
            return False  # System messages are never "mine"
        return self.sender_id == current_user_id
    
    def has_file(self) -> bool:
        """Check if message has file attachment"""
        return self.file_url is not None
    
    def is_edited(self) -> bool:
        """Check if message has been edited"""
        return self.edited_at is not None
    
    def is_message_deleted(self) -> bool:
        """Check if message is deleted"""
        return self.is_deleted == "true"
    
    def has_reactions(self) -> bool:
        """Check if message has any reactions"""
        return len(self.reactions) > 0
    
    def get_reaction_count(self, emoji: str) -> int:
        """Get count of specific emoji reaction"""
        return len(self.reactions.get(emoji, []))
    
    def has_reacted(self, emoji: str, user_id: str) -> bool:
        """Check if user has reacted with specific emoji"""
        users = self.reactions.get(emoji, [])
        return any(user.get("user_id") == user_id for user in users)
    
    def total_reactions(self) -> int:
        """Get total number of reactions"""
        return sum(len(users) for users in self.reactions.values())

