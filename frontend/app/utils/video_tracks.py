import cv2
import numpy as np
import asyncio
import logging
from typing import Optional, Callable
from fractions import Fraction
from av import VideoFrame
from aiortc import VideoStreamTrack

logger = logging.getLogger(__name__)


class OpenCVVideoTrack(VideoStreamTrack):
    
    def __init__(self, camera_index: int = 0, width: int = 640, height: int = 480, fps: int = 30):

        super().__init__()
        self.camera_index = camera_index
        self.width = width
        self.height = height
        self.fps = fps
        self.cap: Optional[cv2.VideoCapture] = None
        self.running = False
        self.frame_time = 1.0 / fps
        
    async def start(self):
        try:
            import platform
            camera_opened = False
            
            # Try multiple camera indices if default fails (useful when testing 2 users on same machine)
            camera_indices_to_try = [self.camera_index]
            if self.camera_index == 0:
                # If using default camera, also try other indices in case of conflict
                camera_indices_to_try = [0, 1, 2]
            
            for cam_idx in camera_indices_to_try:
                try:
                    # Use DirectShow backend on Windows (fixes white frame issue)
                    if platform.system() == "Windows":
                        try:
                            test_cap = cv2.VideoCapture(cam_idx, cv2.CAP_DSHOW)
                            if not test_cap.isOpened():
                                logger.warning(f"DirectShow failed for camera {cam_idx}, trying default backend")
                                test_cap.release()
                                test_cap = cv2.VideoCapture(cam_idx)
                        except Exception as e:
                            logger.warning(f"Error opening camera {cam_idx} with DirectShow: {e}, trying default")
                            test_cap = cv2.VideoCapture(cam_idx)
                    else:
                        test_cap = cv2.VideoCapture(cam_idx)
                    
                    if not test_cap.isOpened():
                        test_cap.release()
                        continue
                    
                    # Set codec, resolution and FPS (same as video_call_page.py)
                    try:
                        fourcc = cv2.VideoWriter_fourcc(*'MJPG')
                        test_cap.set(cv2.CAP_PROP_FOURCC, fourcc)
                    except:
                        pass  # Some cameras don't support MJPG
                    
                    test_cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
                    test_cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
                    test_cap.set(cv2.CAP_PROP_FPS, self.fps)
                    
                    # Camera warm-up: Đọc và discard một vài frame đầu tiên
                    # Frame đầu tiên thường là trắng/đen do camera chưa khởi động xong
                    logger.info(f"Warming up camera {cam_idx}...")
                    for warmup_idx in range(5):  # Discard 5 frames đầu
                        ret, _ = test_cap.read()
                        if not ret:
                            break
                        await asyncio.sleep(0.1)  # Đợi giữa các frame
                    
                    # Test read frame sau warm-up
                    ret, test_frame = test_cap.read()
                    if ret and test_frame is not None:
                        frame_min = test_frame.min()
                        frame_max = test_frame.max()
                        
                        # Check if frame is valid (not all black/white)
                        if frame_min == frame_max and (frame_min == 0 or frame_min == 255):
                            logger.warning(f"Camera {cam_idx} opened but frame is uniform (min=max={frame_min}), trying next camera")
                            test_cap.release()
                            continue
                        
                        # Frame hợp lệ
                        self.cap = test_cap
                        self.camera_index = cam_idx  # Update to actual camera index used
                        camera_opened = True
                        logger.info(f"OpenCVVideoTrack started: camera={cam_idx}, {self.width}x{self.height}@{self.fps}fps, frame_shape={test_frame.shape}, stats: min={frame_min}, max={frame_max}, mean={test_frame.mean():.2f}")
                        break
                    else:
                        logger.warning(f"Camera {cam_idx} opened but cannot read frames, trying next camera")
                        test_cap.release()
                except Exception as e:
                    logger.warning(f"Error trying camera {cam_idx}: {e}")
                    if 'test_cap' in locals() and test_cap:
                        test_cap.release()
                    continue
            
            if not camera_opened:
                raise RuntimeError(f"Failed to open any camera. Tried indices: {camera_indices_to_try}")
            
            self.running = True
        except Exception as e:
            logger.error(f"Error starting OpenCVVideoTrack: {e}")
            if self.cap:
                self.cap.release()
                self.cap = None
            raise
    
    async def stop(self):
        self.running = False
        if self.cap and self.cap.isOpened():
            self.cap.release()
            self.cap = None
            logger.info("OpenCVVideoTrack stopped and camera released")
    
    async def recv(self):
        if not self.running or not self.cap:
            raise RuntimeError("OpenCVVideoTrack is not running")
        
        if not self.cap.isOpened():
            raise RuntimeError("Camera is not opened")
        
        ret, frame = self.cap.read()
        if not ret or frame is None:
            logger.warning("Failed to read frame from camera, using black frame")
            frame = np.zeros((self.height, self.width, 3), dtype=np.uint8)
        else:
            # Check if frame is valid (not all black/white - indicates white screen issue)
            frame_min = frame.min()
            frame_max = frame.max()
            if frame_min == frame_max and (frame_min == 0 or frame_min == 255):
                # Frame is all black (0) or all white (255) - skip this frame
                # Don't log every time to avoid spam, only log occasionally
                if not hasattr(self, '_white_frame_warning_count'):
                    self._white_frame_warning_count = 0
                self._white_frame_warning_count += 1
                if self._white_frame_warning_count % 30 == 0:  # Log mỗi 30 frame
                    logger.warning(f"Frame appears to be uniform (min=max={frame_min}), skipping. "
                                 f"This may indicate camera conflict or warm-up needed.")
                # Use previous frame or black frame instead
                if hasattr(self, '_last_valid_frame'):
                    frame = self._last_valid_frame
                else:
                    frame = np.zeros((self.height, self.width, 3), dtype=np.uint8)
            else:
                # Frame hợp lệ, lưu lại để dùng nếu frame sau bị trắng
                self._last_valid_frame = frame.copy()
                if hasattr(self, '_white_frame_warning_count'):
                    self._white_frame_warning_count = 0
        
        if frame.shape[1] != self.width or frame.shape[0] != self.height:
            frame = cv2.resize(frame, (self.width, self.height))
        
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        video_frame = VideoFrame.from_ndarray(frame_rgb, format="rgb24")
        video_frame.pts = self._next_timestamp()
        video_frame.time_base = Fraction(1, 90000)  # 90kHz clock
        
        return video_frame
    
    def _next_timestamp(self):
        if not hasattr(self, '_timestamp'):
            self._timestamp = 0
        self._timestamp += int(90000 / self.fps)  # 90kHz clock
        return self._timestamp


class RemoteVideoTrackProcessor:
    
    def __init__(self, on_frame: Optional[Callable[[np.ndarray], None]] = None):
        self.on_frame = on_frame
        self.running = False
        self.current_frame: Optional[np.ndarray] = None
    
    async def process_track(self, track: VideoStreamTrack):
        self.running = True
        logger.info("RemoteVideoTrackProcessor started")
        
        try:
            while self.running:
                try:
                    frame = await track.recv()
                    img = frame.to_ndarray(format="rgb24")
                    self.current_frame = img
                    
                    if self.on_frame:
                        try:
                            self.on_frame(img)
                        except Exception as e:
                            logger.error(f"Error in on_frame callback: {e}")
                
                except Exception as e:
                    if self.running:
                        logger.error(f"Error processing remote video frame: {e}")
                    break
        
        except asyncio.CancelledError:
            logger.info("RemoteVideoTrackProcessor cancelled")
        except Exception as e:
            logger.error(f"Fatal error in RemoteVideoTrackProcessor: {e}")
        finally:
            self.running = False
            logger.info("RemoteVideoTrackProcessor stopped")
    
    def stop(self):
        self.running = False
    
    def get_current_frame(self) -> Optional[np.ndarray]:
        return self.current_frame
    
    def frame_to_base64(self, frame: Optional[np.ndarray] = None, quality: int = 85) -> Optional[str]:
        if frame is None:
            frame = self.current_frame
        
        if frame is None:
            return None
        
        try:
            frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            encode_params = [int(cv2.IMWRITE_JPEG_QUALITY), quality]
            success, buffer = cv2.imencode('.jpg', frame_bgr, encode_params)
            
            if not success:
                logger.error("Failed to encode frame to JPEG")
                return None
            
            import base64
            base64_str = base64.b64encode(buffer).decode('utf-8')
            return base64_str
        
        except Exception as e:
            logger.error(f"Error converting frame to base64: {e}")
            return None

