"""
Conversation item component
Displays conversation in list
"""
import flet as ft
from typing import Optional, Callable

from ..models import Conversation, User
from ..config import config
from ..utils.formatters import format_timestamp, truncate_text


class ConversationItem(ft.UserControl):
    """
    Conversation list item component
    Shows conversation preview with last message
    """
    
    def __init__(
        self,
        conversation: Conversation,
        current_user: User,
        page: ft.Page,
        is_selected: bool = False,
        on_click: Optional[Callable] = None
    ):
        """
        Initialize conversation item
        
        Args:
            conversation: Conversation object
            page: Flet page for async operations
            current_user: Current user
            is_selected: Whether this conversation is selected
            on_click: Callback when clicked
        """
        super().__init__()
        self.conversation = conversation
        self.current_user = current_user
        self.page_ref = page
        self.is_selected = is_selected
        self.on_click_callback = on_click
    
    def build(self):
        """Build conversation item UI"""
        # Get display name
        display_name = self.conversation.get_display_name(self.current_user.id)
        
        # Last message preview
        last_msg = truncate_text(self.conversation.last_message or "No messages yet", 35)
        
        # Time
        time_str = format_timestamp(self.conversation.updated_at)
        
        # Icon based on type
        icon = ft.icons.GROUP if self.conversation.type.value == "group" else ft.icons.PERSON
        
        return ft.Container(
            content=ft.Row([
                ft.Icon(
                    icon,
                    size=30,
                    color=config.PRIMARY_COLOR
                ),
                ft.Column([
                    ft.Text(display_name, size=14, weight=ft.FontWeight.BOLD),
                    ft.Text(last_msg, size=12, color=config.TEXT_SECONDARY)
                ], expand=True, spacing=2),
                ft.Text(time_str, size=10, color=config.TEXT_SECONDARY)
            ], spacing=10),
            bgcolor=config.PRIMARY_COLOR + "20" if self.is_selected else ft.colors.WHITE,
            padding=10,
            border_radius=8,
            on_click=self._handle_click,
            ink=True
        )
    
    def _handle_click(self, e):
        """Handle click event"""
        if self.on_click_callback:
            # Wrap async callback with page.run_task
            import asyncio
            import inspect
            if inspect.iscoroutinefunction(self.on_click_callback):
                self.page_ref.run_task(self.on_click_callback, self.conversation)
            else:
                self.on_click_callback(self.conversation)

