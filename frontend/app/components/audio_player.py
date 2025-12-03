"""
Audio Player Component
Handles playback of audio files (voice messages)
"""
import flet as ft
import asyncio
from datetime import datetime, timedelta


class AudioPlayer(ft.UserControl):
    """
    Audio Player component with play/pause, progress bar, and duration display
    """
    
    def __init__(self, audio_url: str, duration: float = None, on_download=None):
        """
        Initialize Audio Player
        
        Args:
            audio_url: URL to audio file
            duration: Duration in seconds (optional)
            on_download: Callback for download button
        """
        super().__init__()
        self.audio_url = audio_url
        self.duration = duration
        self.on_download = on_download
        
        # Player state
        self.is_playing = False
        self.current_time = 0.0
        
        # UI elements
        self.play_button = None
        self.progress_bar = None
        self.time_label = None
        self.download_button = None
        self.audio_element = None
        
    def build(self):
        """Build the UI"""
        # Play/Pause button
        self.play_button = ft.IconButton(
            icon=ft.icons.PLAY_ARROW,
            icon_size=28,
            tooltip="Play voice message",
            on_click=self.toggle_play
        )
        
        # Progress bar
        self.progress_bar = ft.ProgressBar(
            value=0,
            width=150,
            height=4,
            bar_height=4,
            color=ft.colors.BLUE_400,
            bgcolor=ft.colors.GREY_300,
        )
        
        # Time label
        duration_str = self._format_time(self.duration) if self.duration else "0:00"
        self.time_label = ft.Text(
            f"0:00 / {duration_str}",
            size=12,
            color=ft.colors.GREY_700,
        )
        
        # Download button (optional)
        self.download_button = ft.IconButton(
            icon=ft.icons.DOWNLOAD,
            icon_size=20,
            tooltip="Download audio",
            on_click=self._handle_download,
            visible=bool(self.on_download)
        )
        
        # Audio element (hidden, used for playback)
        # Note: Flet's Audio control is used for actual playback
        self.audio_element = ft.Audio(
            src=self.audio_url,
            autoplay=False,
            on_state_changed=self._on_audio_state_changed,
            on_duration_changed=self._on_duration_changed,
            on_position_changed=self._on_position_changed,
        )
        
        return ft.Container(
            content=ft.Column([
                ft.Row([
                    self.play_button,
                    ft.Column([
                        self.progress_bar,
                        self.time_label,
                    ], spacing=2),
                    self.download_button,
                ], alignment=ft.MainAxisAlignment.START, spacing=5, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                self.audio_element,  # Hidden audio element
            ], spacing=0),
            bgcolor=ft.colors.GREY_100,
            border_radius=8,
            padding=8,
        )
    
    def toggle_play(self, e):
        """Toggle between play and pause"""
        if not self.is_playing:
            self.play()
        else:
            self.pause()
    
    def play(self):
        """Start playing audio"""
        print(f"▶️ Playing audio: {self.audio_url}")
        self.is_playing = True
        self.play_button.icon = ft.icons.PAUSE
        self.play_button.tooltip = "Pause"
        
        # Play audio
        if self.audio_element:
            self.audio_element.play()
        
        self.update()
    
    def pause(self):
        """Pause audio playback"""
        print(f"⏸️ Pausing audio")
        self.is_playing = False
        self.play_button.icon = ft.icons.PLAY_ARROW
        self.play_button.tooltip = "Play"
        
        # Pause audio
        if self.audio_element:
            self.audio_element.pause()
        
        self.update()
    
    def stop(self):
        """Stop audio playback"""
        print(f"⏹️ Stopping audio")
        self.is_playing = False
        self.current_time = 0.0
        self.play_button.icon = ft.icons.PLAY_ARROW
        self.play_button.tooltip = "Play"
        
        # Stop audio (reset to beginning)
        if self.audio_element:
            self.audio_element.pause()
            # Note: Flet Audio doesn't have a seek method yet, so we'll just pause
        
        self.progress_bar.value = 0
        duration_str = self._format_time(self.duration) if self.duration else "0:00"
        self.time_label.value = f"0:00 / {duration_str}"
        self.update()
    
    def _on_audio_state_changed(self, e):
        """Handle audio state changes"""
        state = e.data
        print(f"🔊 Audio state: {state}")
        
        if state == "completed":
            # Audio finished playing
            self.stop()
    
    def _on_duration_changed(self, e):
        """Handle when audio duration is loaded"""
        duration_ms = int(e.data)
        self.duration = duration_ms / 1000.0  # Convert to seconds
        print(f"⏱️ Audio duration: {self.duration}s")
        
        # Update time label
        duration_str = self._format_time(self.duration)
        current_str = self._format_time(self.current_time)
        self.time_label.value = f"{current_str} / {duration_str}"
        self.update()
    
    def _on_position_changed(self, e):
        """Handle playback position updates"""
        position_ms = int(e.data)
        self.current_time = position_ms / 1000.0  # Convert to seconds
        
        # Update progress bar
        if self.duration and self.duration > 0:
            progress = self.current_time / self.duration
            self.progress_bar.value = min(progress, 1.0)
        
        # Update time label
        current_str = self._format_time(self.current_time)
        duration_str = self._format_time(self.duration) if self.duration else "0:00"
        self.time_label.value = f"{current_str} / {duration_str}"
        
        self.update()
    
    def _format_time(self, seconds: float) -> str:
        """
        Format time in seconds to MM:SS format
        
        Args:
            seconds: Time in seconds
            
        Returns:
            Formatted string (e.g., "1:23")
        """
        if seconds is None:
            return "0:00"
        
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes}:{secs:02d}"
    
    def _handle_download(self, e):
        """Handle download button click"""
        if self.on_download:
            self.on_download()


class AudioPlayerSimple(ft.UserControl):
    """
    Simplified Audio Player with in-app playback (for messages)
    Uses Flet's Audio widget for in-app audio playback
    """
    
    def __init__(self, audio_url: str, duration: float = None):
        """
        Initialize Simple Audio Player
        
        Args:
            audio_url: URL to audio file
            duration: Duration in seconds (optional)
        """
        super().__init__()
        self.audio_url = audio_url
        self.duration = duration
        self.is_playing = False
        
        # Audio element
        self.audio_element = None
        self.play_button = None
        
    def build(self):
        """Build the UI"""
        # Format duration
        duration_str = self._format_time(self.duration) if self.duration else "Voice message"
        
        # Audio URL is already full URL from API client
        # Don't prepend base URL again to avoid duplication
        
        # Audio element (hidden, for playback)
        self.audio_element = ft.Audio(
            src=self.audio_url,
            autoplay=False,
            volume=1.0,  # Max volume (0.0 to 1.0)
            on_state_changed=self._on_audio_state_changed,
            on_duration_changed=self._on_duration_changed,
            on_position_changed=self._on_position_changed,
        )
        
        print(f"🎵 Audio element created: {self.audio_url}")
        
        # Play/Pause button
        self.play_button = ft.IconButton(
            icon=ft.icons.PLAY_ARROW,
            icon_size=24,
            icon_color=ft.colors.BLUE_600,
            tooltip="Play voice message",
            on_click=self._toggle_play
        )
        
        # Duration label
        duration_label = ft.Text(
            duration_str,
            size=13,
            color=ft.colors.GREY_700,
        )
        
        # Waveform icon
        waveform = ft.Icon(
            ft.icons.GRAPHIC_EQ,
            size=20,
            color=ft.colors.BLUE_400
        )
        
        return ft.Container(
            content=ft.Column([
                ft.Row([
                    self.play_button,
                    waveform,
                    ft.ProgressBar(value=0, width=100, height=3),
                    duration_label,
                ], spacing=8, alignment=ft.MainAxisAlignment.START),
                self.audio_element,  # Hidden audio element
            ], spacing=0),
            bgcolor=ft.colors.BLUE_50,
            border_radius=16,
            padding=ft.padding.only(left=5, right=15, top=5, bottom=5),
        )
    
    def _toggle_play(self, e):
        """Toggle play/pause"""
        if not self.is_playing:
            # Play
            print(f"▶️ Playing audio: {self.audio_url}")
            print(f"   Volume: {self.audio_element.volume}")
            print(f"   Src: {self.audio_element.src}")
            
            self.audio_element.play()
            self.is_playing = True
            self.play_button.icon = ft.icons.PAUSE
            self.play_button.tooltip = "Pause"
        else:
            # Pause
            print(f"⏸️ Pausing audio")
            self.audio_element.pause()
            self.is_playing = False
            self.play_button.icon = ft.icons.PLAY_ARROW
            self.play_button.tooltip = "Play"
        
        self.update()
    
    def _on_audio_state_changed(self, e):
        """Handle audio state changes"""
        state = e.data
        print(f"🔊 Audio state: {state}")
        
        if state == "completed":
            # Audio finished playing - reset button
            self.is_playing = False
            self.play_button.icon = ft.icons.PLAY_ARROW
            self.play_button.tooltip = "Play"
            self.update()
    
    def _on_duration_changed(self, e):
        """Handle audio duration loaded"""
        duration_ms = int(e.data) if e.data else 0
        duration_s = duration_ms / 1000.0
        print(f"⏱️ Audio duration loaded: {duration_s:.1f}s")
    
    def _on_position_changed(self, e):
        """Handle audio position updates"""
        position_ms = int(e.data) if e.data else 0
        position_s = position_ms / 1000.0
        # Only log every 1 second to avoid spam
        if int(position_s) % 1 == 0:
            print(f"🎵 Playback position: {position_s:.1f}s")
    
    def _format_time(self, seconds: float) -> str:
        """Format time in seconds to MM:SS"""
        if seconds is None:
            return "0:00"
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes}:{secs:02d}"

