"""
Conversation endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func
from sqlalchemy.orm import selectinload
from typing import List
from uuid import UUID

from ...database import get_db
from ...models.user import User
from ...models.conversation import Conversation, ConversationParticipant, ConversationType
from ...models.message import Message
from ...schemas.conversation import (
    ConversationCreate,
    ConversationUpdate,
    ConversationResponse,
    ConversationParticipantResponse,
    ConversationType as ConversationTypeSchema
)
from ...core.deps import get_current_active_user
from ...models.friendship import Friendship
from ...websocket.manager import manager
from ...schemas.websocket import WSMessage, WSMessageType, WSChatMessage
from datetime import datetime
from pydantic import BaseModel
from typing import List as ListType

router = APIRouter()


class AddParticipantsBatchRequest(BaseModel):
    """Request schema for adding multiple participants"""
    user_ids: ListType[UUID]


def _build_conversation_response(conversation: Conversation) -> ConversationResponse:
    """Helper function to build ConversationResponse with participant details"""
    participants_response = [
        ConversationParticipantResponse(
            user_id=p.user.id,
            username=p.user.username,
            display_name=p.user.display_name,
            joined_at=p.joined_at
        )
        for p in conversation.participants
    ]
    
    return ConversationResponse(
        id=conversation.id,
        type=conversation.type.value,
        title=conversation.title,
        created_by=conversation.created_by,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        participants=participants_response,
        last_message=None,
        unread_count=0
    )


@router.post("/", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    conversation_data: ConversationCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new conversation
    
    - **type**: "direct" or "group"
    - **title**: Group name (required for group, ignored for direct)
    - **participant_ids**: List of user IDs to add (excluding yourself)
    
    For direct chat: Exactly 1 participant (the other user)
    For group chat: At least 1 participant (will add yourself automatically)
    """
    # Validate participants
    if conversation_data.type == ConversationType.direct:
        if len(conversation_data.participant_ids) != 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Direct conversation must have exactly 1 other participant"
            )
        
        # Check if direct conversation already exists
        other_user_id = conversation_data.participant_ids[0]
        
        # Find existing direct conversation between these 2 users
        result = await db.execute(
            select(Conversation)
            .join(ConversationParticipant, Conversation.id == ConversationParticipant.conversation_id)
            .where(
                and_(
                    Conversation.type == ConversationType.direct,
                    ConversationParticipant.user_id.in_([current_user.id, other_user_id])
                )
            )
            .group_by(Conversation.id)
            .having(func.count(ConversationParticipant.user_id) == 2)
        )
        existing_conv = result.scalar_one_or_none()
        
        if existing_conv:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Direct conversation already exists with this user"
            )
    
    elif conversation_data.type == ConversationType.group:
        if not conversation_data.title:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Group conversation must have a title"
            )
    
    # Verify all participants exist
    result = await db.execute(
        select(User).where(User.id.in_(conversation_data.participant_ids))
    )
    participants = result.scalars().all()
    
    if len(participants) != len(conversation_data.participant_ids):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="One or more participants not found"
        )
    
    # Create conversation
    new_conversation = Conversation(
        type=conversation_data.type,
        title=conversation_data.title,
        created_by=current_user.id
    )
    db.add(new_conversation)
    await db.flush()
    
    # Add creator as participant
    creator_participant = ConversationParticipant(
        conversation_id=new_conversation.id,
        user_id=current_user.id
    )
    db.add(creator_participant)
    
    # Add other participants
    for participant_id in conversation_data.participant_ids:
        participant = ConversationParticipant(
            conversation_id=new_conversation.id,
            user_id=participant_id
        )
        db.add(participant)
    
    await db.commit()
    
    # Reload conversation with participants and user info
    result = await db.execute(
        select(Conversation)
        .options(selectinload(Conversation.participants).selectinload(ConversationParticipant.user))
        .where(Conversation.id == new_conversation.id)
    )
    conversation = result.scalar_one()
    
    # Broadcast new conversation event to all participants via WebSocket
    from ...websocket.manager import manager
    from ...schemas.websocket import WSMessage, WSMessageType
    from datetime import datetime
    import logging
    
    logger = logging.getLogger(__name__)
    
    conversation_response = _build_conversation_response(conversation)
    
    # DEBUG: Check participants
    logger.info(f"🐛 DEBUG: conversation.id = {conversation.id}")
    logger.info(f"🐛 DEBUG: conversation.participants type = {type(conversation.participants)}")
    logger.info(f"🐛 DEBUG: conversation.participants = {conversation.participants}")
    logger.info(f"🐛 DEBUG: len(conversation.participants) = {len(conversation.participants)}")
    
    # Register all participants in connection manager
    for participant in conversation.participants:
        manager.add_user_to_conversation(participant.user_id, conversation.id)
    
    # Send to each participant (including creator)
    logger.info(f"🔔 Broadcasting NEW_CONVERSATION to {len(conversation.participants)} participants")
    for participant in conversation.participants:
        try:
            logger.info(f"📤 Sending NEW_CONVERSATION to user {participant.user_id}")
            ws_message = WSMessage(
                type=WSMessageType.NEW_CONVERSATION,
                data={
                    "conversation": conversation_response.model_dump(mode='json')
                },
                timestamp=datetime.utcnow()
            )
            # Use send_to_user which will log if user is not connected
            # Log the message being sent
            logger.info(f"📤 Message to send: type={ws_message.type}, data keys={list(ws_message.data.keys())}")
            logger.info(f"📤 Conversation data in message: {'conversation' in ws_message.data}")
            
            await manager.send_to_user(ws_message, participant.user_id)
            logger.info(f"✅ NEW_CONVERSATION sent to user {participant.user_id}")
        except Exception as e:
            logger.error(f"❌ Error sending NEW_CONVERSATION to user {participant.user_id}: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    logger.info(f"🎉 Broadcast complete for conversation {conversation.id}")
    
    return conversation_response


@router.get("/", response_model=List[ConversationResponse])
async def get_conversations(
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all conversations for current user
    
    Returns conversations ordered by most recent activity
    """
    # Get conversations where user is a participant with participant/user info
    result = await db.execute(
        select(Conversation)
        .join(ConversationParticipant)
        .options(selectinload(Conversation.participants).selectinload(ConversationParticipant.user))
        .where(ConversationParticipant.user_id == current_user.id)
        .order_by(Conversation.updated_at.desc())
        .offset(skip)
        .limit(limit)
    )
    conversations = result.scalars().unique().all()
    
    return [_build_conversation_response(conv) for conv in conversations]


@router.get("/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get conversation by ID
    
    User must be a participant in the conversation
    """
    # Check if conversation exists and user is participant
    result = await db.execute(
        select(Conversation)
        .join(ConversationParticipant)
        .options(selectinload(Conversation.participants).selectinload(ConversationParticipant.user))
        .where(
            and_(
                Conversation.id == conversation_id,
                ConversationParticipant.user_id == current_user.id
            )
        )
    )
    conversation = result.scalar_one_or_none()
    
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found or you are not a participant"
        )
    
    return _build_conversation_response(conversation)


@router.put("/{conversation_id}", response_model=ConversationResponse)
async def update_conversation(
    conversation_id: UUID,
    conversation_update: ConversationUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update conversation (only group title can be updated)
    
    Only creator can update
    """
    result = await db.execute(
        select(Conversation).where(Conversation.id == conversation_id)
    )
    conversation = result.scalar_one_or_none()
    
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )
    
    # Check if user is creator
    if conversation.created_by != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only conversation creator can update"
        )
    
    # Only group conversations can have title updated
    if conversation.type != ConversationType.group:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot update direct conversation"
        )
    
    # Update title
    if conversation_update.title:
        conversation.title = conversation_update.title
    
    await db.commit()
    
    # Reload with participants
    result = await db.execute(
        select(Conversation)
        .options(selectinload(Conversation.participants).selectinload(ConversationParticipant.user))
        .where(Conversation.id == conversation_id)
    )
    conversation = result.scalar_one()
    
    return _build_conversation_response(conversation)


@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(
    conversation_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete conversation
    
    Only creator can delete. This will delete all messages and participants.
    """
    result = await db.execute(
        select(Conversation).where(Conversation.id == conversation_id)
    )
    conversation = result.scalar_one_or_none()
    
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )
    
    # Check if user is creator
    if conversation.created_by != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only conversation creator can delete"
        )
    
    await db.delete(conversation)
    await db.commit()
    
    return None


@router.get("/{conversation_id}/participants", response_model=List[ConversationParticipantResponse])
async def get_participants(
    conversation_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all participants in a conversation
    """
    # Verify user is participant
    result = await db.execute(
        select(ConversationParticipant)
        .where(
            and_(
                ConversationParticipant.conversation_id == conversation_id,
                ConversationParticipant.user_id == current_user.id
            )
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a participant in this conversation"
        )
    
    # Get all participants with user info
    result = await db.execute(
        select(User, ConversationParticipant.joined_at)
        .join(ConversationParticipant, User.id == ConversationParticipant.user_id)
        .where(ConversationParticipant.conversation_id == conversation_id)
    )
    participants = result.all()
    
    return [
        ConversationParticipantResponse(
            user_id=user.id,
            username=user.username,
            display_name=user.display_name,
            joined_at=joined_at
        )
        for user, joined_at in participants
    ]


@router.post("/{conversation_id}/participants/{user_id}", status_code=status.HTTP_201_CREATED)
async def add_participant(
    conversation_id: UUID,
    user_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Add a single user to group conversation
    
    Only works for group conversations. Only creator can add participants.
    Only friends can be added. Max 100 members.
    """
    # Get conversation
    result = await db.execute(
        select(Conversation).where(Conversation.id == conversation_id)
    )
    conversation = result.scalar_one_or_none()
    
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )
    
    # Check if group conversation
    if conversation.type != ConversationType.group:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only add participants to group conversations"
        )
    
    # Check if current user is creator
    if conversation.created_by != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only conversation creator can add participants"
        )
    
    # Check current participant count
    result = await db.execute(
        select(func.count(ConversationParticipant.user_id))
        .where(ConversationParticipant.conversation_id == conversation_id)
    )
    current_count = result.scalar_one()
    
    if current_count >= 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Group has reached maximum 100 members"
        )
    
    # Check if user exists
    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    added_user = result.scalar_one_or_none()
    if not added_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Check if friend
    result = await db.execute(
        select(Friendship).where(
            or_(
                and_(Friendship.user_id == current_user.id, Friendship.friend_id == user_id),
                and_(Friendship.user_id == user_id, Friendship.friend_id == current_user.id)
            ),
            Friendship.status == "accepted"
        )
    )
    friendship = result.scalar_one_or_none()
    
    if not friendship:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You can only add friends to the group"
        )
    
    # Check if already participant
    result = await db.execute(
        select(ConversationParticipant)
        .where(
            and_(
                ConversationParticipant.conversation_id == conversation_id,
                ConversationParticipant.user_id == user_id
            )
        )
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is already a participant"
        )
    
    # Add participant
    new_participant = ConversationParticipant(
        conversation_id=conversation_id,
        user_id=user_id
    )
    db.add(new_participant)
    await db.flush()
    
    # Create system message
    system_message = Message(
        conversation_id=conversation_id,
        sender_id=None,
        content=f"{current_user.display_name} đã thêm {added_user.display_name} vào nhóm",
        file_type="system"
    )
    db.add(system_message)
    await db.flush()
    
    # Update conversation updated_at
    conversation.updated_at = system_message.created_at
    
    # Broadcast system message to existing participants
    ws_system_msg = WSMessage(
        type=WSMessageType.NEW_MESSAGE,
        data=WSChatMessage(
            conversation_id=conversation_id,
            message_id=system_message.id,
            sender_id=None,
            sender_username="System",
            sender_display_name="System",
            content=system_message.content,
            message_type="system",
            created_at=system_message.created_at
        ).model_dump(mode='json'),
        timestamp=datetime.utcnow()
    )
    await manager.broadcast_to_conversation(ws_system_msg, conversation_id)
    
    # Send NEW_CONVERSATION to new member
    result = await db.execute(
        select(Conversation)
        .options(selectinload(Conversation.participants).selectinload(ConversationParticipant.user))
        .where(Conversation.id == conversation_id)
    )
    conv = result.scalar_one()
    conversation_response = _build_conversation_response(conv)
    
    new_conv_msg = WSMessage(
        type=WSMessageType.NEW_CONVERSATION,
        data={"conversation": conversation_response.model_dump(mode='json')},
        timestamp=datetime.utcnow()
    )
    await manager.send_personal_message(new_conv_msg, user_id)
    manager.add_user_to_conversation(user_id, conversation_id)
    
    await db.commit()
    
    return {"message": "Participant added successfully"}


@router.delete("/{conversation_id}/participants/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_participant(
    conversation_id: UUID,
    user_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Remove a user from group conversation (or leave conversation)
    
    Users can remove themselves. Only creator can remove others.
    """
    # Get conversation
    result = await db.execute(
        select(Conversation).where(Conversation.id == conversation_id)
    )
    conversation = result.scalar_one_or_none()
    
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )
    
    # Check if group conversation
    if conversation.type != ConversationType.group:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot remove participants from direct conversations"
        )
    
    # Check permissions
    if user_id != current_user.id and conversation.created_by != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only remove yourself or be the creator to remove others"
        )
    
    # Get participant
    result = await db.execute(
        select(ConversationParticipant)
        .where(
            and_(
                ConversationParticipant.conversation_id == conversation_id,
                ConversationParticipant.user_id == user_id
            )
        )
    )
    participant = result.scalar_one_or_none()
    
    if not participant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Participant not found in conversation"
        )
    
    # Remove participant
    await db.delete(participant)
    await db.commit()
    
    return None


@router.post("/{conversation_id}/participants/batch", status_code=status.HTTP_201_CREATED)
async def add_participants_batch(
    conversation_id: UUID,
    request: AddParticipantsBatchRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Add multiple friends to group conversation at once
    
    - Only creator can add
    - Only friends can be added
    - Max 100 members total
    - Creates 1 system message for all added users
    """
    # Get conversation
    result = await db.execute(
        select(Conversation).where(Conversation.id == conversation_id)
    )
    conversation = result.scalar_one_or_none()
    
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )
    
    # Check if group conversation
    if conversation.type != ConversationType.group:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only add participants to group conversations"
        )
    
    # Check if current user is creator
    if conversation.created_by != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only conversation creator can add participants"
        )
    
    # Check current participant count
    result = await db.execute(
        select(func.count(ConversationParticipant.user_id))
        .where(ConversationParticipant.conversation_id == conversation_id)
    )
    current_count = result.scalar_one()
    
    # Check if adding would exceed limit (100)
    if current_count + len(request.user_ids) > 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Group can have maximum 100 members. Current: {current_count}, Trying to add: {len(request.user_ids)}"
        )
    
    # Verify all users exist and are friends
    added_users = []
    for user_id in request.user_ids:
        # Check if user exists
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User {user_id} not found"
            )
        
        # Check if friend
        result = await db.execute(
            select(Friendship).where(
                or_(
                    and_(Friendship.user_id == current_user.id, Friendship.friend_id == user_id),
                    and_(Friendship.user_id == user_id, Friendship.friend_id == current_user.id)
                ),
                Friendship.status == "accepted"
            )
        )
        friendship = result.scalar_one_or_none()
        
        if not friendship:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"You can only add friends. User {user.display_name} is not your friend"
            )
        
        # Check if already participant
        result = await db.execute(
            select(ConversationParticipant)
            .where(
                ConversationParticipant.conversation_id == conversation_id,
                ConversationParticipant.user_id == user_id
            )
        )
        if result.scalar_one_or_none():
            continue  # Skip if already participant
        
        # Add participant
        new_participant = ConversationParticipant(
            conversation_id=conversation_id,
            user_id=user_id
        )
        db.add(new_participant)
        added_users.append(user)
    
    # Create 1 system message for all added users
    if added_users:
        # Build message: "A đã thêm B, C, D vào nhóm"
        user_names = [user.display_name for user in added_users]
        if len(user_names) == 1:
            message_content = f"{current_user.display_name} đã thêm {user_names[0]} vào nhóm"
        else:
            names_str = ", ".join(user_names[:-1]) + f" và {user_names[-1]}"
            message_content = f"{current_user.display_name} đã thêm {names_str} vào nhóm"
        
        system_message = Message(
            conversation_id=conversation_id,
            sender_id=None,  # System message
            content=message_content,
            file_type="system"
        )
        db.add(system_message)
        await db.flush()
        
        # Update conversation updated_at
        conversation.updated_at = system_message.created_at
        
        # Broadcast to existing participants (system message)
        ws_system_msg = WSMessage(
            type=WSMessageType.NEW_MESSAGE,
            data=WSChatMessage(
                conversation_id=conversation_id,
                message_id=system_message.id,
                sender_id=None,
                sender_username="System",
                sender_display_name="System",
                content=system_message.content,
                message_type="system",
                created_at=system_message.created_at
            ).model_dump(mode='json'),
            timestamp=datetime.utcnow()
        )
        await manager.broadcast_to_conversation(
            ws_system_msg,
            conversation_id,
            exclude_user_id=None  # Send to all including creator
        )
        
        # Send NEW_CONVERSATION notification to new members (so group appears immediately)
        result = await db.execute(
            select(Conversation)
            .options(selectinload(Conversation.participants).selectinload(ConversationParticipant.user))
            .where(Conversation.id == conversation_id)
        )
        conv = result.scalar_one()
        conversation_response = _build_conversation_response(conv)
        
        for added_user in added_users:
            new_conv_msg = WSMessage(
                type=WSMessageType.NEW_CONVERSATION,
                data={
                    "conversation": conversation_response.model_dump(mode='json')
                },
                timestamp=datetime.utcnow()
            )
            await manager.send_personal_message(new_conv_msg, added_user.id)
            
            # Also register user to conversation in connection manager
            manager.add_user_to_conversation(added_user.id, conversation_id)
    
    await db.commit()
    
    return {
        "message": f"Added {len(added_users)} participant(s) successfully",
        "added_count": len(added_users)
    }


@router.delete("/{conversation_id}/unfriend", status_code=status.HTTP_204_NO_CONTENT)
async def unfriend_in_direct_chat(
    conversation_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Unfriend user in direct conversation (1-1 only)
    
    This removes the friendship relationship but keeps the conversation
    """
    # Get conversation
    result = await db.execute(
        select(Conversation).where(Conversation.id == conversation_id)
    )
    conversation = result.scalar_one_or_none()
    
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )
    
    # Check if direct conversation
    if conversation.type != ConversationType.direct:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only unfriend in direct conversations"
        )
    
    # Check if user is participant
    result = await db.execute(
        select(ConversationParticipant)
        .where(
            ConversationParticipant.conversation_id == conversation_id,
            ConversationParticipant.user_id == current_user.id
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a participant in this conversation"
        )
    
    # Get the other user in direct chat
    result = await db.execute(
        select(ConversationParticipant)
        .where(
            ConversationParticipant.conversation_id == conversation_id,
            ConversationParticipant.user_id != current_user.id
        )
    )
    other_participant = result.scalar_one_or_none()
    
    if not other_participant:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Direct conversation must have exactly 2 participants"
        )
    
    other_user_id = other_participant.user_id
    
    # Find and delete friendship (check both directions)
    result = await db.execute(
        select(Friendship).where(
            or_(
                and_(Friendship.user_id == current_user.id, Friendship.friend_id == other_user_id),
                and_(Friendship.user_id == other_user_id, Friendship.friend_id == current_user.id)
            ),
            Friendship.status == "accepted"
        )
    )
    friendship = result.scalar_one_or_none()
    
    if not friendship:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You are not friends with this user"
        )
    
    # Delete friendship
    await db.delete(friendship)
    await db.commit()
    
    return None


@router.delete("/{conversation_id}/leave", status_code=status.HTTP_204_NO_CONTENT)
async def leave_conversation(
    conversation_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Leave a conversation (remove yourself from participants)
    
    For direct chat: Conversation disappears from your list (friendship NOT deleted)
    For group chat: You leave the group, system message created
    """
    # Get participant record
    result = await db.execute(
        select(ConversationParticipant)
        .where(
            ConversationParticipant.conversation_id == conversation_id,
            ConversationParticipant.user_id == current_user.id
        )
    )
    participant = result.scalar_one_or_none()
    
    if not participant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="You are not a participant in this conversation"
        )
    
    # Get conversation to check type
    result = await db.execute(
        select(Conversation).where(Conversation.id == conversation_id)
    )
    conversation = result.scalar_one()
    
    # Remove participant
    await db.delete(participant)
    
    # For group chat: Create system message and check if need to disband
    if conversation.type == ConversationType.group:
        # Create system message: "{username} đã rời khỏi nhóm"
        system_message = Message(
            conversation_id=conversation_id,
            sender_id=None,  # System message has no sender
            content=f"{current_user.display_name} đã rời khỏi nhóm",
            file_type="system"  # Mark as system message
        )
        db.add(system_message)
        await db.flush()
        
        # Update conversation updated_at
        conversation.updated_at = system_message.created_at
        
        # Check remaining participants count
        result = await db.execute(
            select(func.count(ConversationParticipant.user_id))
            .where(ConversationParticipant.conversation_id == conversation_id)
        )
        remaining_count = result.scalar_one()
        
        # If only 1 person left, auto-disband group
        if remaining_count == 1:
            # Get the last person
            result = await db.execute(
                select(ConversationParticipant)
                .where(ConversationParticipant.conversation_id == conversation_id)
            )
            last_participant = result.scalar_one()
            
            # Create system message for last person
            disband_message = Message(
                conversation_id=conversation_id,
                sender_id=None,
                content="Nhóm đã tự động giải tán vì chỉ còn lại bạn",
                file_type="system"
            )
            db.add(disband_message)
            await db.flush()
            
            # Send notification to last person
            disband_ws_msg = WSMessage(
                type=WSMessageType.NEW_MESSAGE,
                data=WSChatMessage(
                    conversation_id=conversation_id,
                    message_id=disband_message.id,
                    sender_id=None,
                    sender_username="System",
                    sender_display_name="System",
                    content=disband_message.content,
                    message_type="system",
                    created_at=disband_message.created_at
                ).model_dump(mode='json'),
                timestamp=datetime.utcnow()
            )
            # Commit before sending WebSocket (so message is saved)
            await db.commit()
            
            # Send notification to last person
            await manager.send_personal_message(disband_ws_msg, last_participant.user_id)
            
            # Delete conversation (cascade will delete all messages and participants)
            # Need to get conversation again after commit
            result = await db.execute(
                select(Conversation).where(Conversation.id == conversation_id)
            )
            conversation = result.scalar_one()
            await db.delete(conversation)
            await db.commit()
            return None
        else:
            # Broadcast system message to remaining participants
            leave_ws_msg = WSMessage(
                type=WSMessageType.NEW_MESSAGE,
                data=WSChatMessage(
                    conversation_id=conversation_id,
                    message_id=system_message.id,
                    sender_id=None,
                    sender_username="System",
                    sender_display_name="System",
                    content=system_message.content,
                    message_type="system",
                    created_at=system_message.created_at
                ).model_dump(mode='json'),
                timestamp=datetime.utcnow()
            )
            await manager.broadcast_to_conversation(
                leave_ws_msg,
                conversation_id,
                exclude_user_id=current_user.id
            )
    
    await db.commit()
    return None

