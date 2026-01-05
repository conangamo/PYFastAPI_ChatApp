import flet as ft
import cv2
import base64
import asyncio
import logging
from typing import Optional, Callable
from datetime import datetime

from ..utils.webrtc_handler import WebRTCHandler
from ..websocket.client import WebSocketClient, get_ws_client

logger = logging.getLogger(__name__)


class VideoCallPage(ft.UserControl):

    def __init__(
        self,
        page: ft.Page,
        call_id: str,
        local_user_id: str,
        remote_user_id: str,
        remote_username: str,
        is_caller: bool,
        on_call_end: Optional[Callable] = None,
        ws_client: Optional[WebSocketClient] = None
    ):

        super().__init__()
        self.page = page
        self.call_id = call_id
        self.local_user_id = local_user_id
        self.remote_user_id = remote_user_id
        self.remote_username = remote_username
        self.is_caller = is_caller
        self.on_call_end = on_call_end
        self.ws_client = ws_client or get_ws_client()
        
        self.webrtc_handler: Optional[WebRTCHandler] = None
        self.camera_cap: Optional[cv2.VideoCapture] = None
        self.camera_timer: Optional[ft.Timer] = None
        self.local_video_image: Optional[ft.Image] = None
        self.remote_video_image: Optional[ft.Image] = None
        self.status_text: Optional[ft.Text] = None
        self.end_call_button: Optional[ft.ElevatedButton] = None
        self.call_duration_text: Optional[ft.Text] = None
        self.duration_timer: Optional[ft.Timer] = None
        self.call_start_time: Optional[datetime] = None
        self.initialized = False
        self.closed = False
    
    def build(self):
        self.local_video_image = ft.Image(
            src_base64="",
            width=200,
            height=150,
            fit=ft.ImageFit.CONTAIN,
            border=ft.border.all(2, ft.colors.WHITE),
            border_radius=8
        )
        
        local_video_container = ft.Container(
            content=self.local_video_image,
            width=200,
            height=150,
            bgcolor=ft.colors.BLACK,
            border_radius=8,
            padding=4
        )
        
        # Remote video (main, full screen)
        self.remote_video_image = ft.Image(
            src_base64="",
            fit=ft.ImageFit.CONTAIN,
            expand=True
        )
        
        remote_video_container = ft.Container(
            content=self.remote_video_image,
            expand=True,
            bgcolor=ft.colors.BLACK,
            alignment=ft.alignment.center
        )
        
        self.status_text = ft.Text(
            value="Connecting...",
            size=18,
            color=ft.colors.WHITE,
            weight=ft.FontWeight.BOLD
        )
        
        self.call_duration_text = ft.Text(
            value="00:00",
            size=16,
            color=ft.colors.WHITE70
        )
        
        self.end_call_button = ft.ElevatedButton(
            text="End Call",
            icon=ft.icons.CALL_END,
            bgcolor=ft.colors.RED_600,
            color=ft.colors.WHITE,
            height=50,
            width=150,
            on_click=self._handle_end_call_click
        )
        
        controls_container = ft.Container(
            content=ft.Column(
                [
                    self.status_text,
                    self.call_duration_text,
                    self.end_call_button
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=10
            ),
            padding=20,
            bgcolor=ft.colors.with_opacity(0.7, ft.colors.BLACK),
            border_radius=10
        )
        
        # Main layout: Stack to overlay local video on remote video
        return ft.Stack(
            [
                remote_video_container,
                
                ft.Container(
                    content=local_video_container,
                    top=20,
                    right=20,
                    width=200,
                    height=150
                ),
                
                ft.Container(
                    content=controls_container,
                    bottom=30,
                    left=0,
                    right=0,
                    alignment=ft.alignment.bottom_center
                )
            ],
            expand=True
        )
    
    async def did_mount_async(self):
        if self.initialized:
            return
        
        try:
            # Setup camera preview
            await self._setup_camera_preview()
            
            # Initialize WebRTC
            await self._initialize_call()
            
            self.initialized = True
            self.call_start_time = datetime.now()
            self._start_call_duration_timer()
            
        except Exception as e:
            logger.error(f"Error initializing video call page: {e}")
            import traceback
            logger.error(traceback.format_exc())
            self.status_text.value = f"Error: {str(e)}"
            self.status_text.color = ft.colors.RED
            self.update()
    
    async def will_unmount_async(self):
        await self._cleanup()
    
    async def _setup_camera_preview(self):
        try:
            self.camera_cap = cv2.VideoCapture(0)
            if not self.camera_cap.isOpened():
                raise RuntimeError("Failed to open camera")
            
            self.camera_cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            self.camera_cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            
            self.camera_timer = ft.Timer(
                interval=33,  # ~30fps
                callback=self._update_camera_preview,
                repeat=True
            )
            self.camera_timer.start()
            
            logger.info("Camera preview setup completed")
        
        except Exception as e:
            logger.error(f"Error setting up camera preview: {e}")
            self.status_text.value = f"Camera error: {str(e)}"
            self.update()
    
    def _update_camera_preview(self, e=None):
        if not self.camera_cap or not self.camera_cap.isOpened():
            return
        
        try:
            ret, frame = self.camera_cap.read()
            if not ret:
                return
            
            frame = cv2.resize(frame, (200, 150))
            _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
            base64_frame = base64.b64encode(buffer).decode('utf-8')
            
            if self.local_video_image:
                self.local_video_image.src_base64 = base64_frame
                self.update()
        
        except Exception as e:
            logger.error(f"Error updating camera preview: {e}")
    
    async def _initialize_call(self):
        try:
            self.webrtc_handler = WebRTCHandler(
                call_id=self.call_id,
                local_user_id=self.local_user_id,
                remote_user_id=self.remote_user_id,
                is_caller=self.is_caller,
                ws_client=self.ws_client
            )
            
            self.webrtc_handler.set_remote_video_callback(self._on_remote_video_frame)
            self.webrtc_handler.set_connection_state_callback(self._on_connection_state_change)
            
            await self.webrtc_handler.initialize()
            
            if self.is_caller:
                await self._start_as_caller()
            else:
                self.status_text.value = "Waiting for connection..."
                self.update()
            
            logger.info("WebRTC call initialized")
        
        except Exception as e:
            logger.error(f"Error initializing call: {e}")
            import traceback
            logger.error(traceback.format_exc())
            raise
    
    async def _start_as_caller(self):
        try:
            self.status_text.value = "Creating connection..."
            self.update()
            
            sdp_offer = await self.webrtc_handler.create_offer()
            
            await self.ws_client.send_sdp_offer(
                call_id=self.call_id,
                from_user_id=self.local_user_id,
                to_user_id=self.remote_user_id,
                sdp=sdp_offer
            )
            
            self.status_text.value = "Connecting..."
            self.update()
            
            logger.info("SDP offer sent")
        
        except Exception as e:
            logger.error(f"Error starting as caller: {e}")
            self.status_text.value = f"Error: {str(e)}"
            self.status_text.color = ft.colors.RED
            self.update()
    
    def _on_remote_video_frame(self, frame):
        try:
            frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            _, buffer = cv2.imencode('.jpg', frame_bgr, [cv2.IMWRITE_JPEG_QUALITY, 85])
            base64_frame = base64.b64encode(buffer).decode('utf-8')
            
            if self.remote_video_image:
                self.remote_video_image.src_base64 = base64_frame
                self.update()
        
        except Exception as e:
            logger.error(f"Error processing remote video frame: {e}")
    
    def _on_connection_state_change(self, state: str):
        try:
            state_messages = {
                "new": "Initializing...",
                "connecting": "Connecting...",
                "connected": "Connected",
                "disconnected": "Disconnected",
                "failed": "Connection Failed",
                "closed": "Call Ended"
            }
            
            message = state_messages.get(state, state)
            self.status_text.value = message
            
            if state == "connected":
                self.status_text.color = ft.colors.GREEN
            elif state == "failed" or state == "closed":
                self.status_text.color = ft.colors.RED
            else:
                self.status_text.color = ft.colors.WHITE
            
            self.update()
            
            if state == "failed" or state == "closed":
                self.page.run_task(self._handle_end_call)
        
        except Exception as e:
            logger.error(f"Error handling connection state change: {e}")
    
    async def handle_sdp_offer(self, sdp: str):
        try:
            if not self.webrtc_handler:
                logger.error("WebRTC handler not initialized")
                return
            
            self.status_text.value = "Processing connection..."
            self.update()
            
            await self.webrtc_handler.handle_remote_description(sdp, "offer")
            sdp_answer = await self.webrtc_handler.create_answer()
            
            await self.ws_client.send_sdp_answer(
                call_id=self.call_id,
                from_user_id=self.local_user_id,
                to_user_id=self.remote_user_id,
                sdp=sdp_answer
            )
            
            self.status_text.value = "Connecting..."
            self.update()
            
            logger.info("SDP answer sent")
        
        except Exception as e:
            logger.error(f"Error handling SDP offer: {e}")
            self.status_text.value = f"Error: {str(e)}"
            self.status_text.color = ft.colors.RED
            self.update()
    
    async def handle_sdp_answer(self, sdp: str):
        try:
            if not self.webrtc_handler:
                logger.error("WebRTC handler not initialized")
                return
            
            await self.webrtc_handler.handle_remote_description(sdp, "answer")
            
            self.status_text.value = "Connecting..."
            self.update()
            
            logger.info("SDP answer processed")
        
        except Exception as e:
            logger.error(f"Error handling SDP answer: {e}")
            self.status_text.value = f"Error: {str(e)}"
            self.status_text.color = ft.colors.RED
            self.update()
    
    async def handle_ice_candidate(self, candidate: str, sdp_mid: Optional[str] = None, 
                                   sdp_mline_index: Optional[int] = None):
        try:
            if not self.webrtc_handler:
                logger.error("WebRTC handler not initialized")
                return
            
            await self.webrtc_handler.add_ice_candidate(
                candidate=candidate,
                sdp_mid=sdp_mid,
                sdp_mline_index=sdp_mline_index
            )
            
            logger.debug("ICE candidate added")
        
        except Exception as e:
            logger.error(f"Error handling ICE candidate: {e}")
    
    def _handle_end_call_click(self, e):
        self.page.run_task(self._handle_end_call)
    
    async def _handle_end_call(self):
        if self.closed:
            return
        
        self.closed = True
        
        try:
            if self.ws_client and self.ws_client.connected:
                await self.ws_client.send_call_end(
                    call_id=self.call_id,
                    ended_by=self.local_user_id
                )
            
            await self._cleanup()
            
            if self.on_call_end:
                self.on_call_end()
        
        except Exception as e:
            logger.error(f"Error ending call: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    async def _cleanup(self):
        try:
            if self.duration_timer:
                self.duration_timer.cancel()
                self.duration_timer = None
            
            if self.camera_timer:
                self.camera_timer.cancel()
                self.camera_timer = None
            
            if self.camera_cap and self.camera_cap.isOpened():
                self.camera_cap.release()
                self.camera_cap = None
            
            if self.webrtc_handler:
                await self.webrtc_handler.close()
                self.webrtc_handler = None
            
            logger.info("Video call page cleaned up")
        
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
    
    def _start_call_duration_timer(self):
        self.duration_timer = ft.Timer(
            interval=1000,  # 1 second
            callback=self._update_call_duration,
            repeat=True
        )
        self.duration_timer.start()
    
    def _update_call_duration(self, e=None):
        if not self.call_start_time:
            return
        
        try:
            duration = datetime.now() - self.call_start_time
            total_seconds = int(duration.total_seconds())
            minutes = total_seconds // 60
            seconds = total_seconds % 60
            
            duration_str = f"{minutes:02d}:{seconds:02d}"
            
            if self.call_duration_text:
                self.call_duration_text.value = duration_str
                self.update()
        
        except Exception as e:
            logger.error(f"Error updating call duration: {e}")

