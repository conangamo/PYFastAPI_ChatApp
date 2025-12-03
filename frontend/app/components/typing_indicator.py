"""
Typing Indicator Component
Shows "User is typing..." animated indicator
"""
import flet as ft


class TypingIndicator(ft.UserControl):
    """
    Animated typing indicator component
    Displays "Username is typing..." with animated dots
    """
    
    def __init__(self, username: str):
        """
        Initialize typing indicator
        
        Args:
            username: Name of the user who is typing
        """
        super().__init__()
        self.username = username
        self.dots_animation = None
    
    def build(self):
        """Build typing indicator UI"""
        # Animated dots (simple version - just text with dots)
        dots_text = ft.Text(
            "...",
            size=14,
            color=ft.colors.GREY_600,
            animate_opacity=ft.animation.Animation(1000, "easeInOut")
        )
        
        return ft.Container(
            content=ft.Row([
                ft.Icon(
                    ft.icons.EDIT_NOTE,
                    size=16,
                    color=ft.colors.GREY_500
                ),
                ft.Text(
                    f"{self.username} is typing",
                    size=13,
                    color=ft.colors.GREY_600,
                    italic=True
                ),
                dots_text
            ], spacing=4),
            padding=8,
            bgcolor=ft.colors.with_opacity(0.05, ft.colors.GREY),
            border_radius=6,
            margin=ft.margin.only(left=10, bottom=5, right=10)
        )


class TypingIndicatorCompact(ft.UserControl):
    """
    Compact typing indicator (just icon and text, no animation)
    For use in chat header or small spaces
    """
    
    def __init__(self, username: str):
        super().__init__()
        self.username = username
    
    def build(self):
        """Build compact typing indicator"""
        return ft.Row([
            ft.Icon(
                ft.icons.EDIT,
                size=12,
                color=ft.colors.GREEN_600
            ),
            ft.Text(
                "typing...",
                size=10,
                color=ft.colors.GREEN_600,
                italic=True
            )
        ], spacing=2)

