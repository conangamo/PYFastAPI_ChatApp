"""
Profile dialog components
"""
import flet as ft
from typing import Optional, Callable

from ..models import User
from ..config import config
from ..utils.formatters import format_timestamp


class ProfileDialog:
    """Profile view dialog"""
    
    def __init__(
        self,
        user: User,
        page: ft.Page,
        on_edit: Optional[Callable] = None
    ):
        """
        Initialize profile dialog
        
        Args:
            user: User to display
            page: Flet page
            on_edit: Callback when edit is clicked
        """
        self.user = user
        self.page = page
        self.on_edit = on_edit
        self.dialog = None
    
    def show(self):
        """Show profile dialog"""
        profile_content = ft.Column([
            # Profile header
            ft.Container(
                content=ft.Row([
                    ft.Icon(ft.icons.ACCOUNT_CIRCLE, size=60, color=config.PRIMARY_COLOR),
                    ft.Column([
                        ft.Text(self.user.display_name, size=20, weight=ft.FontWeight.BOLD),
                        ft.Text(f"@{self.user.username}", size=14, color=config.TEXT_SECONDARY)
                    ], spacing=2)
                ], spacing=15),
                padding=20,
                bgcolor=ft.colors.BLUE_GREY_50,
                border_radius=8
            ),
            ft.Divider(),
            # Profile info
            ft.ListTile(
                leading=ft.Icon(ft.icons.EMAIL),
                title=ft.Text("Email"),
                subtitle=ft.Text(self.user.email)
            ),
            ft.ListTile(
                leading=ft.Icon(ft.icons.CALENDAR_TODAY),
                title=ft.Text("Member since"),
                subtitle=ft.Text(format_timestamp(self.user.created_at))
            ),
        ], spacing=10)
        
        self.dialog = ft.AlertDialog(
            title=ft.Text("My Profile"),
            content=ft.Container(
                content=profile_content,
                width=400
            ),
            actions=[
                ft.TextButton("Edit Profile", on_click=self._handle_edit),
                ft.TextButton("Close", on_click=self._close)
            ]
        )
        
        self.page.dialog = self.dialog
        self.dialog.open = True
        self.page.update()
    
    def _handle_edit(self, e):
        """Handle edit button click"""
        self.close()
        if self.on_edit:
            self.on_edit()
    
    def _close(self, e):
        """Close dialog"""
        self.close()
    
    def close(self):
        """Close dialog"""
        if self.dialog:
            self.dialog.open = False
            self.page.update()


class EditProfileDialog:
    """Edit profile dialog"""
    
    def __init__(
        self,
        user: User,
        page: ft.Page,
        on_save: Optional[Callable] = None
    ):
        """
        Initialize edit profile dialog
        
        Args:
            user: User to edit
            page: Flet page
            on_save: Callback when saved (display_name, email)
        """
        self.user = user
        self.page = page
        self.on_save = on_save
        self.dialog = None
        
        # Input fields
        self.display_name_input = ft.TextField(
            label="Display Name",
            value=user.display_name,
            width=380
        )
        
        self.email_input = ft.TextField(
            label="Email",
            value=user.email,
            width=380
        )
    
    def show(self):
        """Show edit profile dialog"""
        self.dialog = ft.AlertDialog(
            title=ft.Text("Edit Profile"),
            content=ft.Container(
                content=ft.Column([
                    self.display_name_input,
                    self.email_input,
                    ft.Text(
                        "Note: Username cannot be changed",
                        size=12,
                        color=config.TEXT_SECONDARY,
                        italic=True
                    )
                ], spacing=15),
                width=400
            ),
            actions=[
                ft.TextButton("Cancel", on_click=self._close),
                ft.ElevatedButton(
                    "Save Changes",
                    on_click=self._handle_save,
                    style=ft.ButtonStyle(
                        bgcolor=config.SUCCESS_COLOR,
                        color=ft.colors.WHITE
                    )
                )
            ]
        )
        
        self.page.dialog = self.dialog
        self.dialog.open = True
        self.page.update()
    
    def _handle_save(self, e):
        """Handle save button click"""
        display_name = self.display_name_input.value
        email = self.email_input.value
        
        # Validate
        if not display_name or not display_name.strip():
            self._show_error("Display name is required")
            return
        
        if not email or not email.strip():
            self._show_error("Email is required")
            return
        
        self.close()
        
        if self.on_save:
            self.on_save(display_name.strip(), email.strip())
    
    def _show_error(self, message: str):
        """Show error notification"""
        self.page.snack_bar = ft.SnackBar(
            content=ft.Text(message),
            bgcolor=config.ERROR_COLOR
        )
        self.page.snack_bar.open = True
        self.page.update()
    
    def _close(self, e):
        """Close dialog"""
        self.close()
    
    def close(self):
        """Close dialog"""
        if self.dialog:
            self.dialog.open = False
            self.page.update()

