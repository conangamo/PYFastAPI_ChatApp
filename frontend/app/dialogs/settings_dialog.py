"""
Settings dialog component
"""
import flet as ft
from typing import Optional

from ..config import config


class SettingsDialog:
    """Application settings dialog"""
    
    def __init__(self, page: ft.Page):
        """
        Initialize settings dialog
        
        Args:
            page: Flet page
        """
        self.page = page
        self.dialog = None
    
    def show(self):
        """Show settings dialog"""
        settings_content = ft.Column([
            ft.Text("Application Settings", size=16, weight=ft.FontWeight.BOLD),
            ft.Divider(),
            
            # Theme setting (placeholder - would need actual implementation)
            ft.ListTile(
                leading=ft.Icon(ft.icons.DARK_MODE),
                title=ft.Text("Dark Mode"),
                subtitle=ft.Text("Switch between light and dark theme"),
                trailing=ft.Switch(value=False, disabled=True)
            ),
            
            # Notifications
            ft.ListTile(
                leading=ft.Icon(ft.icons.NOTIFICATIONS),
                title=ft.Text("Notifications"),
                subtitle=ft.Text("Enable desktop notifications"),
                trailing=ft.Switch(value=True, disabled=True)
            ),
            
            # Sounds
            ft.ListTile(
                leading=ft.Icon(ft.icons.VOLUME_UP),
                title=ft.Text("Sound"),
                subtitle=ft.Text("Play sound for new messages"),
                trailing=ft.Switch(value=True, disabled=True)
            ),
            
            ft.Divider(),
            
            # About
            ft.ListTile(
                leading=ft.Icon(ft.icons.INFO),
                title=ft.Text("About"),
                subtitle=ft.Text("Chat App v1.0.0")
            ),
        ], spacing=5)
        
        self.dialog = ft.AlertDialog(
            title=ft.Text("Settings"),
            content=ft.Container(
                content=settings_content,
                width=400,
                height=400
            ),
            actions=[
                ft.TextButton("Close", on_click=self._close)
            ]
        )
        
        self.page.dialog = self.dialog
        self.dialog.open = True
        self.page.update()
    
    def _close(self, e):
        """Close dialog"""
        self.close()
    
    def close(self):
        """Close dialog"""
        if self.dialog:
            self.dialog.open = False
            self.page.update()

