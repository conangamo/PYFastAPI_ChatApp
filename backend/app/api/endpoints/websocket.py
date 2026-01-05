from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import Optional
from uuid import UUID
import json
import logging
from datetime import datetime

from ...database import get_db
from ...models.user import User
from ...models.conversation import Conversation, ConversationParticipant
from ...core.security import decode_access_token
from ...websocket import manager
from ...schemas.websocket import (
    WSMessage,
    WSMessageType,
    WSConnected,
    WSError,
    WSUserStatus,
    WSTypingIndicator,
    WSCallInvite,
    WSCallInviteSent,
    WSCallIncoming,
    WSCallAccept,
    WSCallAccepted,
    WSCallReject,
    WSCallEnd,
    WSCallEnded,
    WSSDPOffer,
    WSSDPAnswer,
    WSICECandidate
)
from ...websocket.manager import CallSession

router = APIRouter()
logger = logging.getLogger(__name__)


async def get_user_from_token(token: str, db: AsyncSession) -> Optional[User]:
    try:
        # Decode token
        payload = decode_access_token(token)
        if not payload:
            return None
        
        user_id = payload.get("sub")
        if not user_id:
            return None
        
        result = await db.execute(
            select(User).where(User.id == UUID(user_id), User.is_active == True)
        )
        user = result.scalar_one_or_none()
        
        return user
    except Exception as e:
        logger.error(f"Error validating token: {e}")
        return None


async def load_user_conversations(user_id: UUID, db: AsyncSession):
    try:
        # Get all conversations user is part of
        result = await db.execute(
            select(ConversationParticipant.conversation_id)
            .where(ConversationParticipant.user_id == user_id)
        )
        conversation_ids = [row[0] for row in result.all()]
        
        for conv_id in conversation_ids:
            manager.add_user_to_conversation(user_id, conv_id)
        
        logger.info(f"Loaded {len(conversation_ids)} conversations for user {user_id}")
    except Exception as e:
        logger.error(f"Error loading conversations for user {user_id}: {e}")


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str = Query(..., description="JWT access token"),
    db: AsyncSession = Depends(get_db)
):

    # Authenticate user
    user = await get_user_from_token(token, db)
    
    if not user:
        # Authentication failed
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Authentication failed")
        logger.warning("WebSocket connection rejected: Invalid token")
        return
    
    # Accept connection
    await manager.connect(websocket, user.id)
    
    # Load user's conversations
    await load_user_conversations(user.id, db)
    
    connected_msg = WSMessage(
        type=WSMessageType.CONNECTED,
        data=WSConnected(
            user_id=user.id,
            username=user.username,
            message=f"Connected successfully as {user.username}"
        ).model_dump(mode='json'),
        timestamp=datetime.utcnow()
    )
    await manager.send_personal_message(connected_msg, user.id)
    
    # Broadcast user online status to others
    online_msg = WSMessage(
        type=WSMessageType.USER_ONLINE,
        data=WSUserStatus(
            user_id=user.id,
            username=user.username,
            status="online"
        ).model_dump(mode='json'),
        timestamp=datetime.utcnow()
    )
    await manager.broadcast_to_all(online_msg, exclude_user_id=user.id)
    
    logger.info(f"User {user.username} ({user.id}) connected via WebSocket")
    
    try:
        while True:
            data = await websocket.receive_text()
            
            try:
                message_data = json.loads(data)
                message_type = message_data.get("type")
                message_payload = message_data.get("data", {})
                
                logger.debug(f"Received WebSocket message from {user.username}: {message_type}")
                
                if message_type == "typing":
                    conversation_id = UUID(message_payload.get("conversation_id"))
                    is_typing = message_payload.get("is_typing", False)
                    
                    typing_msg = WSMessage(
                        type=WSMessageType.TYPING,
                        data=WSTypingIndicator(
                            conversation_id=conversation_id,
                            user_id=user.id,
                            username=user.username,
                            is_typing=is_typing
                        ).model_dump(mode='json'),
                        timestamp=datetime.utcnow()
                    )
                    
                    # Broadcast to conversation participants (except sender)
                    await manager.broadcast_to_conversation(
                        typing_msg,
                        conversation_id,
                        exclude_user_id=user.id
                    )
                
                elif message_type == "ping":
                    pong_msg = WSMessage(
                        type=WSMessageType.PONG,
                        data={"message": "pong"},
                        timestamp=datetime.utcnow()
                    )
                    await manager.send_personal_message(pong_msg, user.id)
                
                elif message_type == "call_invite":
                    # Handle call invite
                    try:
                        call_invite = WSCallInvite(**message_payload)
                        call_id = call_invite.call_id
                        caller_id = call_invite.caller_id
                        callee_id = call_invite.callee_id
                        conversation_id = call_invite.conversation_id
                        
                        if caller_id != user.id:
                            raise ValueError("Caller ID does not match authenticated user")
                        
                        if not manager.is_user_online(callee_id):
                            error_msg = WSMessage(
                                type=WSMessageType.ERROR,
                                data=WSError(
                                    message="User is not online",
                                    code="USER_OFFLINE"
                                ).model_dump(mode='json'),
                                timestamp=datetime.utcnow()
                            )
                            await manager.send_personal_message(error_msg, user.id)
                            continue
                        
                        # Create call session
                        call_session = CallSession(
                            call_id=call_id,
                            caller_id=caller_id,
                            callee_id=callee_id,
                            state="ringing"
                        )
                        manager.active_calls[call_id] = call_session
                        
                        result = await db.execute(
                            select(User).where(User.id == caller_id)
                        )
                        caller = result.scalar_one_or_none()
                        
                        if not caller:
                            raise ValueError("Caller not found")
                        
                        invite_sent_msg = WSMessage(
                            type=WSMessageType.CALL_INVITE_SENT,
                            data=WSCallInviteSent(
                                call_id=call_id,
                                callee_id=callee_id,
                                conversation_id=conversation_id
                            ).model_dump(mode='json'),
                            timestamp=datetime.utcnow()
                        )
                        await manager.send_personal_message(invite_sent_msg, caller_id)
                        
                        incoming_msg = WSMessage(
                            type=WSMessageType.CALL_INCOMING,
                            data=WSCallIncoming(
                                call_id=call_id,
                                caller_id=caller_id,
                                caller_username=caller.username,
                                caller_display_name=caller.display_name or caller.username,
                                conversation_id=conversation_id
                            ).model_dump(mode='json'),
                            timestamp=datetime.utcnow()
                        )
                        await manager.send_personal_message(incoming_msg, callee_id)
                        
                        logger.info(f"Call invite sent: {call_id} from {caller_id} to {callee_id}")
                        
                    except Exception as e:
                        logger.error(f"Error handling call_invite: {e}")
                        error_msg = WSMessage(
                            type=WSMessageType.ERROR,
                            data=WSError(
                                message=f"Error processing call invite: {str(e)}",
                                code="CALL_INVITE_ERROR"
                            ).model_dump(mode='json'),
                            timestamp=datetime.utcnow()
                        )
                        await manager.send_personal_message(error_msg, user.id)
                
                elif message_type == "call_accept":
                    # Handle call accept
                    try:
                        call_accept = WSCallAccept(**message_payload)
                        call_id = call_accept.call_id
                        caller_id = call_accept.caller_id
                        callee_id = call_accept.callee_id
                        
                        if callee_id != user.id:
                            raise ValueError("Callee ID does not match authenticated user")
                        
                        if call_id not in manager.active_calls:
                            raise ValueError("Call session not found")
                        
                        call_session = manager.active_calls[call_id]
                        
                        if call_session.state != "ringing":
                            raise ValueError(f"Call is not in ringing state: {call_session.state}")
                        
                        call_session.state = "active"
                        
                        result = await db.execute(
                            select(User).where(User.id == callee_id)
                        )
                        callee = result.scalar_one_or_none()
                        
                        if not callee:
                            raise ValueError("Callee not found")
                        
                        accepted_msg = WSMessage(
                            type=WSMessageType.CALL_ACCEPTED,
                            data=WSCallAccepted(
                                call_id=call_id,
                                callee_id=callee_id,
                                callee_username=callee.username,
                                callee_display_name=callee.display_name or callee.username
                            ).model_dump(mode='json'),
                            timestamp=datetime.utcnow()
                        )
                        await manager.send_personal_message(accepted_msg, caller_id)
                        
                        logger.info(f"Call accepted: {call_id} by {callee_id}")
                        
                    except Exception as e:
                        logger.error(f"Error handling call_accept: {e}")
                        error_msg = WSMessage(
                            type=WSMessageType.ERROR,
                            data=WSError(
                                message=f"Error processing call accept: {str(e)}",
                                code="CALL_ACCEPT_ERROR"
                            ).model_dump(mode='json'),
                            timestamp=datetime.utcnow()
                        )
                        await manager.send_personal_message(error_msg, user.id)
                
                elif message_type == "call_reject":
                    # Handle call reject
                    try:
                        call_reject = WSCallReject(**message_payload)
                        call_id = call_reject.call_id
                        caller_id = call_reject.caller_id
                        callee_id = call_reject.callee_id
                        reason = call_reject.reason
                        
                        if callee_id != user.id:
                            raise ValueError("Callee ID does not match authenticated user")
                        
                        reject_msg = WSMessage(
                            type=WSMessageType.CALL_REJECT,
                            data=call_reject.model_dump(mode='json'),
                            timestamp=datetime.utcnow()
                        )
                        await manager.send_personal_message(reject_msg, caller_id)
                        
                        if call_id in manager.active_calls:
                            call_session = manager.active_calls[call_id]
                            call_session.state = "rejected"
                            call_session.ended_at = datetime.utcnow()
                            del manager.active_calls[call_id]
                        
                        logger.info(f"Call rejected: {call_id} by {callee_id}, reason: {reason}")
                        
                    except Exception as e:
                        logger.error(f"Error handling call_reject: {e}")
                        error_msg = WSMessage(
                            type=WSMessageType.ERROR,
                            data=WSError(
                                message=f"Error processing call reject: {str(e)}",
                                code="CALL_REJECT_ERROR"
                            ).model_dump(mode='json'),
                            timestamp=datetime.utcnow()
                        )
                        await manager.send_personal_message(error_msg, user.id)
                
                elif message_type == "call_end":
                    # Handle call end
                    try:
                        call_end = WSCallEnd(**message_payload)
                        call_id = call_end.call_id
                        ended_by = call_end.ended_by
                        
                        if call_id not in manager.active_calls:
                            raise ValueError("Call session not found")
                        
                        call_session = manager.active_calls[call_id]
                        
                        if ended_by != call_session.caller_id and ended_by != call_session.callee_id:
                            raise ValueError("User is not part of this call")
                        
                        peer_id = call_session.callee_id if ended_by == call_session.caller_id else call_session.caller_id
                        
                        call_session.state = "ended"
                        call_session.ended_at = datetime.utcnow()
                        
                        ended_msg = WSMessage(
                            type=WSMessageType.CALL_ENDED,
                            data=WSCallEnded(
                                call_id=call_id,
                                ended_by=ended_by,
                                reason=None
                            ).model_dump(mode='json'),
                            timestamp=datetime.utcnow()
                        )
                        await manager.send_personal_message(ended_msg, peer_id)
                        
                        del manager.active_calls[call_id]
                        
                        logger.info(f"Call ended: {call_id} by {ended_by}")
                        
                    except Exception as e:
                        logger.error(f"Error handling call_end: {e}")
                        error_msg = WSMessage(
                            type=WSMessageType.ERROR,
                            data=WSError(
                                message=f"Error processing call end: {str(e)}",
                                code="CALL_END_ERROR"
                            ).model_dump(mode='json'),
                            timestamp=datetime.utcnow()
                        )
                        await manager.send_personal_message(error_msg, user.id)
                
                elif message_type == "sdp_offer":
                    # Handle SDP offer
                    try:
                        sdp_offer = WSSDPOffer(**message_payload)
                        call_id = sdp_offer.call_id
                        from_user_id = sdp_offer.from_user_id
                        to_user_id = sdp_offer.to_user_id
                        
                        if from_user_id != user.id:
                            raise ValueError("Sender ID does not match authenticated user")
                        
                        # Verify call session exists
                        if call_id not in manager.active_calls:
                            raise ValueError("Call session not found")
                        
                        call_session = manager.active_calls[call_id]
                        
                        if from_user_id not in [call_session.caller_id, call_session.callee_id]:
                            raise ValueError("Sender is not part of this call")
                        if to_user_id not in [call_session.caller_id, call_session.callee_id]:
                            raise ValueError("Recipient is not part of this call")
                        
                        offer_msg = WSMessage(
                            type=WSMessageType.SDP_OFFER,
                            data=sdp_offer.model_dump(mode='json'),
                            timestamp=datetime.utcnow()
                        )
                        await manager.send_personal_message(offer_msg, to_user_id)
                        
                        logger.debug(f"SDP offer forwarded: {call_id} from {from_user_id} to {to_user_id}")
                        
                    except Exception as e:
                        logger.error(f"Error handling sdp_offer: {e}")
                        error_msg = WSMessage(
                            type=WSMessageType.ERROR,
                            data=WSError(
                                message=f"Error processing SDP offer: {str(e)}",
                                code="SDP_OFFER_ERROR"
                            ).model_dump(mode='json'),
                            timestamp=datetime.utcnow()
                        )
                        await manager.send_personal_message(error_msg, user.id)
                
                elif message_type == "sdp_answer":
                    # Handle SDP answer
                    try:
                        sdp_answer = WSSDPAnswer(**message_payload)
                        call_id = sdp_answer.call_id
                        from_user_id = sdp_answer.from_user_id
                        to_user_id = sdp_answer.to_user_id
                        
                        if from_user_id != user.id:
                            raise ValueError("Sender ID does not match authenticated user")
                        
                        if call_id not in manager.active_calls:
                            raise ValueError("Call session not found")
                        
                        call_session = manager.active_calls[call_id]
                        
                        if from_user_id not in [call_session.caller_id, call_session.callee_id]:
                            raise ValueError("Sender is not part of this call")
                        if to_user_id not in [call_session.caller_id, call_session.callee_id]:
                            raise ValueError("Recipient is not part of this call")
                        
                        answer_msg = WSMessage(
                            type=WSMessageType.SDP_ANSWER,
                            data=sdp_answer.model_dump(mode='json'),
                            timestamp=datetime.utcnow()
                        )
                        await manager.send_personal_message(answer_msg, to_user_id)
                        
                        logger.debug(f"SDP answer forwarded: {call_id} from {from_user_id} to {to_user_id}")
                        
                    except Exception as e:
                        logger.error(f"Error handling sdp_answer: {e}")
                        error_msg = WSMessage(
                            type=WSMessageType.ERROR,
                            data=WSError(
                                message=f"Error processing SDP answer: {str(e)}",
                                code="SDP_ANSWER_ERROR"
                            ).model_dump(mode='json'),
                            timestamp=datetime.utcnow()
                        )
                        await manager.send_personal_message(error_msg, user.id)
                
                elif message_type == "ice_candidate":
                    # Handle ICE candidate
                    try:
                        ice_candidate = WSICECandidate(**message_payload)
                        call_id = ice_candidate.call_id
                        from_user_id = ice_candidate.from_user_id
                        to_user_id = ice_candidate.to_user_id
                        
                        if from_user_id != user.id:
                            raise ValueError("Sender ID does not match authenticated user")
                        
                        if call_id not in manager.active_calls:
                            raise ValueError("Call session not found")
                        
                        call_session = manager.active_calls[call_id]
                        
                        if from_user_id not in [call_session.caller_id, call_session.callee_id]:
                            raise ValueError("Sender is not part of this call")
                        if to_user_id not in [call_session.caller_id, call_session.callee_id]:
                            raise ValueError("Recipient is not part of this call")
                        
                        candidate_msg = WSMessage(
                            type=WSMessageType.ICE_CANDIDATE,
                            data=ice_candidate.model_dump(mode='json'),
                            timestamp=datetime.utcnow()
                        )
                        await manager.send_personal_message(candidate_msg, to_user_id)
                        
                        logger.debug(f"ICE candidate forwarded: {call_id} from {from_user_id} to {to_user_id}")
                        
                    except Exception as e:
                        logger.error(f"Error handling ice_candidate: {e}")
                        error_msg = WSMessage(
                            type=WSMessageType.ERROR,
                            data=WSError(
                                message=f"Error processing ICE candidate: {str(e)}",
                                code="ICE_CANDIDATE_ERROR"
                            ).model_dump(mode='json'),
                            timestamp=datetime.utcnow()
                        )
                        await manager.send_personal_message(error_msg, user.id)
                
                else:
                    logger.warning(f"Unknown WebSocket message type: {message_type}")
                    error_msg = WSMessage(
                        type=WSMessageType.ERROR,
                        data=WSError(
                            message=f"Unknown message type: {message_type}",
                            code="UNKNOWN_MESSAGE_TYPE"
                        ).model_dump(mode='json'),
                        timestamp=datetime.utcnow()
                    )
                    await manager.send_personal_message(error_msg, user.id)
            
            except json.JSONDecodeError:
                logger.error(f"Invalid JSON received from {user.username}")
                error_msg = WSMessage(
                    type=WSMessageType.ERROR,
                    data=WSError(
                        message="Invalid JSON format",
                        code="INVALID_JSON"
                    ).model_dump(mode='json'),
                    timestamp=datetime.utcnow()
                )
                await manager.send_personal_message(error_msg, user.id)
            
            except Exception as e:
                logger.error(f"Error processing WebSocket message from {user.username}: {e}")
                error_msg = WSMessage(
                    type=WSMessageType.ERROR,
                    data=WSError(
                        message="Error processing message",
                        code="PROCESSING_ERROR",
                        details={"error": str(e)}
                    ).model_dump(mode='json'),
                    timestamp=datetime.utcnow()
                )
                await manager.send_personal_message(error_msg, user.id)
    
    except WebSocketDisconnect:
        manager.disconnect(user.id)
        
        # Broadcast user offline status
        offline_msg = WSMessage(
            type=WSMessageType.USER_OFFLINE,
            data=WSUserStatus(
                user_id=user.id,
                username=user.username,
                status="offline",
                last_seen_at=datetime.utcnow()
            ).model_dump(mode='json'),
            timestamp=datetime.utcnow()
        )
        await manager.broadcast_to_all(offline_msg)
        
        logger.info(f"User {user.username} ({user.id}) disconnected from WebSocket")
    
    except Exception as e:
        logger.error(f"Unexpected error in WebSocket connection for {user.username}: {e}")
        manager.disconnect(user.id)

