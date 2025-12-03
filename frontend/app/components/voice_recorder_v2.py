"""
Voice Recorder Component (In-Memory Version)
Records audio to memory buffer and uploads directly without temp files
"""
import flet as ft
import sounddevice as sd
import soundfile as sf
import numpy as np
from io import BytesIO
from datetime import datetime


class VoiceRecorderMemory(ft.UserControl):
    """
    Voice Recorder that uses in-memory buffer (no temp files)
    More professional for chat applications
    """
    
    def __init__(self, page: ft.Page, on_recording_complete, max_duration: int = 120):
        """
        Initialize Voice Recorder
        
        Args:
            page: Flet page for async operations
            on_recording_complete: Callback function(audio_buffer: BytesIO, duration: float)
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
        
        # UI elements (same as before)
        self.record_button = None
        self.timer_text = None
        self.status_text = None
        self.waveform_indicator = None
        self.cancel_button = None
    
    # ... (keep all the UI and recording logic same) ...
    
    def stop_recording(self):
        """Stop recording and save to memory buffer"""
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
            
            # Save to memory buffer (no temp file!)
            audio_buffer = BytesIO()
            sf.write(audio_buffer, audio, self.sample_rate, format='WAV')
            audio_buffer.seek(0)  # Reset to beginning
            
            buffer_size = len(audio_buffer.getvalue())
            print(f"✅ Audio buffered: {buffer_size} bytes (in memory)")
            
            # Update UI
            self.status_text.value = f"✓ Recorded {duration:.1f}s"
            self.status_text.color = ft.colors.GREEN
            
            # Call callback with buffer
            if self.on_recording_complete:
                self.on_recording_complete(audio_buffer, duration)
            
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


# Example usage in MessageInput:
"""
def _handle_voice_recorded(self, audio_buffer: BytesIO, duration: float):
    '''Handle voice recording completed'''
    print(f"🎤 Voice recorded in memory: {len(audio_buffer.getvalue())} bytes, duration: {duration:.1f}s")
    
    # Save buffer to use later
    self.recorded_voice_buffer = audio_buffer
    self.voice_duration = duration
    
    # Show notification
    self.page_ref.snack_bar = ft.SnackBar(
        content=ft.Text(f"✅ Voice message recorded ({duration:.1f}s). Click Send to upload."),
        bgcolor=config.SUCCESS_COLOR
    )
    self.page_ref.snack_bar.open = True
    self.page_ref.update()

async def _upload_voice_from_buffer(self, audio_buffer: BytesIO):
    '''Upload audio directly from buffer'''
    try:
        # Reset buffer position
        audio_buffer.seek(0)
        
        # Create form data
        files = {
            'file': ('voice_msg.wav', audio_buffer, 'audio/wav')
        }
        
        # Upload
        response = await self.api_client.post('/api/files/upload', files=files)
        
        # Return file URL
        return response['file_url']
        
    except Exception as e:
        print(f"❌ Upload failed: {e}")
        # Fallback: Save to temp and retry later
        raise
"""

