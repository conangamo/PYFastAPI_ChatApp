"""
Message bubble component
Renders individual message with file support (including audio)
"""
import flet as ft
from typing import Optional

from ..models import Message, User
from ..api.client import get_api_client
from ..config import config
from ..utils.formatters import format_timestamp
from .reactions import ReactionDisplay
from .audio_player import AudioPlayerSimple
from .message_status import MessageStatus


class MessageBubble(ft.UserControl):
    """
    Message bubble component
    Displays message content, files, and metadata
    """
    
    def __init__(
        self,
        message: Message,
        current_user: User,
        is_group_chat: bool = False,
        on_download: Optional[callable] = None,
        on_edit: Optional[callable] = None,
        on_delete: Optional[callable] = None,
        on_copy: Optional[callable] = None,
        on_reaction_click: Optional[callable] = None,
        on_add_reaction: Optional[callable] = None
    ):
        """
        Initialize message bubble
        
        Args:
            message: Message object
            current_user: Current user
            is_group_chat: Whether this is a group chat
            on_download: Callback for file download
            on_edit: Callback for editing message
            on_delete: Callback for deleting message
            on_copy: Callback for copying message text
            on_reaction_click: Callback for clicking on reaction
            on_add_reaction: Callback for adding reaction
        """
        super().__init__()
        self.message = message
        self.current_user = current_user
        self.is_group_chat = is_group_chat
        self.on_download = on_download
        self.on_edit = on_edit
        self.on_delete = on_delete
        self.on_copy = on_copy
        self.on_reaction_click = on_reaction_click
        self.on_add_reaction = on_add_reaction
    
    def build(self):
        """Build message bubble UI"""
        # Check if this is a system message
        is_system_message = (
            self.message.file_type == "system" or 
            self.message.sender_id is None or
            self.message.sender_id == "" or
            (hasattr(self.message, 'sender_username') and self.message.sender_username == "System")
        )
        
        # System messages are displayed differently
        if is_system_message:
            return self._build_system_message()
        
        is_mine = self.message.is_mine(self.current_user.id)
        
        # Message content widgets
        content_widgets = []
        
        # Show sender name at the TOP in group chats (for messages from others)
        if not is_mine and self.is_group_chat:
            # Get sender display name, fallback to username if not available
            sender_name = self.message.sender_display_name or self.message.sender_username or "Unknown User"
            content_widgets.append(
                ft.Text(
                    sender_name,
                    size=12,
                    weight=ft.FontWeight.BOLD,
                    color=config.PRIMARY_COLOR
                )
            )
        
        # Add file preview/attachment if present
        if self.message.has_file():
            file_widget = self._build_file_widget()
            if file_widget:
                content_widgets.append(file_widget)
        
        # Add text content
        if self.message.content:
            # Style deleted messages differently
            if self.message.is_message_deleted():
                content_widgets.append(
                    ft.Text(
                        self.message.content,
                        size=14,
                        italic=True,
                        color=ft.colors.GREY_500
                    )
                )
            else:
                content_widgets.append(
                    ft.Text(self.message.content, size=14, selectable=True)
                )
        
        # Time and edited indicator at the bottom
        time_parts = [format_timestamp(self.message.created_at)]
        if self.message.is_edited() and not self.message.is_message_deleted():
            time_parts.append("(edited)")
        
        time_text = " ".join(time_parts)
        
        # Build timestamp row with status icon (for own messages)
        timestamp_widgets = [
            ft.Text(time_text, size=10, color=config.TEXT_SECONDARY, italic=True)
        ]
        
        # Add status icon for own messages (sent/delivered/read)
        if is_mine and not self.message.is_message_deleted():
            status_icon = MessageStatus(
                created_at=self.message.created_at,
                delivered_at=self.message.delivered_at,
                read_at=self.message.read_at
            )
            timestamp_widgets.append(status_icon)
        
        content_widgets.append(
            ft.Row(
                controls=timestamp_widgets,
                spacing=4,
                alignment=ft.MainAxisAlignment.END
            )
        )
        
        # Choose background color
        if self.message.is_message_deleted():
            bgcolor = ft.colors.GREY_200
        else:
            bgcolor = config.MESSAGE_SENT_BG if is_mine else config.MESSAGE_RECEIVED_BG
        
        # Build bubble content (with menu button for own messages)
        bubble_content = ft.Column(content_widgets, spacing=5)
        
        # Add three-dots menu button for own messages (not deleted)
        if is_mine and not self.message.is_message_deleted():
            bubble_content = ft.Stack([
                # Message content
                ft.Container(
                    content=ft.Column(content_widgets, spacing=5),
                    padding=ft.padding.only(right=25)  # Space for menu button
                ),
                # Menu button (top-right corner)
                ft.Container(
                    content=ft.IconButton(
                        icon=ft.icons.MORE_VERT,
                        icon_size=16,
                        icon_color=config.TEXT_SECONDARY,
                        tooltip="Message options",
                        on_click=self._show_context_menu
                    ),
                    right=0,
                    top=0
                )
            ])
        
        # Calculate width based on message content
        # For text messages, adjust width based on content length
        text_content = self.message.content or ""
        if text_content and not self.message.has_file():
            # Calculate width: min 150px, max 500px
            # Formula: base (150px) + ~6px per character
            char_count = len(text_content)
            # For multiline, use longest line
            if '\n' in text_content:
                lines = text_content.split('\n')
                char_count = max(len(line) for line in lines)
            
            calculated_width = max(150, min(500, 150 + (char_count * 6)))
        else:
            # For file messages or empty, use default (no width constraint)
            calculated_width = None
        
        bubble = ft.Container(
            content=bubble_content,
            bgcolor=bgcolor,
            padding=10,
            border_radius=10,
            margin=ft.margin.only(left=60 if is_mine else 0, right=0 if is_mine else 60),
            width=calculated_width  # Set width based on content
        )
        
        # Also add right-click support
        if is_mine and not self.message.is_message_deleted():
            bubble = ft.GestureDetector(
                content=bubble,
                on_secondary_tap=self._show_context_menu  # Right-click
            )
        
        # Build reactions display
        reactions_display = None
        if not self.message.is_message_deleted():
            reactions_display = ReactionDisplay(
                message=self.message,
                current_user_id=self.current_user.id,
                on_reaction_click=lambda emoji, is_mine: self._handle_reaction_click(emoji, is_mine),
                on_add_reaction=lambda: self._handle_add_reaction()
            )
        
        # Combine bubble and reactions
        message_content = ft.Column([
            ft.Container(
                content=bubble,
                alignment=ft.alignment.center_right if is_mine else ft.alignment.center_left
            )
        ], spacing=0)
        
        if reactions_display:
            message_content.controls.append(
                ft.Container(
                    content=reactions_display,
                    alignment=ft.alignment.center_right if is_mine else ft.alignment.center_left,
                    padding=ft.padding.only(left=60 if is_mine else 0, right=0 if is_mine else 60)
                )
            )
        
        return message_content
    
    def _build_file_widget(self):
        """Build file preview/download widget"""
        if not self.message.has_file():
            return None
        
        api = get_api_client()
        file_url = api.get_file_download_url(self.message.file_url)
        
        # Check if it's an image
        if self.message.file_type and self.message.file_type.startswith("image/"):
            # Image preview
            return ft.Container(
                content=ft.Column([
                    ft.Image(
                        src=file_url,
                        width=300,
                        height=200,
                        fit=ft.ImageFit.CONTAIN,
                        border_radius=8
                    ),
                    ft.Row([
                        ft.Icon(ft.icons.IMAGE, size=14),
                        ft.Text(self.message.file_name or "Image", size=12)
                    ], spacing=5)
                ], spacing=5),
                padding=5,
                border_radius=8
            )
        # Check if it's an audio file (voice message)
        elif self.message.file_type and self.message.file_type.startswith("audio/"):
            # Extract duration from message content if available
            # Format: "🎤 Voice message (45.2s)"
            duration = None
            if "(" in self.message.content and "s)" in self.message.content:
                try:
                    duration_str = self.message.content.split("(")[1].split("s)")[0]
                    duration = float(duration_str)
                except:
                    pass
            
            # Audio player
            return ft.Container(
                content=AudioPlayerSimple(
                    audio_url=file_url,
                    duration=duration
                ),
                padding=5,
                border_radius=8
            )
        else:
            # File attachment with download button
            file_icon = self._get_file_icon()
            
            return ft.Container(
                content=ft.Row([
                    ft.Icon(file_icon, size=32, color=config.PRIMARY_COLOR),
                    ft.Column([
                        ft.Text(self.message.file_name or "File", size=13, weight=ft.FontWeight.BOLD),
                        ft.Text(self.message.file_type or "Unknown type", size=11, color=config.TEXT_SECONDARY)
                    ], spacing=2, expand=True),
                    ft.IconButton(
                        icon=ft.icons.DOWNLOAD,
                        tooltip="Download",
                        icon_size=20,
                        on_click=lambda e: self._handle_download(file_url, self.message.file_name)
                    )
                ], spacing=10, alignment=ft.MainAxisAlignment.START),
                bgcolor=ft.colors.GREY_100,
                padding=10,
                border_radius=8,
                border=ft.border.all(1, ft.colors.GREY_300)
            )
    
    def _get_file_icon(self):
        """Get appropriate icon for file type"""
        if not self.message.file_type:
            return ft.icons.ATTACH_FILE
        
        file_type = self.message.file_type.lower()
        
        if "pdf" in file_type:
            return ft.icons.PICTURE_AS_PDF
        elif "word" in file_type or "document" in file_type:
            return ft.icons.DESCRIPTION
        elif "audio" in file_type:
            return ft.icons.AUDIO_FILE
        elif "video" in file_type:
            return ft.icons.VIDEO_FILE
        elif "zip" in file_type or "rar" in file_type:
            return ft.icons.FOLDER_ZIP
        else:
            return ft.icons.ATTACH_FILE
    
    def _handle_download(self, file_url: str, file_name: str):
        """Handle file download"""
        if self.on_download:
            self.on_download(file_url, file_name)
        else:
            # Default: Open in browser
            import webbrowser
            webbrowser.open(file_url)
    
    def _show_context_menu(self, e):
        """Show context menu with Edit, Delete, Copy options"""
        if not self.page:
            return
        
        menu_items = []
        
        # Copy option
        if self.on_copy:
            menu_items.append(
                ft.ListTile(
                    leading=ft.Icon(ft.icons.CONTENT_COPY, size=20),
                    title=ft.Text("Copy"),
                    on_click=lambda _: self._handle_menu_action("copy")
                )
            )
        
        # Edit option
        if self.on_edit:
            menu_items.append(
                ft.ListTile(
                    leading=ft.Icon(ft.icons.EDIT, size=20),
                    title=ft.Text("Edit"),
                    on_click=lambda _: self._handle_menu_action("edit")
                )
            )
        
        # Delete option
        if self.on_delete:
            menu_items.append(
                ft.ListTile(
                    leading=ft.Icon(ft.icons.DELETE, size=20, color=ft.colors.RED),
                    title=ft.Text("Delete", color=ft.colors.RED),
                    on_click=lambda _: self._handle_menu_action("delete")
                )
            )
        
        if not menu_items:
            return
        
        # Create and show menu dialog
        menu_dialog = ft.AlertDialog(
            content=ft.Container(
                content=ft.Column(menu_items, spacing=0, tight=True),
                padding=0
            ),
            actions=[
                ft.TextButton("Cancel", on_click=lambda _: self._close_menu())
            ],
            actions_alignment=ft.MainAxisAlignment.CENTER
        )
        
        self.page.dialog = menu_dialog
        menu_dialog.open = True
        self.page.update()
    
    def _handle_menu_action(self, action: str):
        """Handle menu action selection"""
        self._close_menu()
        
        if action == "copy" and self.on_copy:
            self.on_copy(self.message)
        elif action == "edit" and self.on_edit:
            self.on_edit(self.message)
        elif action == "delete" and self.on_delete:
            self.on_delete(self.message)
    
    def _close_menu(self):
        """Close context menu"""
        if self.page and self.page.dialog:
            self.page.dialog.open = False
            self.page.update()
    
    def _handle_reaction_click(self, emoji: str, is_my_reaction: bool):
        """Handle clicking on a reaction"""
        if self.on_reaction_click:
            self.on_reaction_click(self.message, emoji, is_my_reaction)
    
    def _handle_add_reaction(self):
        """Handle clicking add reaction button"""
        if self.on_add_reaction:
            self.on_add_reaction(self.message)
    
    def _build_system_message(self):
        """Build system message UI (centered, italic, gray)"""
        return ft.Container(
            content=ft.Row(
                controls=[
                    ft.Text(
                        self.message.content,
                        size=12,
                        italic=True,
                        color=config.TEXT_SECONDARY,
                        text_align=ft.TextAlign.CENTER
                    )
                ],
                alignment=ft.MainAxisAlignment.CENTER
            ),
            padding=ft.padding.symmetric(vertical=8, horizontal=20),
            alignment=ft.alignment.center
        )

