"""
Message Reaction endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from typing import List
from uuid import UUID
from datetime import datetime
from collections import defaultdict

from ...database import get_db
from ...models.user import User
from ...models.message import Message
from ...models.reaction import MessageReaction
from ...models.conversation import ConversationParticipant
from ...schemas.reaction import (
    ReactionCreate,
    ReactionResponse,
    ReactionSummary,
    MessageWithReactions
)
from ...schemas.websocket import WSMessage, WSMessageType, WSReactionAdded, WSReactionRemoved
from ...core.deps import get_current_active_user
from ...websocket import manager

router = APIRouter()


@router.post("/{message_id}/reactions", response_model=ReactionResponse, status_code=status.HTTP_201_CREATED)
async def add_reaction(
    message_id: UUID,
    reaction_data: ReactionCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Add a reaction to a message
    
    - **message_id**: Message to react to
    - **emoji**: Emoji to react with (e.g., 👍, ❤️, 😂)
    
    User must be participant in the conversation
    """
    # Get message
    result = await db.execute(
        select(Message).where(Message.id == message_id)
    )
    message = result.scalar_one_or_none()
    
    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message not found"
        )
    
    # Verify user is participant in conversation
    result = await db.execute(
        select(ConversationParticipant)
        .where(
            and_(
                ConversationParticipant.conversation_id == message.conversation_id,
                ConversationParticipant.user_id == current_user.id
            )
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a participant in this conversation"
        )
    
    # Check if reaction already exists
    result = await db.execute(
        select(MessageReaction)
        .where(
            and_(
                MessageReaction.message_id == message_id,
                MessageReaction.user_id == current_user.id,
                MessageReaction.emoji == reaction_data.emoji
            )
        )
    )
    existing_reaction = result.scalar_one_or_none()
    
    if existing_reaction:
        # Return existing reaction
        return ReactionResponse(
            id=existing_reaction.id,
            message_id=existing_reaction.message_id,
            user_id=existing_reaction.user_id,
            user_username=current_user.username,
            user_display_name=current_user.display_name,
            emoji=existing_reaction.emoji,
            created_at=existing_reaction.created_at
        )
    
    # Create new reaction
    new_reaction = MessageReaction(
        message_id=message_id,
        user_id=current_user.id,
        emoji=reaction_data.emoji
    )
    db.add(new_reaction)
    await db.commit()
    await db.refresh(new_reaction)
    
    # Broadcast reaction via WebSocket
    ws_message = WSMessage(
        type=WSMessageType.REACTION_ADDED,
        data=WSReactionAdded(
            conversation_id=message.conversation_id,
            message_id=message_id,
            user_id=current_user.id,
            username=current_user.username,
            emoji=reaction_data.emoji,
            created_at=new_reaction.created_at
        ).model_dump(mode='json'),
        timestamp=datetime.utcnow()
    )
    
    await manager.broadcast_to_conversation(
        ws_message,
        message.conversation_id,
        exclude_user_id=None
    )
    
    return ReactionResponse(
        id=new_reaction.id,
        message_id=new_reaction.message_id,
        user_id=new_reaction.user_id,
        user_username=current_user.username,
        user_display_name=current_user.display_name,
        emoji=new_reaction.emoji,
        created_at=new_reaction.created_at
    )


@router.delete("/{message_id}/reactions/{emoji}", status_code=status.HTTP_200_OK)
async def remove_reaction(
    message_id: UUID,
    emoji: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Remove a reaction from a message
    
    - **message_id**: Message ID
    - **emoji**: Emoji to remove
    
    User can only remove their own reactions
    """
    # Get message
    result = await db.execute(
        select(Message).where(Message.id == message_id)
    )
    message = result.scalar_one_or_none()
    
    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message not found"
        )
    
    # Find reaction
    result = await db.execute(
        select(MessageReaction)
        .where(
            and_(
                MessageReaction.message_id == message_id,
                MessageReaction.user_id == current_user.id,
                MessageReaction.emoji == emoji
            )
        )
    )
    reaction = result.scalar_one_or_none()
    
    if not reaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reaction not found"
        )
    
    # Delete reaction
    await db.delete(reaction)
    await db.commit()
    
    # Broadcast removal via WebSocket
    ws_message = WSMessage(
        type=WSMessageType.REACTION_REMOVED,
        data=WSReactionRemoved(
            conversation_id=message.conversation_id,
            message_id=message_id,
            user_id=current_user.id,
            emoji=emoji
        ).model_dump(mode='json'),
        timestamp=datetime.utcnow()
    )
    
    await manager.broadcast_to_conversation(
        ws_message,
        message.conversation_id,
        exclude_user_id=None
    )
    
    return {"message": "Reaction removed successfully"}


@router.get("/{message_id}/reactions", response_model=MessageWithReactions)
async def get_message_reactions(
    message_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all reactions for a message (aggregated by emoji)
    
    - **message_id**: Message ID
    
    Returns summary with counts and user lists for each emoji
    """
    # Get message
    result = await db.execute(
        select(Message).where(Message.id == message_id)
    )
    message = result.scalar_one_or_none()
    
    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message not found"
        )
    
    # Verify user is participant
    result = await db.execute(
        select(ConversationParticipant)
        .where(
            and_(
                ConversationParticipant.conversation_id == message.conversation_id,
                ConversationParticipant.user_id == current_user.id
            )
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a participant in this conversation"
        )
    
    # Get all reactions with user info
    from sqlalchemy.orm import selectinload
    result = await db.execute(
        select(MessageReaction)
        .options(selectinload(MessageReaction.user))
        .where(MessageReaction.message_id == message_id)
    )
    reactions = result.scalars().all()
    
    # Aggregate by emoji
    emoji_map = defaultdict(lambda: {"count": 0, "users": [], "reacted_by_me": False})
    
    for reaction in reactions:
        emoji_data = emoji_map[reaction.emoji]
        emoji_data["count"] += 1
        emoji_data["users"].append({
            "user_id": str(reaction.user_id),
            "username": reaction.user.username if reaction.user else "Unknown",
            "display_name": reaction.user.display_name if reaction.user else "Unknown User"
        })
        if reaction.user_id == current_user.id:
            emoji_data["reacted_by_me"] = True
    
    # Build summary list
    reaction_summaries = [
        ReactionSummary(
            emoji=emoji,
            count=data["count"],
            users=data["users"],
            reacted_by_me=data["reacted_by_me"]
        )
        for emoji, data in emoji_map.items()
    ]
    
    return MessageWithReactions(
        message_id=message_id,
        reactions=reaction_summaries,
        total_reactions=len(reactions)
    )

