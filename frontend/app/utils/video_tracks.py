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
            self.cap = cv2.VideoCapture(self.camera_index)
            if not self.cap.isOpened():
                raise RuntimeError(f"Failed to open camera {self.camera_index}")
            
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
            self.cap.set(cv2.CAP_PROP_FPS, self.fps)
            
            self.running = True
            logger.info(f"OpenCVVideoTrack started: camera={self.camera_index}, {self.width}x{self.height}@{self.fps}fps")
        except Exception as e:
            logger.error(f"Error starting OpenCVVideoTrack: {e}")
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
        if not ret:
            logger.warning("Failed to read frame from camera")
            frame = np.zeros((self.height, self.width, 3), dtype=np.uint8)
        
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

