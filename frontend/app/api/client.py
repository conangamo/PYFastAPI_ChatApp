import httpx
from typing import Optional, List, Dict, Any
from pathlib import Path

from ..config import config
from ..models import User, Conversation, Message


class APIClient:
    def __init__(self, base_url: str = None):
        self.base_url = base_url or config.API_BASE
        self.token: Optional[str] = None
        self.client = httpx.AsyncClient(timeout=30.0, follow_redirects=True)
    
    def set_token(self, token: str):
        self.token = token
    
    def get_headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers
    
    async def close(self):
        await self.client.aclose()
    
    async def login(self, username: str, password: str) -> Dict[str, Any]:
        response = await self.client.post(
            f"{self.base_url}/auth/login/",
            data={"username": username, "password": password}
        )
        response.raise_for_status()
        return response.json()
    
    async def register(self, username: str, email: str, password: str, display_name: str) -> Dict[str, Any]:
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
    
    async def get_current_user(self) -> User:
        response = await self.client.get(
            f"{self.base_url}/users/me/",
            headers=self.get_headers()
        )
        response.raise_for_status()
        return User.from_dict(response.json())
    
    async def get_users(self) -> List[User]:
        response = await self.client.get(
            f"{self.base_url}/users/",
            headers=self.get_headers()
        )
        response.raise_for_status()
        return [User.from_dict(u) for u in response.json()]
    
    async def get_conversations(self) -> List[Conversation]:
        response = await self.client.get(
            f"{self.base_url}/conversations/",
            headers=self.get_headers()
        )
        response.raise_for_status()
        return [Conversation.from_dict(c) for c in response.json()]
    
    async def create_conversation(self, type: str, participant_ids: List[str], title: Optional[str] = None) -> Conversation:
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
        response = await self.client.get(
            f"{self.base_url}/conversations/{conversation_id}/",
            headers=self.get_headers()
        )
        response.raise_for_status()
        return Conversation.from_dict(response.json())
    
    async def unfriend_in_conversation(self, conversation_id: str) -> None:
        response = await self.client.delete(
            f"{self.base_url}/conversations/{conversation_id}/unfriend",
            headers=self.get_headers()
        )
        response.raise_for_status()
    
    async def leave_conversation(self, conversation_id: str) -> None:
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
        response = await self.client.post(
            f"{self.base_url}/conversations/{conversation_id}/participants/batch",
            headers=self.get_headers(),
            json={"user_ids": user_ids}
        )
        response.raise_for_status()
        return response.json()
    
    async def get_friends(self) -> List[dict]:
        response = await self.client.get(
            f"{self.base_url}/friendships/friends",
            headers=self.get_headers()
        )
        response.raise_for_status()
        return response.json()
    
    async def get_messages(self, conversation_id: str, skip: int = 0, limit: int = 50) -> List[Message]:
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
    
    async def upload_file(self, file_path: Path) -> Dict[str, Any]:
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
        if file_url.startswith("http"):
            return file_url
        return f"{config.BACKEND_URL}{file_url}"
    
    async def get(self, endpoint: str, **kwargs) -> httpx.Response:
        url = f"{self.base_url}{endpoint}" if not endpoint.startswith("http") else endpoint
        return await self.client.get(
            url,
            headers=self.get_headers(),
            **kwargs
        )
    
    async def post(self, endpoint: str, **kwargs) -> httpx.Response:
        url = f"{self.base_url}{endpoint}" if not endpoint.startswith("http") else endpoint
        return await self.client.post(
            url,
            headers=self.get_headers(),
            **kwargs
        )
    
    async def put(self, endpoint: str, **kwargs) -> httpx.Response:
        url = f"{self.base_url}{endpoint}" if not endpoint.startswith("http") else endpoint
        return await self.client.put(
            url,
            headers=self.get_headers(),
            **kwargs
        )
    
    async def delete(self, endpoint: str, **kwargs) -> httpx.Response:
        url = f"{self.base_url}{endpoint}" if not endpoint.startswith("http") else endpoint
        return await self.client.delete(
            url,
            headers=self.get_headers(),
            **kwargs
        )


api_client: Optional[APIClient] = None


def get_api_client() -> APIClient:
    global api_client
    if api_client is None:
        api_client = APIClient()
    return api_client

