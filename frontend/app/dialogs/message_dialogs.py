"""
Message management dialogs
Edit and delete message dialogs
"""
import flet as ft
from typing import Optional, Callable

from ..models import Message
from ..config import config


class EditMessageDialog:
    """Dialog for editing a message"""
    
    def __init__(
        self,
        message: Message,
        page: ft.Page,
        on_save: Optional[Callable] = None
    ):
        """
        Initialize edit message dialog
        
        Args:
            message: Message to edit
            page: Flet page
            on_save: Callback when message is saved (message_id, new_content)
        """
        self.message = message
        self.page = page
        self.on_save = on_save
        self.dialog = None
        self.content_input = None
    
    def show(self):
        """Show edit message dialog"""
        self.content_input = ft.TextField(
            value=self.message.content,
            multiline=True,
            min_lines=3,
            max_lines=10,
            label="Edit your message",
            autofocus=True,
            on_submit=lambda _: self._handle_save()
        )
        
        self.dialog = ft.AlertDialog(
            title=ft.Text("Edit Message"),
            content=ft.Container(
                content=self.content_input,
                width=400,
                padding=10
            ),
            actions=[
                ft.TextButton(
                    "Cancel",
                    on_click=lambda _: self._close()
                ),
                ft.ElevatedButton(
                    "Save",
                    icon=ft.icons.CHECK,
                    on_click=lambda _: self._handle_save()
                )
            ],
            actions_alignment=ft.MainAxisAlignment.END
        )
        
        self.page.dialog = self.dialog
        self.dialog.open = True
        self.page.update()
    
    def _handle_save(self):
        """Handle save button click"""
        new_content = self.content_input.value.strip()
        
        if not new_content:
            self.page.snack_bar = ft.SnackBar(
                content=ft.Text("Message cannot be empty"),
                bgcolor=ft.colors.RED_400
            )
            self.page.snack_bar.open = True
            self.page.update()
            return
        
        if new_content == self.message.content:
            # No changes
            self._close()
            return
        
        self._close()
        
        if self.on_save:
            self.on_save(self.message.id, new_content)
    
    def _close(self):
        """Close dialog"""
        if self.dialog:
            self.dialog.open = False
            self.page.update()


class DeleteMessageDialog:
    """Dialog for confirming message deletion"""
    
    def __init__(
        self,
        message: Message,
        page: ft.Page,
        on_confirm: Optional[Callable] = None
    ):
        """
        Initialize delete confirmation dialog
        
        Args:
            message: Message to delete
            page: Flet page
            on_confirm: Callback when deletion is confirmed (message_id)
        """
        self.message = message
        self.page = page
        self.on_confirm = on_confirm
        self.dialog = None
    
    def show(self):
        """Show delete confirmation dialog"""
        self.dialog = ft.AlertDialog(
            title=ft.Text("Delete Message?"),
            content=ft.Column([
                ft.Text(
                    "Are you sure you want to delete this message?",
                    size=14
                ),
                ft.Container(height=10),
                ft.Container(
                    content=ft.Text(
                        self.message.content[:100] + ("..." if len(self.message.content) > 100 else ""),
                        size=12,
                        italic=True,
                        color=config.TEXT_SECONDARY
                    ),
                    padding=10,
                    bgcolor=ft.colors.GREY_100,
                    border_radius=5
                ),
                ft.Container(height=10),
                ft.Text(
                    "This action cannot be undone.",
                    size=12,
                    color=ft.colors.RED,
                    weight=ft.FontWeight.BOLD
                )
            ], tight=True, spacing=5),
            actions=[
                ft.TextButton(
                    "Cancel",
                    on_click=lambda _: self._close()
                ),
                ft.ElevatedButton(
                    "Delete",
                    icon=ft.icons.DELETE,
                    bgcolor=ft.colors.RED,
                    color=ft.colors.WHITE,
                    on_click=lambda _: self._handle_confirm()
                )
            ],
            actions_alignment=ft.MainAxisAlignment.END
        )
        
        self.page.dialog = self.dialog
        self.dialog.open = True
        self.page.update()
    
    def _handle_confirm(self):
        """Handle confirm button click"""
        self._close()
        
        if self.on_confirm:
            self.on_confirm(self.message.id)
    
    def _close(self):
        """Close dialog"""
        if self.dialog:
            self.dialog.open = False
            self.page.update()

