import flet as ft
import base64
import asyncio
import logging
from typing import Optional, Callable
from datetime import datetime

# Optional imports for video call functionality
try:
    import cv2
    CV2_AVAILABLE = True
    print(f"[OK] OpenCV imported successfully, version: {cv2.__version__}")
except ImportError as e:
    CV2_AVAILABLE = False
    cv2 = None
    print(f"[ERROR] Failed to import OpenCV: {e}")
except Exception as e:
    CV2_AVAILABLE = False
    cv2 = None
    print(f"[ERROR] Error importing OpenCV: {e}")
    import traceback
    traceback.print_exc()

try:
    from ..utils.webrtc_handler import WebRTCHandler
    WEBRTC_AVAILABLE = True
except (ImportError, AttributeError):
    WEBRTC_AVAILABLE = False
    WebRTCHandler = None

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
        self.camera_cap = None
        self.camera_timer_task: Optional[asyncio.Task] = None
        self.local_video_image: Optional[ft.Image] = None
        self.remote_video_image: Optional[ft.Image] = None
        self.status_text: Optional[ft.Text] = None
        self.end_call_button: Optional[ft.ElevatedButton] = None
        self.call_duration_text: Optional[ft.Text] = None
        self.duration_timer_task: Optional[asyncio.Task] = None
        self.call_start_time: Optional[datetime] = None
        self.initialized = False
        self.closed = False
    
    def build(self):
        placeholder_base64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        
        self.local_video_image = ft.Image(
            src_base64=placeholder_base64,
            width=200,
            height=150,
            fit=ft.ImageFit.CONTAIN,
            border_radius=8
        )
        
        local_video_container = ft.Container(
            content=self.local_video_image,
            width=200,
            height=150,
            bgcolor=ft.colors.BLACK,
            border=ft.border.all(2, ft.colors.WHITE),
            border_radius=8,
            padding=4
        )
        
        self.remote_video_image = ft.Image(
            src_base64=placeholder_base64,
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
        print("=" * 60)
        print("did_mount_async CALLED!")
        print(f"initialized: {self.initialized}")
        print("=" * 60)
        
        if self.initialized:
            print("Video call page already initialized, skipping...")
            return
        
        try:
            logger.info("Video call page mounting, initializing...")
            
            await self._setup_camera_preview()
            
            await self._initialize_call()
            
            self.initialized = True
            self.call_start_time = datetime.now()
            self._start_call_duration_timer()
            
            logger.info("Video call page initialized successfully!")
            
        except Exception as e:
            print(f"ERROR initializing video call page: {e}")
            import traceback
            traceback.print_exc()
            logger.error(f"Error initializing video call page: {e}")
            if self.status_text and self.page:
                try:
                    self.status_text.value = f"Error: {str(e)}"
                    self.status_text.color = ft.colors.RED
                    self.update()
                except:
                    pass
    
    async def will_unmount_async(self):
        await self._cleanup()
    
    async def _setup_camera_preview(self):
        print("_setup_camera_preview called")
        print(f"CV2_AVAILABLE check: {CV2_AVAILABLE}")
        print(f"cv2 object: {cv2}")
        
        if not CV2_AVAILABLE:
            print("ERROR: OpenCV not available!")
            print("Attempting to import cv2 again to see error...")
            try:
                import cv2 as cv2_retry
                print(f"Direct import successful! Version: {cv2_retry.__version__}")
                # Try to use it anyway by updating module-level variables
                import sys
                import importlib
                # Update the module's cv2 reference
                current_module = sys.modules[__name__]
                current_module.cv2 = cv2_retry
                current_module.CV2_AVAILABLE = True
                # Also update globals for this function
                globals()['cv2'] = cv2_retry
                globals()['CV2_AVAILABLE'] = True
                print("✓ OpenCV made available after retry")
            except Exception as e:
                print(f"✗ Direct import also failed: {e}")
                import traceback
                traceback.print_exc()
                logger.error("OpenCV not available. Please install: pip install opencv-python")
                if self.status_text:
                    self.status_text.value = "Camera not available (OpenCV missing)"
                    self.update()
                return
        
        # Double check after retry - use module-level cv2
        import sys
        current_module = sys.modules[__name__]
        actual_cv2 = getattr(current_module, 'cv2', None)
        actual_available = getattr(current_module, 'CV2_AVAILABLE', False)
        
        if not actual_available or actual_cv2 is None:
            logger.error("OpenCV not available. Please install: pip install opencv-python")
            if self.status_text:
                self.status_text.value = "Camera not available (OpenCV missing)"
                self.update()
            return
        
        # Use the actual cv2 from module
        cv2_to_use = actual_cv2
        
        try:
            logger.info("Attempting to open camera with optimized settings...")
            camera_opened = False
            
            for camera_idx in [0, 1, 2]:
                try:
                    print(f"Trying camera index {camera_idx} with CAP_DSHOW...")
                    # Ưu tiên DirectShow backend (ổn định nhất trên Windows)
                    test_cap = cv2_to_use.VideoCapture(camera_idx, cv2_to_use.CAP_DSHOW)
                    
                    if not test_cap.isOpened():
                        print(f"CAP_DSHOW failed for index {camera_idx}, trying default backend...")
                        test_cap.release()
                        test_cap = cv2_to_use.VideoCapture(camera_idx)  # Fallback
                    
                    if test_cap.isOpened():
                        # Set properties ngay sau khi mở thành công
                        fourcc = cv2_to_use.VideoWriter_fourcc(*'MJPG')
                        test_cap.set(cv2_to_use.CAP_PROP_FOURCC, fourcc)
                        test_cap.set(cv2_to_use.CAP_PROP_FRAME_WIDTH, 1280)
                        test_cap.set(cv2_to_use.CAP_PROP_FRAME_HEIGHT, 720)
                        test_cap.set(cv2_to_use.CAP_PROP_FPS, 30)
                        
                        # Camera warm-up: Đọc và discard một vài frame đầu tiên
                        # Frame đầu tiên thường là trắng/đen do camera chưa khởi động xong
                        print(f"Warming up camera {camera_idx}...")
                        for warmup_idx in range(5):  # Discard 5 frames đầu
                            ret, _ = test_cap.read()
                            if not ret:
                                break
                            await asyncio.sleep(0.1)  # Đợi giữa các frame
                        
                        # Test đọc frame sau warm-up
                        ret, frame = test_cap.read()
                        if ret and frame is not None:
                            frame_min = frame.min()
                            frame_max = frame.max()
                            frame_mean = frame.mean()
                            
                            # Kiểm tra frame có hợp lệ không (không phải trắng/đen hoàn toàn)
                            if frame_min == frame_max and (frame_min == 0 or frame_min == 255):
                                print(f"Camera {camera_idx} frame is uniform (min=max={frame_min}), trying next camera...")
                                test_cap.release()
                                continue
                            
                            # Logging chi tiết để debug white screen
                            print(f"✓ Camera {camera_idx} opened successfully!")
                            print(f"   Frame shape: {frame.shape}")
                            print(f"   Frame stats: min={frame_min}, max={frame_max}, mean={frame_mean:.2f}")
                            
                            self.camera_cap = test_cap
                            camera_opened = True
                            logger.info(f"Camera opened at index {camera_idx} (backend: {'DirectShow' if test_cap.get(cv2_to_use.CAP_PROP_BACKEND) == cv2_to_use.CAP_DSHOW else 'Default'})")
                            break
                        else:
                            print(f"Camera {camera_idx} opened but frame is empty or white")
                            test_cap.release()
                    else:
                        test_cap.release()
                        
                except Exception as e:
                    print(f"Exception opening camera {camera_idx}: {e}")
                    if 'test_cap' in locals() and test_cap:
                        test_cap.release()
            
            if not camera_opened:
                raise RuntimeError("Không thể mở bất kỳ camera nào. Kiểm tra quyền truy cập và thiết bị.")
            
            if self.status_text:
                self.status_text.value = "Camera ready"
                self.update()
            
            # Start preview loop
            async def camera_update_loop():
                frame_count = 0
                print("Camera preview loop starting...")
                print(f"Initial state: closed={self.closed}, camera_cap={self.camera_cap is not None}")
                
                while True:
                    # Check conditions
                    if self.closed:
                        print("Loop stopped: self.closed is True")
                        break
                    if not self.camera_cap:
                        print("Loop stopped: camera_cap is None")
                        break
                    if not self.camera_cap.isOpened():
                        print("Loop stopped: camera_cap is not opened")
                        break
                    
                    try:
                        self._update_camera_preview()
                        frame_count += 1
                        if frame_count % 30 == 0:
                            print(f"Local preview running - frames processed: {frame_count}")
                        await asyncio.sleep(1/30)  # ~30 FPS
                    except asyncio.CancelledError:
                        print("Camera preview loop cancelled")
                        break
                    except Exception as e:
                        print(f"Error in camera preview loop: {e}")
                        logger.error(f"Error in camera preview loop: {e}")
                        import traceback
                        logger.error(traceback.format_exc())
                        # Don't break immediately, try to continue
                        await asyncio.sleep(1/30)
                
                print(f"Camera preview loop ended. Total frames: {frame_count}")
            
            self.camera_timer_task = asyncio.create_task(camera_update_loop())
            logger.info("Camera preview loop started")
            
        except Exception as e:
            print(f"ERROR setting up camera preview: {e}")
            import traceback
            traceback.print_exc()
            logger.error(f"Error setting up camera preview: {e}")
            if self.status_text:
                self.status_text.value = f"Camera error: {str(e)}"
                self.status_text.color = ft.colors.RED
                self.update()
    
    def _update_camera_preview(self, e=None):
        # Get actual cv2 from module
        import sys
        current_module = sys.modules[__name__]
        cv2_to_use = getattr(current_module, 'cv2', None)
        
        if not cv2_to_use:
            return
            
        if not self.camera_cap:
            return
            
        if not self.camera_cap.isOpened():
            return
        
        try:
            ret, frame = self.camera_cap.read()
            if not ret or frame is None:
                logger.warning("Failed to read frame from camera")
                return
            
            # Kiểm tra frame có hợp lệ không (không phải trắng/đen hoàn toàn)
            frame_min = frame.min()
            frame_max = frame.max()
            if frame_min == frame_max and (frame_min == 0 or frame_min == 255):
                # Frame trắng/đen, skip frame này
                if not hasattr(self, '_white_frame_count'):
                    self._white_frame_count = 0
                self._white_frame_count += 1
                if self._white_frame_count % 30 == 0:  # Log mỗi 30 frame trắng
                    logger.warning(f"Skipping white/black frame (count: {self._white_frame_count})")
                return
            
            # Reset counter nếu frame hợp lệ
            if hasattr(self, '_white_frame_count'):
                self._white_frame_count = 0
            
            # Logging mỗi 60 frame (~2 giây) để không spam console
            if hasattr(self, '_frame_log_counter'):
                self._frame_log_counter += 1
            else:
                self._frame_log_counter = 0
                
            if self._frame_log_counter % 60 == 0:
                print(f"Local frame: shape={frame.shape}, min={frame_min}, max={frame_max}, mean={frame.mean():.2f}")
            
            # Flip ngang để mirror (tự nhiên khi nhìn mình)
            frame = cv2_to_use.flip(frame, 1)
            
            # Resize cho local preview nhỏ
            frame = cv2_to_use.resize(frame, (200, 150))
            
            # Encode to JPEG
            _, buffer = cv2_to_use.imencode('.jpg', frame, [cv2_to_use.IMWRITE_JPEG_QUALITY, 85])
            base64_frame = base64.b64encode(buffer).decode('utf-8')
            
            if self.local_video_image and self.page:
                self.local_video_image.src_base64 = base64_frame
                self.update()
        
        except Exception as e:
            logger.error(f"Error updating local camera preview: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    async def _initialize_call(self):
        if not WEBRTC_AVAILABLE or not WebRTCHandler:
            logger.error("WebRTC handler not available")
            self.status_text.value = "WebRTC not available"
            self.update()
            return
        
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
        if not CV2_AVAILABLE:
            return
        
        try:
            # frame từ aiortc là RGB → chuyển sang BGR để encode
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
            
            if state in ["failed", "closed"]:
                self.page.run_task(self._handle_end_call)
        
        except Exception as e:
            logger.error(f"Error handling connection state change: {e}")
    
    async def handle_sdp_offer(self, sdp: str):
        try:
            if not self.webrtc_handler:
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
                return
            
            await self.webrtc_handler.add_ice_candidate(
                candidate=candidate,
                sdp_mid=sdp_mid,
                sdp_mline_index=sdp_mline_index
            )
            
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
    
    async def _cleanup(self):
        try:
            if self.duration_timer_task and not self.duration_timer_task.done():
                self.duration_timer_task.cancel()
                try:
                    await self.duration_timer_task
                except asyncio.CancelledError:
                    pass
            
            if self.camera_timer_task and not self.camera_timer_task.done():
                self.camera_timer_task.cancel()
                try:
                    await self.camera_timer_task
                except asyncio.CancelledError:
                    pass
            
            if CV2_AVAILABLE and self.camera_cap and self.camera_cap.isOpened():
                self.camera_cap.release()
                self.camera_cap = None
            
            if self.webrtc_handler:
                await self.webrtc_handler.close()
                self.webrtc_handler = None
            
            logger.info("Video call page cleaned up")
        
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
    
    def _start_call_duration_timer(self):
        async def duration_update_loop():
            while self.call_start_time and not self.closed:
                try:
                    self._update_call_duration()
                    await asyncio.sleep(1)
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Error in duration update loop: {e}")
                    break
        
        self.duration_timer_task = asyncio.create_task(duration_update_loop())
    
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

