"""
Voice Recorder Component
Handles audio recording from microphone and saving to app data directory
"""
import flet as ft
import sounddevice as sd
import soundfile as sf
import numpy as np
import asyncio
import os
from pathlib import Path
from datetime import datetime

from ..utils.app_dirs import get_recordings_dir


class VoiceRecorder(ft.UserControl):
    """
    Voice Recorder component with visual feedback
    Records audio from microphone and saves to temporary MP3 file
    """
    
    def __init__(self, page: ft.Page, on_recording_complete, max_duration: int = 120):
        """
        Initialize Voice Recorder
        
        Args:
            page: Flet page for async operations
            on_recording_complete: Callback function(file_path: str, duration: float)
            max_duration: Maximum recording duration in seconds (default 120s = 2 min)
        """
        super().__init__()
        self.page_ref = page
        self.on_recording_complete = on_recording_complete
        self.max_duration = max_duration
        
        # Recording state
        self.is_recording = False
        self.audio_data = []
        self.sample_rate = 44100  # CD quality
        self.channels = 1  # Mono for voice
        self.start_time = None
        self.stream = None
        
        # UI elements
        self.record_button = None
        self.timer_text = None
        self.status_text = None
        self.waveform_indicator = None
        self.cancel_button = None
        
    def build(self):
        """Build the UI"""
        # Record/Stop button
        self.record_button = ft.IconButton(
            icon=ft.icons.MIC,
            icon_color=ft.colors.RED_400,
            icon_size=32,
            tooltip="Record voice message (max 2 min)",
            on_click=self.toggle_recording
        )
        
        # Timer display
        self.timer_text = ft.Text(
            "0:00",
            size=16,
            weight=ft.FontWeight.BOLD,
            visible=False
        )
        
        # Status text
        self.status_text = ft.Text(
            "",
            size=12,
            color=ft.colors.GREY_600,
            visible=False
        )
        
        # Waveform indicator (animated)
        self.waveform_indicator = ft.Container(
            content=ft.Row([
                ft.Container(width=3, height=20, bgcolor=ft.colors.RED_400, border_radius=2),
                ft.Container(width=3, height=30, bgcolor=ft.colors.RED_400, border_radius=2),
                ft.Container(width=3, height=25, bgcolor=ft.colors.RED_400, border_radius=2),
                ft.Container(width=3, height=35, bgcolor=ft.colors.RED_400, border_radius=2),
                ft.Container(width=3, height=20, bgcolor=ft.colors.RED_400, border_radius=2),
            ], spacing=2),
            visible=False
        )
        
        # Cancel button (only visible when recording)
        self.cancel_button = ft.TextButton(
            "Cancel",
            icon=ft.icons.CLOSE,
            on_click=self.cancel_recording,
            visible=False
        )
        
        return ft.Container(
            content=ft.Column([
                ft.Row([
                    self.record_button,
                    self.timer_text,
                    self.waveform_indicator,
                    self.cancel_button,
                ], alignment=ft.MainAxisAlignment.START, spacing=10),
                self.status_text,
            ], spacing=5),
            padding=5
        )
    
    def toggle_recording(self, e):
        """Toggle between start and stop recording"""
        if not self.is_recording:
            self.start_recording()
        else:
            self.stop_recording()
    
    def start_recording(self):
        """Start audio recording"""
        try:
            print("🎤 Starting voice recording...")
            self.is_recording = True
            self.audio_data = []
            self.start_time = datetime.now()
            
            # Update UI
            self.record_button.icon = ft.icons.STOP_CIRCLE
            self.record_button.icon_color = ft.colors.RED_700
            self.record_button.tooltip = "Stop recording"
            self.timer_text.visible = True
            self.waveform_indicator.visible = True
            self.cancel_button.visible = True
            self.status_text.value = "Recording... Speak now!"
            self.status_text.color = ft.colors.RED_600
            self.status_text.visible = True
            self.update()
            
            # Start audio stream
            self.stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                dtype='float32',
                callback=self._audio_callback
            )
            self.stream.start()
            
            # Start timer update
            self.page_ref.run_task(self._update_timer)
            
            print("✅ Recording started")
            
        except Exception as e:
            print(f"❌ Error starting recording: {e}")
            self.status_text.value = f"Error: {str(e)}"
            self.status_text.color = ft.colors.RED
            self.status_text.visible = True
            self.reset_ui()
            self.update()
    
    def _audio_callback(self, indata, frames, time, status):
        """
        Callback function called by sounddevice for each audio block
        
        Args:
            indata: Input audio data (numpy array)
            frames: Number of frames
            time: Time info
            status: Status flags
        """
        if status:
            print(f"Audio callback status: {status}")
        
        if self.is_recording:
            # Append audio data
            self.audio_data.append(indata.copy())
    
    async def _update_timer(self):
        """Update timer display while recording"""
        while self.is_recording:
            elapsed = (datetime.now() - self.start_time).total_seconds()
            
            # Update timer text
            minutes = int(elapsed // 60)
            seconds = int(elapsed % 60)
            self.timer_text.value = f"{minutes}:{seconds:02d}"
            self.update()
            
            # Auto-stop at max duration
            if elapsed >= self.max_duration:
                print(f"⏰ Max duration ({self.max_duration}s) reached, auto-stopping...")
                self.stop_recording()
                break
            
            await asyncio.sleep(0.1)  # Update every 100ms
    
    def stop_recording(self):
        """Stop recording and save audio file"""
        if not self.is_recording:
            return
        
        try:
            print("⏹️ Stopping recording...")
            self.is_recording = False
            
            # Stop stream
            if self.stream:
                self.stream.stop()
                self.stream.close()
                self.stream = None
            
            # Calculate duration
            duration = (datetime.now() - self.start_time).total_seconds()
            print(f"📊 Recording duration: {duration:.2f}s")
            
            # Check if we have audio data
            if not self.audio_data:
                print("⚠️ No audio data recorded")
                self.status_text.value = "No audio recorded"
                self.status_text.color = ft.colors.ORANGE
                self.reset_ui()
                self.update()
                return
            
            # Update UI
            self.status_text.value = "Processing audio..."
            self.status_text.color = ft.colors.BLUE
            self.update()
            
            # Combine all audio chunks
            audio = np.concatenate(self.audio_data, axis=0)
            print(f"📊 Audio shape: {audio.shape}, dtype: {audio.dtype}")
            
            # Save to app data directory (OS-standard location)
            recordings_dir = get_recordings_dir()
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            temp_file = recordings_dir / f"voice_msg_{timestamp}.wav"
            
            print(f"💾 Saving to: {temp_file}")
            print(f"📁 Recordings directory: {recordings_dir}")
            sf.write(temp_file, audio, self.sample_rate)
            
            # Verify file was created
            if not temp_file.exists():
                raise Exception("Failed to save audio file")
            
            file_size = temp_file.stat().st_size
            print(f"✅ Audio saved: {file_size} bytes")
            
            # Update UI
            self.status_text.value = f"✓ Recorded {duration:.1f}s"
            self.status_text.color = ft.colors.GREEN
            
            # Call callback with file path (as string for compatibility)
            if self.on_recording_complete:
                self.on_recording_complete(str(temp_file), duration)
            
            # Reset UI after 2 seconds
            self.page_ref.run_task(self._delayed_reset)
            
        except Exception as e:
            print(f"❌ Error stopping recording: {e}")
            import traceback
            traceback.print_exc()
            
            self.status_text.value = f"Error: {str(e)}"
            self.status_text.color = ft.colors.RED
            self.reset_ui()
            self.update()
    
    def cancel_recording(self, e):
        """Cancel current recording without saving"""
        print("🚫 Cancelling recording...")
        
        self.is_recording = False
        
        # Stop stream
        if self.stream:
            self.stream.stop()
            self.stream.close()
            self.stream = None
        
        # Clear audio data
        self.audio_data = []
        
        # Update UI
        self.status_text.value = "Recording cancelled"
        self.status_text.color = ft.colors.GREY
        self.status_text.visible = True
        
        self.reset_ui()
        self.update()
        
        # Clear status after 2 seconds
        self.page_ref.run_task(self._delayed_reset)
    
    async def _delayed_reset(self):
        """Reset UI after delay"""
        await asyncio.sleep(2)
        self.reset_ui()
        self.update()
    
    def reset_ui(self):
        """Reset UI to initial state"""
        self.record_button.icon = ft.icons.MIC
        self.record_button.icon_color = ft.colors.RED_400
        self.record_button.tooltip = "Record voice message (max 2 min)"
        self.timer_text.visible = False
        self.timer_text.value = "0:00"
        self.waveform_indicator.visible = False
        self.cancel_button.visible = False
        self.status_text.visible = False

