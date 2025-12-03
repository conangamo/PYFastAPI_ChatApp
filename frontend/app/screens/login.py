"""
Login screen
"""
import flet as ft
from typing import Callable

from ..api.client import get_api_client
from ..utils.storage import storage
from ..config import config


class LoginScreen(ft.UserControl):
    """
    Login screen component
    Handles user authentication
    """
    
    def __init__(self, page: ft.Page, on_login_success: Callable, on_go_to_register: Callable):
        """
        Initialize login screen
        
        Args:
            page: Flet page
            on_login_success: Callback when login succeeds (token, user)
            on_go_to_register: Callback to switch to register screen
        """
        super().__init__()
        self.page = page
        self.on_login_success = on_login_success
        self.on_go_to_register = on_go_to_register
        
        # Form fields
        self.username_field = ft.TextField(
            label="Username",
            hint_text="Enter your username",
            autofocus=True,
            width=350,
            on_submit=lambda _: self.password_field.focus()
        )
        
        self.password_field = ft.TextField(
            label="Password",
            hint_text="Enter your password",
            password=True,
            can_reveal_password=True,
            width=350,
            on_submit=lambda _: self.handle_login(None)
        )
        
        self.error_text = ft.Text(
            value="",
            color=ft.colors.RED_400,
            size=14,
            visible=False
        )
        
        self.login_button = ft.ElevatedButton(
            text="Login",
            width=350,
            height=50,
            on_click=self.handle_login,
            style=ft.ButtonStyle(
                bgcolor=config.PRIMARY_COLOR,
                color=ft.colors.WHITE
            )
        )
        
        self.register_link = ft.TextButton(
            text="Don't have an account? Register here",
            on_click=lambda _: on_go_to_register()
        )
    
    def build(self):
        """Build login screen UI"""
        return ft.Container(
            content=ft.Column(
                [
                    # Logo/Title
                    ft.Container(height=50),
                    ft.Icon(
                        name=ft.icons.CHAT_BUBBLE_ROUNDED,
                        size=80,
                        color=config.PRIMARY_COLOR
                    ),
                    ft.Text(
                        config.APP_NAME,
                        size=36,
                        weight=ft.FontWeight.BOLD,
                        color=config.PRIMARY_COLOR
                    ),
                    ft.Text(
                        "Welcome back!",
                        size=16,
                        color=config.TEXT_SECONDARY
                    ),
                    ft.Container(height=30),
                    
                    # Login form
                    self.username_field,
                    self.password_field,
                    self.error_text,
                    ft.Container(height=10),
                    self.login_button,
                    ft.Container(height=20),
                    self.register_link,
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                alignment=ft.MainAxisAlignment.CENTER,
            ),
            alignment=ft.alignment.center,
            expand=True,
            bgcolor=config.BACKGROUND_COLOR
        )
    
    async def handle_login(self, e):
        """Handle login button click"""
        # Validate inputs
        username = self.username_field.value
        password = self.password_field.value
        
        if not username or not password:
            self.show_error("Please enter username and password")
            return
        
        # Show loading
        self.login_button.disabled = True
        self.login_button.text = "Logging in..."
        self.error_text.visible = False
        self.update()
        
        try:
            # Call API
            api = get_api_client()
            result = await api.login(username, password)
            
            # Save token
            token = result["access_token"]
            api.set_token(token)
            storage.set_token(token)
            
            # Get user profile
            user = await api.get_current_user()
            storage.set_user(user.to_dict())
            
            # Success!
            self.on_login_success(token, user)
        
        except Exception as error:
            # Show error
            error_msg = str(error)
            if "401" in error_msg:
                self.show_error("Invalid username or password")
            elif "404" in error_msg:
                self.show_error("User not found")
            else:
                self.show_error(f"Login failed: {error_msg}")
            
            # Reset button
            self.login_button.disabled = False
            self.login_button.text = "Login"
            self.update()
    
    def show_error(self, message: str):
        """Show error message"""
        self.error_text.value = message
        self.error_text.visible = True
        self.update()
    
    def clear_form(self):
        """Clear form fields"""
        self.username_field.value = ""
        self.password_field.value = ""
        self.error_text.visible = False
        self.update()

