"""
WebSocket client for real-time communication
"""
import asyncio
import websockets
import json
from typing import Optional, Callable, Dict, Any
import logging

from ..config import config


logger = logging.getLogger(__name__)


class WebSocketClient:
    """
    WebSocket client for real-time messaging
    Handles connection, message listening, and sending
    """
    
    def __init__(self, token: str):
        """Initialize WebSocket client"""
        self.token = token
        self.url = f"{config.WS_ENDPOINT}?token={token}"
        self.ws: Optional[websockets.WebSocketClientProtocol] = None
        self.connected = False
        self.message_callbacks: list[Callable] = []
        self.listen_task: Optional[asyncio.Task] = None
        
    
    def add_message_callback(self, callback: Callable[[Dict[str, Any]], None]):
        """Add callback for incoming messages"""
        self.message_callbacks.append(callback)
    
    def remove_message_callback(self, callback: Callable):
        """Remove callback"""
        if callback in self.message_callbacks:
            self.message_callbacks.remove(callback)
    
    async def connect(self):
        """Connect to WebSocket server"""
        try:
            # Close existing connection if any
            if self.ws:
                try:
                    await self.ws.close()
                except Exception as e:
                    logger.warning(f"Error closing existing WebSocket: {e}")
                self.ws = None
            
            # Cancel existing listen task if any and wait for it to finish
            if self.listen_task and not self.listen_task.done():
                logger.info("Cancelling existing listen task...")
                self.listen_task.cancel()
                try:
                    await self.listen_task
                except asyncio.CancelledError:
                    pass
                logger.info("Existing listen task cancelled")
            
            # Reset state
            self.connected = False
            self.listen_task = None
            
            logger.info(f"Connecting to WebSocket: {config.WS_ENDPOINT}")
            self.ws = await websockets.connect(self.url)
            self.connected = True
            logger.info("✅ WebSocket connected!")
            
            # Start listening in background (only one task at a time)
            self.listen_task = asyncio.create_task(self._listen())
            logger.info("✅ Listen task started")
        except Exception as e:
            logger.error(f"❌ WebSocket connection error: {e}")
            import traceback
            logger.error(traceback.format_exc())
            self.connected = False
            self.ws = None
            raise
    
    async def disconnect(self):
        """Disconnect from WebSocket server"""
        self.connected = False
        
        # Cancel listen task
        if self.listen_task:
            self.listen_task.cancel()
            try:
                await self.listen_task
            except asyncio.CancelledError:
                pass
        
        # Close connection
        if self.ws:
            try:
                await self.ws.close()
            except Exception as e:
                logger.warning(f"Error closing WebSocket: {e}")
            self.ws = None
        
        logger.info("✅ WebSocket disconnected")
    
    async def _listen(self):
        """Listen for incoming messages"""
        try:
            while self.connected and self.ws:
                try:
                    message = await self.ws.recv()
                    data = json.loads(message)
                    
                    msg_type = data.get('type', 'unknown')
                    logger.info(f"📥 WebSocket RAW message received: type={msg_type}")
                    logger.info(f"📥 Full message data: {json.dumps(data, indent=2, default=str)}")
                    
                    # Call all callbacks
                    for callback in self.message_callbacks:
                        try:
                            callback(data)
                        except Exception as e:
                            logger.error(f"❌ Error in message callback: {e}")
                            import traceback
                            logger.error(traceback.format_exc())
                
                except websockets.exceptions.ConnectionClosed:
                    logger.warning("⚠️⚠️⚠️ WebSocket connection closed!")
                    self.connected = False
                    # Don't reconnect here - break and let the connection be handled externally
                    # Reconnecting here causes multiple coroutines to call recv() simultaneously
                    break
                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON from WebSocket: {e}")
                    # Continue listening on JSON errors
                    continue
                except Exception as e:
                    logger.error(f"Error in WebSocket listen loop: {e}")
                    import traceback
                    logger.error(traceback.format_exc())
                    # Continue listening on other errors (but log them)
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
        """
        Send message through WebSocket
        
        Args:
            message_type: Type of message (e.g., "typing")
            data: Message data
        """
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
        """
        Send typing indicator
        
        Args:
            conversation_id: Conversation ID
            is_typing: True if user is typing, False if stopped
        """
        await self.send("typing", {
            "conversation_id": conversation_id,
            "is_typing": is_typing
        })
    
    async def send_ping(self):
        """Send ping to keep connection alive"""
        await self.send("ping", {})


# Global WebSocket client instance
ws_client: Optional[WebSocketClient] = None


def get_ws_client() -> Optional[WebSocketClient]:
    """Get global WebSocket client instance"""
    return ws_client


def set_ws_client(client: Optional[WebSocketClient]):
    """Set global WebSocket client instance"""
    global ws_client
    ws_client = client

