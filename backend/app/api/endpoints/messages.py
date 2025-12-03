"""
Message endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc
from typing import List
from uuid import UUID
from datetime import datetime

from ...database import get_db
from ...models.user import User
from ...models.conversation import Conversation, ConversationParticipant
from ...models.message import Message
from ...schemas.message import MessageCreate, MessageResponse, MessageUpdate, MessageReadResponse
from ...schemas.websocket import WSMessage, WSMessageType, WSChatMessage, WSMessageEdited, WSMessageDeleted, WSMessageRead
from ...core.deps import get_current_active_user
from ...websocket import manager

router = APIRouter()


@router.post("/", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
async def send_message(
    message_data: MessageCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Send a message to a conversation
    
    - **conversation_id**: Conversation to send message to
    - **content**: Message text content
    - **file_url**: Optional file URL (for images/files)
    - **file_type**: Optional file MIME type
    - **file_name**: Optional file name
    
    User must be a participant in the conversation
    """
    # Verify conversation exists and user is participant
    result = await db.execute(
        select(ConversationParticipant)
        .where(
            and_(
                ConversationParticipant.conversation_id == message_data.conversation_id,
                ConversationParticipant.user_id == current_user.id
            )
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a participant in this conversation"
        )
    
    # Create message
    new_message = Message(
        conversation_id=message_data.conversation_id,
        sender_id=current_user.id,
        content=message_data.content,
        file_url=message_data.file_url,
        file_type=message_data.file_type,
        file_name=message_data.file_name
    )
    db.add(new_message)
    
    # Update conversation updated_at
    result = await db.execute(
        select(Conversation).where(Conversation.id == message_data.conversation_id)
    )
    conversation = result.scalar_one()
    conversation.updated_at = new_message.created_at
    
    await db.commit()
    await db.refresh(new_message)
    
    # Broadcast message via WebSocket to all conversation participants
    ws_message = WSMessage(
        type=WSMessageType.NEW_MESSAGE,
        data=WSChatMessage(
            conversation_id=new_message.conversation_id,
            message_id=new_message.id,
            sender_id=new_message.sender_id,
            sender_username=current_user.username,
            sender_display_name=current_user.display_name,
            content=new_message.content,
            message_type=new_message.file_type or "text",
            file_url=new_message.file_url,
            created_at=new_message.created_at
        ).model_dump(mode='json'),
        timestamp=datetime.utcnow()
    )
    
    # Broadcast to all participants in the conversation
    await manager.broadcast_to_conversation(
        ws_message,
        message_data.conversation_id,
        exclude_user_id=None  # Send to everyone including sender for confirmation
    )
    
    # Return message with sender info
    msg_response = MessageResponse(
        id=new_message.id,
        conversation_id=new_message.conversation_id,
        sender_id=new_message.sender_id,
        sender_username=current_user.username,
        sender_display_name=current_user.display_name,
        content=new_message.content,
        file_url=new_message.file_url,
        file_type=new_message.file_type,
        file_name=new_message.file_name,
        created_at=new_message.created_at,
        edited_at=new_message.edited_at,
        is_deleted=new_message.is_deleted,
        # Read Receipts
        delivered_at=new_message.delivered_at,
        read_at=new_message.read_at,
        read_by_user_id=new_message.read_by_user_id
    )
    
    return msg_response


@router.get("/", response_model=List[MessageResponse])
async def get_messages(
    conversation_id: UUID,
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get messages from a conversation
    
    Returns messages ordered by newest first (pagination supported)
    
    - **conversation_id**: Conversation ID (query parameter)
    - **skip**: Number of messages to skip
    - **limit**: Maximum number of messages to return (default 50)
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
    
    # Get messages with sender information
    from sqlalchemy.orm import selectinload
    result = await db.execute(
        select(Message)
        .options(selectinload(Message.sender))  # Load sender relationship
        .where(Message.conversation_id == conversation_id)
        .order_by(desc(Message.created_at))
        .offset(skip)
        .limit(limit)
    )
    messages = result.scalars().all()
    
    # Manually build response with sender info
    messages_response = []
    for msg in messages:
        msg_dict = {
            "id": msg.id,
            "conversation_id": msg.conversation_id,
            "sender_id": msg.sender_id,
            "sender_username": msg.sender.username if msg.sender else "Unknown",
            "sender_display_name": msg.sender.display_name if msg.sender else "Unknown User",
            "content": msg.content,
            "file_url": msg.file_url,
            "file_type": msg.file_type,
            "file_name": msg.file_name,
            "created_at": msg.created_at,
            "edited_at": msg.edited_at,
            "is_deleted": msg.is_deleted,
            # Read Receipts
            "delivered_at": msg.delivered_at,
            "read_at": msg.read_at,
            "read_by_user_id": msg.read_by_user_id
        }
        messages_response.append(MessageResponse(**msg_dict))
    
    return messages_response


@router.put("/{message_id}", response_model=MessageResponse)
async def edit_message(
    message_id: UUID,
    message_update: MessageUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Edit a message
    
    Only message sender can edit their own messages
    Cannot edit deleted messages
    """
    # Get message with sender info
    from sqlalchemy.orm import selectinload
    result = await db.execute(
        select(Message)
        .options(selectinload(Message.sender))
        .where(Message.id == message_id)
    )
    message = result.scalar_one_or_none()
    
    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message not found"
        )
    
    # Check if current user is sender
    if message.sender_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only edit your own messages"
        )
    
    # Check if message is deleted
    if message.is_deleted == "true":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot edit deleted messages"
        )
    
    # Update message
    message.content = message_update.content
    message.edited_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(message)
    
    # Broadcast edit via WebSocket
    ws_message = WSMessage(
        type=WSMessageType.MESSAGE_EDITED,
        data=WSMessageEdited(
            conversation_id=message.conversation_id,
            message_id=message.id,
            sender_id=message.sender_id,
            content=message.content,
            edited_at=message.edited_at
        ).model_dump(mode='json'),
        timestamp=datetime.utcnow()
    )
    
    await manager.broadcast_to_conversation(
        ws_message,
        message.conversation_id,
        exclude_user_id=None
    )
    
    # Return updated message with sender info
    msg_response = MessageResponse(
        id=message.id,
        conversation_id=message.conversation_id,
        sender_id=message.sender_id,
        sender_username=message.sender.username if message.sender else "Unknown",
        sender_display_name=message.sender.display_name if message.sender else "Unknown User",
        content=message.content,
        file_url=message.file_url,
        file_type=message.file_type,
        file_name=message.file_name,
        created_at=message.created_at,
        edited_at=message.edited_at,
        is_deleted=message.is_deleted,
        # Read Receipts
        delivered_at=message.delivered_at,
        read_at=message.read_at,
        read_by_user_id=message.read_by_user_id
    )
    
    return msg_response


@router.put("/{message_id}/read", response_model=MessageReadResponse, status_code=status.HTTP_200_OK)
async def mark_message_as_read(
    message_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Mark a message as read
    
    Updates:
    - message.read_at timestamp
    - message.read_by_user_id
    - participant.last_read_message_id
    - Broadcasts MESSAGE_READ event via WebSocket
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
    
    # Check if user is participant in the conversation
    result = await db.execute(
        select(ConversationParticipant)
        .where(
            and_(
                ConversationParticipant.conversation_id == message.conversation_id,
                ConversationParticipant.user_id == current_user.id
            )
        )
    )
    participant = result.scalar_one_or_none()
    
    if not participant:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a participant in this conversation"
        )
    
    # Don't mark own messages as read
    if message.sender_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot mark your own message as read"
        )
    
    # Update message read status
    read_timestamp = datetime.utcnow()
    message.read_at = read_timestamp
    message.read_by_user_id = current_user.id
    
    # Also update participant's last read message
    participant.last_read_message_id = message_id
    
    await db.commit()
    await db.refresh(message)
    
    # Broadcast MESSAGE_READ event via WebSocket to conversation participants
    read_event = WSMessage(
        type=WSMessageType.MESSAGE_READ,
        data=WSMessageRead(
            conversation_id=message.conversation_id,
            message_id=message.id,
            read_by_user_id=current_user.id,
            read_by_username=current_user.username,
            read_at=read_timestamp
        ).model_dump(mode='json'),
        timestamp=datetime.utcnow()
    )
    
    await manager.broadcast_to_conversation(
        read_event,
        message.conversation_id,
        exclude_user_id=current_user.id  # Don't send to the user who marked it
    )
    
    return MessageReadResponse(
        message_id=message.id,
        read_at=read_timestamp,
        read_by_user_id=current_user.id
    )


@router.delete("/{message_id}", status_code=status.HTTP_200_OK)
async def delete_message(
    message_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a message (soft delete)
    
    Only message sender can delete their own messages
    Message content is replaced with deletion notice
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
    
    # Check if current user is sender
    if message.sender_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only delete your own messages"
        )
    
    # Check if already deleted
    if message.is_deleted == "true":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Message already deleted"
        )
    
    # Soft delete
    message.is_deleted = "true"
    message.content = "This message was deleted"
    message.file_url = None
    message.file_type = None
    message.file_name = None
    
    await db.commit()
    await db.refresh(message)
    
    # Broadcast delete via WebSocket
    ws_message = WSMessage(
        type=WSMessageType.MESSAGE_DELETED,
        data=WSMessageDeleted(
            conversation_id=message.conversation_id,
            message_id=message.id,
            sender_id=message.sender_id
        ).model_dump(mode='json'),
        timestamp=datetime.utcnow()
    )
    
    await manager.broadcast_to_conversation(
        ws_message,
        message.conversation_id,
        exclude_user_id=None
    )
    
    return {"message": "Message deleted successfully"}

