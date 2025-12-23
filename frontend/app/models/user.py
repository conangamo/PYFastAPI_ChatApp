from dataclasses import dataclass
from typing import Optional


@dataclass
class User:
    id: str
    username: str
    email: str
    display_name: str
    created_at: str
    last_seen_at: Optional[str] = None
    is_active: bool = True
    
    @classmethod
    def from_dict(cls, data: dict) -> "User":
        return cls(
            id=data["id"],
            username=data["username"],
            email=data["email"],
            display_name=data["display_name"],
            created_at=data["created_at"],
            last_seen_at=data.get("last_seen_at"),
            is_active=data.get("is_active", True)
        )
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "display_name": self.display_name,
            "created_at": self.created_at,
            "last_seen_at": self.last_seen_at,
            "is_active": self.is_active
        }

