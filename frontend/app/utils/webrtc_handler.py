import asyncio
import logging
import json
from typing import Optional, Callable
from uuid import UUID

from aiortc import RTCPeerConnection, RTCSessionDescription, RTCIceCandidate, RTCConfiguration, RTCIceServer
from aiortc.contrib.media import MediaPlayer

from .video_tracks import OpenCVVideoTrack, RemoteVideoTrackProcessor
from ..websocket.client import WebSocketClient, get_ws_client

logger = logging.getLogger(__name__)


class WebRTCHandler:

    def __init__(
        self,
        call_id: str,
        local_user_id: str,
        remote_user_id: str,
        is_caller: bool = False,
        ws_client: Optional[WebSocketClient] = None
    ):

        self.call_id = call_id
        self.local_user_id = local_user_id
        self.remote_user_id = remote_user_id
        self.is_caller = is_caller
        self.ws_client = ws_client or get_ws_client()
        
        # RTCPeerConnection
        self.pc: Optional[RTCPeerConnection] = None
        self.local_video_track: Optional[OpenCVVideoTrack] = None
        self.local_audio_track: Optional[MediaPlayer] = None
        self.remote_video_processor: Optional[RemoteVideoTrackProcessor] = None
        self.on_remote_video_frame: Optional[Callable] = None
        self.on_connection_state_change: Optional[Callable] = None
        self.initialized = False
        self.closed = False
    
    async def initialize(self, camera_index: int = 0, video_width: int = 640, video_height: int = 480):

        if self.initialized:
            logger.warning("WebRTCHandler already initialized")
            return
        
        try:
            # Create RTCPeerConnection with STUN server
            config = RTCConfiguration(
                iceServers=[RTCIceServer(urls=["stun:stun.l.google.com:19302"])]
            )
            self.pc = RTCPeerConnection(configuration=config)
            
            self._setup_event_handlers()
            await self._setup_local_video(camera_index, video_width, video_height)
            await self._setup_local_audio()
            
            if self.local_video_track:
                self.pc.addTrack(self.local_video_track)
            if self.local_audio_track:
                for track in self.local_audio_track.audio_tracks:
                    self.pc.addTrack(track)
            
            self.initialized = True
            logger.info(f"WebRTCHandler initialized: call_id={self.call_id}, is_caller={self.is_caller}")
        
        except Exception as e:
            logger.error(f"Error initializing WebRTCHandler: {e}")
            import traceback
            logger.error(traceback.format_exc())
            raise
    
    def _setup_event_handlers(self):
        """Setup RTCPeerConnection event handlers"""
        if not self.pc:
            return
        
        @self.pc.on("connectionstatechange")
        async def on_connectionstatechange():
            state = self.pc.connectionState
            logger.info(f"Connection state changed: {state}")
            if self.on_connection_state_change:
                try:
                    self.on_connection_state_change(state)
                except Exception as e:
                    logger.error(f"Error in connection state change callback: {e}")
        
        @self.pc.on("track")
        def on_track(track):
            logger.info(f"=== Remote track received: kind={track.kind}, id={track.id}, readyState={track.readyState} ===")
            if track.kind == "video":
                logger.info("Processing remote video track...")
                self._handle_remote_video_track(track)
            elif track.kind == "audio":
                logger.info("Remote audio track received (auto-played by browser)")
            else:
                logger.warning(f"Unknown track kind: {track.kind}")
        
        @self.pc.on("icecandidate")
        def on_icecandidate(candidate):
            if candidate:
                self._handle_ice_candidate(candidate)
            else:
                logger.info("ICE gathering completed")
    
    async def _setup_local_video(self, camera_index: int, width: int, height: int):

        try:
            self.local_video_track = OpenCVVideoTrack(
                camera_index=camera_index,
                width=width,
                height=height,
                fps=30
            )
            await self.local_video_track.start()
            logger.info(f"Local video track setup: {width}x{height} from camera {camera_index}")
        except Exception as e:
            logger.error(f"Error setting up local video: {e}")
            self.local_video_track = None
            raise
    
    async def _setup_local_audio(self):
        try:
            import platform
            if platform.system() == "Windows":
                try:
                    self.local_audio_track = MediaPlayer(
                        "audio=default",
                        format="dshow"
                    )
                    logger.info("Local audio track setup using DirectShow (Windows)")
                except Exception as e:
                    logger.warning(f"DirectShow failed, trying default: {e}")
                    try:
                        self.local_audio_track = MediaPlayer("audio=default")
                        logger.info("Local audio track setup using default format")
                    except Exception as e2:
                        logger.warning(f"Default audio also failed: {e2}")
                        self.local_audio_track = None
            else:
                try:
                    self.local_audio_track = MediaPlayer("audio=default")
                    logger.info("Local audio track setup using default")
                except Exception as e:
                    logger.warning(f"Audio setup failed: {e}")
                    self.local_audio_track = None
            
            if self.local_audio_track:
                logger.info("Local audio track setup completed")
            else:
                logger.warning("Local audio track not available (video-only call)")
        except Exception as e:
            logger.error(f"Error setting up local audio: {e}")
            self.local_audio_track = None
    
    def _handle_remote_video_track(self, track):
        try:
            logger.info(f"_handle_remote_video_track called: track={track}, readyState={track.readyState}")
            logger.info(f"on_remote_video_frame callback: {self.on_remote_video_frame}")
            
            self.remote_video_processor = RemoteVideoTrackProcessor(
                on_frame=self.on_remote_video_frame
            )
            
            logger.info("Creating task to process remote video track...")
            asyncio.create_task(self.remote_video_processor.process_track(track))
            logger.info("Remote video track processing task created")
        except Exception as e:
            logger.error(f"Error handling remote video track: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    def _handle_ice_candidate(self, candidate: RTCIceCandidate):
        if not self.ws_client or not self.ws_client.connected:
            logger.warning("WebSocket not connected, cannot send ICE candidate")
            return
        
        try:
            # Convert candidate to JSON
            candidate_dict = {
                "candidate": candidate.candidate,
                "sdpMid": candidate.sdpMid,
                "sdpMLineIndex": candidate.sdpMLineIndex
            }
            candidate_json = json.dumps(candidate_dict)
            
            # Send via WebSocket
            asyncio.create_task(
                self.ws_client.send_ice_candidate(
                    call_id=self.call_id,
                    from_user_id=self.local_user_id,
                    to_user_id=self.remote_user_id,
                    candidate=candidate_json,
                    sdp_mid=candidate.sdpMid,
                    sdp_mline_index=candidate.sdpMLineIndex
                )
            )
            logger.debug(f"ICE candidate sent: {candidate.sdpMid}:{candidate.sdpMLineIndex}")
        except Exception as e:
            logger.error(f"Error sending ICE candidate: {e}")
    
    async def create_offer(self) -> str:
        if not self.pc:
            raise RuntimeError("RTCPeerConnection not initialized")
        
        if not self.is_caller:
            raise RuntimeError("Only caller can create offer")
        
        try:
            # Create offer
            offer = await self.pc.createOffer()
            await self.pc.setLocalDescription(offer)
            
            logger.info("SDP offer created")
            
            await asyncio.sleep(0.5)
            
            sdp = self.pc.localDescription.sdp
            return sdp
        
        except Exception as e:
            logger.error(f"Error creating offer: {e}")
            raise
    
    async def create_answer(self) -> str:

        if not self.pc:
            raise RuntimeError("RTCPeerConnection not initialized")
        
        if self.is_caller:
            raise RuntimeError("Only callee can create answer")
        
        try:
            answer = await self.pc.createAnswer()
            await self.pc.setLocalDescription(answer)
            
            logger.info("SDP answer created")
            
            await asyncio.sleep(0.5)
            
            sdp = self.pc.localDescription.sdp
            return sdp
        
        except Exception as e:
            logger.error(f"Error creating answer: {e}")
            raise
    
    async def handle_remote_description(self, sdp: str, sdp_type: str):
        if not self.pc:
            raise RuntimeError("RTCPeerConnection not initialized")
        
        try:
            description = RTCSessionDescription(sdp=sdp, type=sdp_type)
            await self.pc.setRemoteDescription(description)
            
            logger.info(f"Remote {sdp_type} description set")
        
        except Exception as e:
            logger.error(f"Error handling remote description: {e}")
            raise
    
    async def add_ice_candidate(self, candidate: str, sdp_mid: Optional[str] = None, 
                                sdp_mline_index: Optional[int] = None):
        if not self.pc:
            raise RuntimeError("RTCPeerConnection not initialized")
        
        try:
            if isinstance(candidate, str):
                try:
                    candidate_dict = json.loads(candidate)
                    candidate_str = candidate_dict.get("candidate", candidate)
                    sdp_mid = candidate_dict.get("sdpMid") or sdp_mid
                    sdp_mline_index = candidate_dict.get("sdpMLineIndex") or sdp_mline_index
                except json.JSONDecodeError:
                    candidate_str = candidate
            else:
                candidate_str = candidate
            
            # Create RTCIceCandidate
            ice_candidate = RTCIceCandidate(
                candidate=candidate_str,
                sdpMid=sdp_mid,
                sdpMLineIndex=sdp_mline_index
            )
            
            # Add to peer connection
            await self.pc.addIceCandidate(ice_candidate)
            
            logger.debug(f"ICE candidate added: {sdp_mid}:{sdp_mline_index}")
        
        except Exception as e:
            logger.error(f"Error adding ICE candidate: {e}")
    
    def set_remote_video_callback(self, callback: Callable):
        self.on_remote_video_frame = callback
        if self.remote_video_processor:
            self.remote_video_processor.on_frame = callback
    
    def set_connection_state_callback(self, callback: Callable):
        self.on_connection_state_change = callback
    
    async def close(self):
        if self.closed:
            return
        
        self.closed = True
        logger.info("Closing WebRTCHandler...")
        
        try:
            if self.remote_video_processor:
                self.remote_video_processor.stop()
                self.remote_video_processor = None
            
            if self.local_video_track:
                await self.local_video_track.stop()
                self.local_video_track = None
            
            if self.local_audio_track:
                self.local_audio_track.stop()
                self.local_audio_track = None
            
            # Close peer connection
            if self.pc:
                await self.pc.close()
                self.pc = None
            
            self.initialized = False
            logger.info("WebRTCHandler closed")
        
        except Exception as e:
            logger.error(f"Error closing WebRTCHandler: {e}")
            import traceback
            logger.error(traceback.format_exc())

