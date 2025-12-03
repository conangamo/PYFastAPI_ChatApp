"""
Register screen
"""
import flet as ft
from typing import Callable

from ..api.client import get_api_client
from ..config import config


class RegisterScreen(ft.UserControl):
    """
    Register screen component
    Handles new user registration
    """
    
    def __init__(self, page: ft.Page, on_register_success: Callable, on_go_to_login: Callable):
        """
        Initialize register screen
        
        Args:
            page: Flet page
            on_register_success: Callback when registration succeeds
            on_go_to_login: Callback to switch to login screen
        """
        super().__init__()
        self.page = page
        self.on_register_success = on_register_success
        self.on_go_to_login = on_go_to_login
        
        # Form fields
        self.username_field = ft.TextField(
            label="Username",
            hint_text="Choose a username",
            autofocus=True,
            width=350
        )
        
        self.email_field = ft.TextField(
            label="Email",
            hint_text="Enter your email",
            keyboard_type=ft.KeyboardType.EMAIL,
            width=350
        )
        
        self.display_name_field = ft.TextField(
            label="Display Name",
            hint_text="Enter your display name",
            width=350
        )
        
        self.password_field = ft.TextField(
            label="Password",
            hint_text="Choose a password (min 6 characters)",
            password=True,
            can_reveal_password=True,
            width=350
        )
        
        self.confirm_password_field = ft.TextField(
            label="Confirm Password",
            hint_text="Re-enter your password",
            password=True,
            can_reveal_password=True,
            width=350,
            on_submit=lambda _: self.handle_register(None)
        )
        
        self.error_text = ft.Text(
            value="",
            color=ft.colors.RED_400,
            size=14,
            visible=False
        )
        
        self.register_button = ft.ElevatedButton(
            text="Register",
            width=350,
            height=50,
            on_click=self.handle_register,
            style=ft.ButtonStyle(
                bgcolor=config.PRIMARY_COLOR,
                color=ft.colors.WHITE
            )
        )
        
        self.login_link = ft.TextButton(
            text="Already have an account? Login here",
            on_click=lambda _: on_go_to_login()
        )
    
    def build(self):
        """Build register screen UI"""
        return ft.Container(
            content=ft.Column(
                [
                    # Logo/Title
                    ft.Container(height=30),
                    ft.Icon(
                        name=ft.icons.PERSON_ADD_ROUNDED,
                        size=60,
                        color=config.PRIMARY_COLOR
                    ),
                    ft.Text(
                        "Create Account",
                        size=32,
                        weight=ft.FontWeight.BOLD,
                        color=config.PRIMARY_COLOR
                    ),
                    ft.Text(
                        "Join the conversation!",
                        size=16,
                        color=config.TEXT_SECONDARY
                    ),
                    ft.Container(height=20),
                    
                    # Register form
                    self.username_field,
                    self.email_field,
                    self.display_name_field,
                    self.password_field,
                    self.confirm_password_field,
                    self.error_text,
                    ft.Container(height=10),
                    self.register_button,
                    ft.Container(height=15),
                    self.login_link,
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                alignment=ft.MainAxisAlignment.CENTER,
                scroll=ft.ScrollMode.AUTO
            ),
            alignment=ft.alignment.center,
            expand=True,
            bgcolor=config.BACKGROUND_COLOR
        )
    
    async def handle_register(self, e):
        """Handle register button click"""
        # Get values
        username = self.username_field.value
        email = self.email_field.value
        display_name = self.display_name_field.value
        password = self.password_field.value
        confirm_password = self.confirm_password_field.value
        
        # Validate inputs
        if not all([username, email, display_name, password, confirm_password]):
            self.show_error("Please fill in all fields")
            return
        
        if len(password) < 6:
            self.show_error("Password must be at least 6 characters")
            return
        
        if password != confirm_password:
            self.show_error("Passwords do not match")
            return
        
        # Validate email format (basic)
        if "@" not in email or "." not in email:
            self.show_error("Please enter a valid email address")
            return
        
        # Show loading
        self.register_button.disabled = True
        self.register_button.text = "Creating account..."
        self.error_text.visible = False
        self.update()
        
        try:
            # Call API
            api = get_api_client()
            user_data = await api.register(
                username=username,
                email=email,
                password=password,
                display_name=display_name
            )
            
            # Success!
            self.show_success()
            
            # Switch to login after a moment
            import asyncio
            await asyncio.sleep(1.5)
            self.on_register_success()
        
        except Exception as error:
            # Show error
            error_msg = str(error)
            if "already exists" in error_msg.lower() or "409" in error_msg:
                self.show_error("Username or email already exists")
            elif "400" in error_msg:
                self.show_error("Invalid input. Please check your information.")
            else:
                self.show_error(f"Registration failed: {error_msg}")
            
            # Reset button
            self.register_button.disabled = False
            self.register_button.text = "Register"
            self.update()
    
    def show_error(self, message: str):
        """Show error message"""
        self.error_text.value = message
        self.error_text.color = ft.colors.RED_400
        self.error_text.visible = True
        self.update()
    
    def show_success(self):
        """Show success message"""
        self.error_text.value = "✓ Account created successfully! Redirecting to login..."
        self.error_text.color = ft.colors.GREEN_400
        self.error_text.visible = True
        self.register_button.text = "Success!"
        self.update()
    
    def clear_form(self):
        """Clear form fields"""
        self.username_field.value = ""
        self.email_field.value = ""
        self.display_name_field.value = ""
        self.password_field.value = ""
        self.confirm_password_field.value = ""
        self.error_text.visible = False
        self.update()

