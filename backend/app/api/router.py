"""
API router - combines all endpoint routers
"""
from fastapi import APIRouter
from .endpoints import auth, users, conversations, messages, websocket, files, reactions
from . import friendships

api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(users.router, prefix="/users", tags=["Users"])
api_router.include_router(conversations.router, prefix="/conversations", tags=["Conversations"])
api_router.include_router(messages.router, prefix="/messages", tags=["Messages"])
api_router.include_router(reactions.router, prefix="/messages", tags=["Reactions"])
api_router.include_router(files.router, prefix="/files", tags=["Files"])
api_router.include_router(friendships.router, tags=["Friendships"])
api_router.include_router(websocket.router, tags=["WebSocket"])

