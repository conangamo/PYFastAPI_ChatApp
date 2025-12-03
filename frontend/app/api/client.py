"""
Main API client
Handles all HTTP communication with backend
"""
import httpx
from typing import Optional, List, Dict, Any
from pathlib import Path

from ..config import config
from ..models import User, Conversation, Message


class APIClient:
    """
    API client for backend communication
    Handles authentication and all API calls
    """
    
    def __init__(self, base_url: str = None):
        """Initialize API client"""
        self.base_url = base_url or config.API_BASE
        self.token: Optional[str] = None
        self.client = httpx.AsyncClient(timeout=30.0, follow_redirects=True)
    
    def set_token(self, token: str):
        """Set authentication token"""
        self.token = token
    
    def get_headers(self) -> Dict[str, str]:
        """Get request headers with auth"""
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers
    
    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()
    
    # ==================== Authentication ====================
    
    async def login(self, username: str, password: str) -> Dict[str, Any]:
        """
        Login user
        
        Returns:
            {
                "access_token": "...",
                "token_type": "bearer"
            }
        """
        response = await self.client.post(
            f"{self.base_url}/auth/login/",
            data={"username": username, "password": password}
        )
        response.raise_for_status()
        return response.json()
    
    async def register(self, username: str, email: str, password: str, display_name: str) -> Dict[str, Any]:
        """
        Register new user
        
        Returns:
            User data
        """
        response = await self.client.post(
            f"{self.base_url}/auth/register/",
            json={
                "username": username,
                "email": email,
                "password": password,
                "display_name": display_name
            }
        )
        response.raise_for_status()
        return response.json()
    
    # ==================== Users ====================
    
    async def get_current_user(self) -> User:
        """Get current user profile"""
        response = await self.client.get(
            f"{self.base_url}/users/me/",
            headers=self.get_headers()
        )
        response.raise_for_status()
        return User.from_dict(response.json())
    
    async def get_users(self) -> List[User]:
        """Get all users"""
        response = await self.client.get(
            f"{self.base_url}/users/",
            headers=self.get_headers()
        )
        response.raise_for_status()
        return [User.from_dict(u) for u in response.json()]
    
    # ==================== Conversations ====================
    
    async def get_conversations(self) -> List[Conversation]:
        """Get user's conversations"""
        response = await self.client.get(
            f"{self.base_url}/conversations/",
            headers=self.get_headers()
        )
        response.raise_for_status()
        return [Conversation.from_dict(c) for c in response.json()]
    
    async def create_conversation(self, type: str, participant_ids: List[str], title: Optional[str] = None) -> Conversation:
        """
        Create new conversation
        
        Args:
            type: "direct" or "group"
            participant_ids: List of user IDs
            title: Group title (required for groups)
        """
        data = {
            "type": type,
            "participant_ids": participant_ids
        }
        if title:
            data["title"] = title
        
        response = await self.client.post(
            f"{self.base_url}/conversations/",
            headers=self.get_headers(),
            json=data
        )
        response.raise_for_status()
        return Conversation.from_dict(response.json())
    
    async def get_conversation(self, conversation_id: str) -> Conversation:
        """Get conversation by ID"""
        response = await self.client.get(
            f"{self.base_url}/conversations/{conversation_id}/",
            headers=self.get_headers()
        )
        response.raise_for_status()
        return Conversation.from_dict(response.json())
    
    async def unfriend_in_conversation(self, conversation_id: str) -> None:
        """Unfriend user in direct conversation"""
        response = await self.client.delete(
            f"{self.base_url}/conversations/{conversation_id}/unfriend",
            headers=self.get_headers()
        )
        response.raise_for_status()
    
    async def leave_conversation(self, conversation_id: str) -> None:
        """Leave a conversation (remove from your list)"""
        response = await self.client.delete(
            f"{self.base_url}/conversations/{conversation_id}/leave",
            headers=self.get_headers()
        )
        response.raise_for_status()
    
    async def add_participant_to_group(
        self,
        conversation_id: str,
        user_id: str
    ) -> dict:
        """Add a single friend to group conversation"""
        response = await self.client.post(
            f"{self.base_url}/conversations/{conversation_id}/participants/{user_id}",
            headers=self.get_headers()
        )
        response.raise_for_status()
        return response.json()
    
    async def add_participants_batch(
        self,
        conversation_id: str,
        user_ids: List[str]
    ) -> dict:
        """Add multiple friends to group conversation at once"""
        response = await self.client.post(
            f"{self.base_url}/conversations/{conversation_id}/participants/batch",
            headers=self.get_headers(),
            json={"user_ids": user_ids}
        )
        response.raise_for_status()
        return response.json()
    
    async def get_friends(self) -> List[dict]:
        """Get list of friends"""
        response = await self.client.get(
            f"{self.base_url}/friendships/friends",
            headers=self.get_headers()
        )
        response.raise_for_status()
        return response.json()
    
    # ==================== Messages ====================
    
    async def get_messages(self, conversation_id: str, skip: int = 0, limit: int = 50) -> List[Message]:
        """Get messages from conversation"""
        response = await self.client.get(
            f"{self.base_url}/messages/",
            params={
                "conversation_id": conversation_id,
                "skip": skip,
                "limit": limit
            },
            headers=self.get_headers()
        )
        response.raise_for_status()
        return [Message.from_dict(m) for m in response.json()]
    
    async def send_message(
        self,
        conversation_id: str,
        content: str,
        file_url: Optional[str] = None,
        file_type: Optional[str] = None,
        file_name: Optional[str] = None
    ) -> Message:
        """
        Send message
        
        Args:
            conversation_id: Conversation ID
            content: Message text
            file_url: File URL (if sending file)
            file_type: File MIME type
            file_name: Original filename
        """
        data = {
            "conversation_id": conversation_id,
            "content": content
        }
        if file_url:
            data["file_url"] = file_url
            data["file_type"] = file_type
            data["file_name"] = file_name
        
        response = await self.client.post(
            f"{self.base_url}/messages/",
            headers=self.get_headers(),
            json=data
        )
        response.raise_for_status()
        return Message.from_dict(response.json())
    
    # ==================== Files ====================
    
    async def upload_file(self, file_path: Path) -> Dict[str, Any]:
        """
        Upload file
        
        Returns:
            {
                "file_url": "...",
                "file_name": "...",
                "file_type": "...",
                "file_size": 123456,
                "file_category": "image",
                "thumbnail_url": "..." (if image)
            }
        """
        with open(file_path, 'rb') as f:
            files = {"file": (file_path.name, f)}
            headers = {}
            if self.token:
                headers["Authorization"] = f"Bearer {self.token}"
            
            response = await self.client.post(
                f"{self.base_url}/files/upload/",
                headers=headers,
                files=files
            )
            response.raise_for_status()
            return response.json()
    
    def get_file_download_url(self, file_url: str) -> str:
        """
        Get full URL for file download
        
        Args:
            file_url: Relative file URL from backend
            
        Returns:
            Full URL like http://localhost:8000/api/files/download/...
        """
        if file_url.startswith("http"):
            return file_url
        return f"{config.BACKEND_URL}{file_url}"
    
    # ==================== Generic HTTP Methods ====================
    
    async def get(self, endpoint: str, **kwargs) -> httpx.Response:
        """
        Generic GET request
        
        Args:
            endpoint: API endpoint (e.g., "/api/friendships/search/alice")
            **kwargs: Additional httpx request parameters
            
        Returns:
            httpx.Response object
        """
        url = f"{self.base_url}{endpoint}" if not endpoint.startswith("http") else endpoint
        return await self.client.get(
            url,
            headers=self.get_headers(),
            **kwargs
        )
    
    async def post(self, endpoint: str, **kwargs) -> httpx.Response:
        """
        Generic POST request
        
        Args:
            endpoint: API endpoint
            **kwargs: Additional httpx request parameters (json, data, etc.)
            
        Returns:
            httpx.Response object
        """
        url = f"{self.base_url}{endpoint}" if not endpoint.startswith("http") else endpoint
        return await self.client.post(
            url,
            headers=self.get_headers(),
            **kwargs
        )
    
    async def put(self, endpoint: str, **kwargs) -> httpx.Response:
        """Generic PUT request"""
        url = f"{self.base_url}{endpoint}" if not endpoint.startswith("http") else endpoint
        return await self.client.put(
            url,
            headers=self.get_headers(),
            **kwargs
        )
    
    async def delete(self, endpoint: str, **kwargs) -> httpx.Response:
        """Generic DELETE request"""
        url = f"{self.base_url}{endpoint}" if not endpoint.startswith("http") else endpoint
        return await self.client.delete(
            url,
            headers=self.get_headers(),
            **kwargs
        )


# Global API client instance (will be initialized in main app)
api_client: Optional[APIClient] = None


def get_api_client() -> APIClient:
    """Get global API client instance"""
    global api_client
    if api_client is None:
        api_client = APIClient()
    return api_client

