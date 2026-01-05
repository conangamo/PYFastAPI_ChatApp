import asyncio
import websockets
import json
from typing import Optional, Callable, Dict, Any
import logging

from ..config import config


logger = logging.getLogger(__name__)


class WebSocketClient:
    def __init__(self, token: str):
        self.token = token
        self.url = f"{config.WS_ENDPOINT}?token={token}"
        self.ws: Optional[websockets.WebSocketClientProtocol] = None
        self.connected = False
        self.message_callbacks: list[Callable] = []
        self.call_callbacks: list[Callable] = []  # Callbacks for video call messages
        self.listen_task: Optional[asyncio.Task] = None
    
    def add_message_callback(self, callback: Callable[[Dict[str, Any]], None]):
        self.message_callbacks.append(callback)
    
    def remove_message_callback(self, callback: Callable):
        if callback in self.message_callbacks:
            self.message_callbacks.remove(callback)
    
    def add_call_callback(self, callback: Callable[[Dict[str, Any]], None]):
        """Add callback for video call messages"""
        self.call_callbacks.append(callback)
    
    def remove_call_callback(self, callback: Callable):
        """Remove callback for video call messages"""
        if callback in self.call_callbacks:
            self.call_callbacks.remove(callback)
    
    async def connect(self):
        """Connect to WebSocket server"""
        try:
            if self.ws:
                try:
                    await self.ws.close()
                except Exception as e:
                    logger.warning(f"Error closing existing WebSocket: {e}")
                self.ws = None
            
            if self.listen_task and not self.listen_task.done():
                logger.info("Cancelling existing listen task...")
                self.listen_task.cancel()
                try:
                    await self.listen_task
                except asyncio.CancelledError:
                    pass
                logger.info("Existing listen task cancelled")
            
            self.connected = False
            self.listen_task = None
            
            logger.info(f"Connecting to WebSocket: {config.WS_ENDPOINT}")
            self.ws = await websockets.connect(self.url)
            self.connected = True
            logger.info("WebSocket connected!")
            
            self.listen_task = asyncio.create_task(self._listen())
            logger.info("Listen task started")
        except Exception as e:
            logger.error(f"WebSocket connection error: {e}")
            import traceback
            logger.error(traceback.format_exc())
            self.connected = False
            self.ws = None
            raise
    
    async def disconnect(self):
        self.connected = False
        
        if self.listen_task:
            self.listen_task.cancel()
            try:
                await self.listen_task
            except asyncio.CancelledError:
                pass
        
        if self.ws:
            try:
                await self.ws.close()
            except Exception as e:
                logger.warning(f"Error closing WebSocket: {e}")
            self.ws = None
        
        logger.info("WebSocket disconnected")
    
    async def _listen(self):
        try:
            while self.connected and self.ws:
                try:
                    message = await self.ws.recv()
                    data = json.loads(message)
                    
                    msg_type = data.get('type', 'unknown')
                    logger.info(f"WebSocket RAW message received: type={msg_type}")
                    logger.info(f"Full message data: {json.dumps(data, indent=2, default=str)}")
                    
                    call_message_types = [
                        'call_invite_sent', 'call_incoming', 'call_accepted', 
                        'call_reject', 'call_ended', 'sdp_offer', 'sdp_answer', 
                        'ice_candidate'
                    ]
                    
                    if msg_type in call_message_types:
                        for callback in self.call_callbacks:
                            try:
                                callback(data)
                            except Exception as e:
                                logger.error(f"Error in call callback: {e}")
                                import traceback
                                logger.error(traceback.format_exc())
                    else:
                        for callback in self.message_callbacks:
                            try:
                                callback(data)
                            except Exception as e:
                                logger.error(f"Error in message callback: {e}")
                                import traceback
                                logger.error(traceback.format_exc())
                
                except websockets.exceptions.ConnectionClosed:
                    logger.warning("WebSocket connection closed!")
                    self.connected = False
                    break
                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON from WebSocket: {e}")
                    continue
                except Exception as e:
                    logger.error(f"Error in WebSocket listen loop: {e}")
                    import traceback
                    logger.error(traceback.format_exc())
                    continue
        
        except asyncio.CancelledError:
            logger.info("WebSocket listen task cancelled")
        except Exception as e:
            logger.error(f"Fatal error in WebSocket listen: {e}")
            import traceback
            logger.error(traceback.format_exc())
        finally:
            logger.info("_listen() task finished")
    
    async def send(self, message_type: str, data: Dict[str, Any]):
        if not self.connected or not self.ws:
            logger.warning("WebSocket not connected, cannot send message")
            return
        
        try:
            message = {
                "type": message_type,
                "data": data
            }
            await self.ws.send(json.dumps(message))
            logger.debug(f"WebSocket message sent: {message_type}")
        except Exception as e:
            logger.error(f"Error sending WebSocket message: {e}")
    
    async def send_typing(self, conversation_id: str, is_typing: bool):
        await self.send("typing", {
            "conversation_id": conversation_id,
            "is_typing": is_typing
        })
    
    async def send_ping(self):
        await self.send("ping", {})
    
    async def send_call_invite(self, call_id: str, caller_id: str, callee_id: str, conversation_id: str):
        await self.send("call_invite", {
            "call_id": call_id,
            "caller_id": caller_id,
            "callee_id": callee_id,
            "conversation_id": conversation_id
        })
    
    async def send_call_accept(self, call_id: str, caller_id: str, callee_id: str):
        await self.send("call_accept", {
            "call_id": call_id,
            "caller_id": caller_id,
            "callee_id": callee_id
        })
    
    async def send_call_reject(self, call_id: str, caller_id: str, callee_id: str, reason: Optional[str] = None):
        await self.send("call_reject", {
            "call_id": call_id,
            "caller_id": caller_id,
            "callee_id": callee_id,
            "reason": reason
        })
    
    async def send_call_end(self, call_id: str, ended_by: str):
        await self.send("call_end", {
            "call_id": call_id,
            "ended_by": ended_by
        })
    
    async def send_sdp_offer(self, call_id: str, from_user_id: str, to_user_id: str, sdp: str):
        await self.send("sdp_offer", {
            "call_id": call_id,
            "from_user_id": from_user_id,
            "to_user_id": to_user_id,
            "sdp": sdp,
            "sdp_type": "offer"
        })
    
    async def send_sdp_answer(self, call_id: str, from_user_id: str, to_user_id: str, sdp: str):
        await self.send("sdp_answer", {
            "call_id": call_id,
            "from_user_id": from_user_id,
            "to_user_id": to_user_id,
            "sdp": sdp,
            "sdp_type": "answer"
        })
    
    async def send_ice_candidate(self, call_id: str, from_user_id: str, to_user_id: str, 
                                 candidate: str, sdp_mid: Optional[str] = None, 
                                 sdp_mline_index: Optional[int] = None):
        await self.send("ice_candidate", {
            "call_id": call_id,
            "from_user_id": from_user_id,
            "to_user_id": to_user_id,
            "candidate": candidate,
            "sdp_mid": sdp_mid,
            "sdp_mline_index": sdp_mline_index
        })


ws_client: Optional[WebSocketClient] = None


def get_ws_client() -> Optional[WebSocketClient]:
    return ws_client


def set_ws_client(client: Optional[WebSocketClient]):
    global ws_client
    ws_client = client

