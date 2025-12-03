"""
Message input component
Input area with file upload and voice recording support
"""
import flet as ft
from typing import Optional, Callable
from pathlib import Path

from ..config import config
from .voice_recorder import VoiceRecorder


class MessageInput(ft.UserControl):
    """
    Message input component with file attachment
    """
    
    def __init__(
        self,
        page: ft.Page,
        on_send: Optional[Callable] = None,
        on_typing: Optional[Callable] = None
    ):
        """
        Initialize message input
        
        Args:
            page: Flet page for async operations
            on_send: Callback when message is sent (text, file_path)
            on_typing: Callback when user is typing
        """
        super().__init__()
        self.page_ref = page
        self.on_send_callback = on_send
        self.on_typing_callback = on_typing
        self.selected_file: Optional[Path] = None
        self.recorded_voice: Optional[Path] = None
        self.voice_duration: Optional[float] = None
        
        # Voice recorder state
        self.is_recording_mode = False
        
        # UI Components
        self.message_input = ft.TextField(
            hint_text="Type a message...",
            expand=True,
            multiline=True,
            min_lines=1,
            max_lines=3,
            shift_enter=True,
            on_submit=self._handle_send,
            on_change=self._handle_typing
        )
        
        self.file_picker = ft.FilePicker(on_result=self._handle_file_picked)
        self.upload_progress = ft.ProgressBar(visible=False, width=200)
        
        self.attach_button = ft.IconButton(
            icon=ft.icons.ATTACH_FILE,
            icon_color=config.PRIMARY_COLOR,
            tooltip="Attach file",
            on_click=self._pick_file
        )
        
        # Voice recording button
        self.voice_button = ft.IconButton(
            icon=ft.icons.MIC,
            icon_color=ft.colors.RED_400,
            tooltip="Record voice message",
            on_click=self._toggle_voice_recorder
        )
        
        # Voice recorder component (initially hidden)
        self.voice_recorder = None
        
        self.send_button = ft.IconButton(
            icon=ft.icons.SEND_ROUNDED,
            icon_color=config.PRIMARY_COLOR,
            on_click=self._handle_send
        )
    
    def build(self):
        """Build message input UI"""
        # Input row content (changes based on recording mode)
        input_row_content = [
            self.attach_button,
            self.voice_button,
            self.message_input,
            self.send_button
        ]
        
        return ft.Container(
            content=ft.Column([
                # Upload progress bar (hidden by default)
                self.upload_progress,
                # Voice recorder (shown when recording)
                ft.Container(
                    ref=ft.Ref[ft.Container](),
                    visible=False
                ),
                # Input row
                ft.Row(
                    input_row_content,
                    spacing=10
                )
            ], spacing=5),
            bgcolor=ft.colors.WHITE,
            padding=10,
            border=ft.border.only(top=ft.BorderSide(1, ft.colors.GREY_300))
        )
    
    def did_mount(self):
        """Add file picker to page overlay"""
        self.page.overlay.append(self.file_picker)
        self.page.update()
    
    def _pick_file(self, e):
        """Open file picker"""
        self.file_picker.pick_files(
            dialog_title="Select file to upload",
            allow_multiple=False,
            allowed_extensions=["jpg", "jpeg", "png", "gif", "pdf", "txt", "docx", "xlsx", "mp3", "mp4", "zip"]
        )
    
    def _handle_file_picked(self, e: ft.FilePickerResultEvent):
        """Handle file picked from file picker"""
        if e.files and len(e.files) > 0:
            self.selected_file = Path(e.files[0].path)
            print(f"📎 File selected: {self.selected_file.name}")
            
            # Show notification
            self.page.snack_bar = ft.SnackBar(
                content=ft.Text(f"File selected: {self.selected_file.name}. Click Send to upload."),
                bgcolor=config.SUCCESS_COLOR
            )
            self.page.snack_bar.open = True
            self.page.update()
        else:
            print("No file selected")
    
    def _handle_typing(self, e):
        """Handle typing event"""
        if self.on_typing_callback:
            # Wrap async callback
            import inspect
            if inspect.iscoroutinefunction(self.on_typing_callback):
                self.page_ref.run_task(self.on_typing_callback, e)
            else:
                self.on_typing_callback(e)
    
    def _handle_send(self, e):
        """Handle send button click"""
        content = self.message_input.value
        
        # Priority: Voice > File > Text
        file_to_send = None
        
        if self.recorded_voice:
            # Send voice message
            file_to_send = self.recorded_voice
            if not content or not content.strip():
                content = f"🎤 Voice message ({self.voice_duration:.1f}s)"
        elif self.selected_file:
            # Send file attachment
            file_to_send = self.selected_file
            if not content or not content.strip():
                content = f"📎 {self.selected_file.name}"
        
        # Check if we have content or file
        if (not content or not content.strip()) and not file_to_send:
            return
        
        # Call callback with content and file
        if self.on_send_callback:
            # Wrap async callback
            import inspect
            if inspect.iscoroutinefunction(self.on_send_callback):
                self.page_ref.run_task(self.on_send_callback, content.strip() if content else "", file_to_send)
            else:
                self.on_send_callback(content.strip() if content else "", file_to_send)
        
        # Clear input and file selection
        self.message_input.value = ""
        self.selected_file = None
        self.recorded_voice = None
        self.voice_duration = None
        self.update()
    
    def show_upload_progress(self):
        """Show upload progress bar"""
        self.upload_progress.visible = True
        self.upload_progress.value = None  # Indeterminate
        self.update()
    
    def hide_upload_progress(self):
        """Hide upload progress bar"""
        self.upload_progress.visible = False
        self.update()
    
    def _toggle_voice_recorder(self, e):
        """Toggle voice recorder visibility"""
        if not self.is_recording_mode:
            self._show_voice_recorder()
        else:
            self._hide_voice_recorder()
    
    def _show_voice_recorder(self):
        """Show voice recorder dialog"""
        # Create voice recorder if not exists
        if not self.voice_recorder:
            self.voice_recorder = VoiceRecorder(
                page=self.page_ref,
                on_recording_complete=self._handle_voice_recorded
            )
        
        # Create dialog
        dialog = ft.AlertDialog(
            title=ft.Text("🎤 Record Voice Message"),
            content=self.voice_recorder,
            actions=[
                ft.TextButton("Close", on_click=lambda e: self._close_voice_dialog(dialog))
            ],
            actions_alignment=ft.MainAxisAlignment.END
        )
        
        # Show dialog
        self.page_ref.dialog = dialog
        dialog.open = True
        self.page_ref.update()
        
        self.is_recording_mode = True
    
    def _close_voice_dialog(self, dialog):
        """Close voice recorder dialog"""
        dialog.open = False
        self.page_ref.update()
        self.is_recording_mode = False
    
    def _hide_voice_recorder(self):
        """Hide voice recorder"""
        if self.page_ref.dialog:
            self.page_ref.dialog.open = False
            self.page_ref.update()
        self.is_recording_mode = False
    
    def _handle_voice_recorded(self, file_path: str, duration: float):
        """Handle voice recording completed"""
        print(f"🎤 Voice recorded: {file_path}, duration: {duration:.1f}s")
        
        # Store the recorded voice file
        self.recorded_voice = Path(file_path)
        self.voice_duration = duration
        
        # Close dialog
        if self.page_ref.dialog:
            self.page_ref.dialog.open = False
            self.page_ref.update()
        self.is_recording_mode = False
        
        # Show notification
        self.page_ref.snack_bar = ft.SnackBar(
            content=ft.Text(f"✅ Voice message recorded ({duration:.1f}s). Click Send to upload."),
            bgcolor=config.SUCCESS_COLOR
        )
        self.page_ref.snack_bar.open = True
        self.page_ref.update()
        
        # Auto-send voice message after recording
        # Or let user send it manually - uncomment line below to auto-send:
        # self._handle_send(None)
    
    def clear(self):
        """Clear input field"""
        self.message_input.value = ""
        self.selected_file = None
        self.recorded_voice = None
        self.voice_duration = None
        self.update()

