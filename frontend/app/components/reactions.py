"""
Reaction components for messages
"""
import flet as ft
from typing import Optional, Callable, Dict, List

from ..models import Message
from ..config import config


# Quick reactions - most commonly used emojis
QUICK_REACTIONS = ["👍", "❤️", "😂", "😮", "😢", "🔥"]


class ReactionPicker(ft.UserControl):
    """
    Emoji picker for adding reactions
    Shows quick reactions + more button
    """
    
    def __init__(
        self,
        page: ft.Page,
        on_reaction_selected: Optional[Callable] = None
    ):
        """
        Initialize reaction picker
        
        Args:
            page: Flet page
            on_reaction_selected: Callback when emoji selected (emoji: str)
        """
        super().__init__()
        self.page_ref = page
        self.on_reaction_selected = on_reaction_selected
    
    def build(self):
        """Build reaction picker UI"""
        # Quick reaction buttons
        reaction_buttons = []
        
        for emoji in QUICK_REACTIONS:
            btn = ft.IconButton(
                content=ft.Text(emoji, size=20),
                on_click=lambda e, em=emoji: self._handle_reaction(em),
                tooltip=f"React with {emoji}"
            )
            reaction_buttons.append(btn)
        
        return ft.Container(
            content=ft.Row(
                reaction_buttons,
                spacing=5,
                scroll=ft.ScrollMode.AUTO
            ),
            padding=5,
            bgcolor=ft.colors.SURFACE_VARIANT,
            border_radius=8
        )
    
    def _handle_reaction(self, emoji: str):
        """Handle reaction selection"""
        if self.on_reaction_selected:
            self.on_reaction_selected(emoji)


class ReactionDisplay(ft.UserControl):
    """
    Display reactions under a message
    Shows emoji buttons with counts
    """
    
    def __init__(
        self,
        message: Message,
        current_user_id: str,
        on_reaction_click: Optional[Callable] = None,
        on_add_reaction: Optional[Callable] = None
    ):
        """
        Initialize reaction display
        
        Args:
            message: Message with reactions
            current_user_id: Current user ID
            on_reaction_click: Callback when reaction clicked (emoji, is_my_reaction)
            on_add_reaction: Callback when + button clicked
        """
        super().__init__()
        self.message = message
        self.current_user_id = current_user_id
        self.on_reaction_click = on_reaction_click
        self.on_add_reaction = on_add_reaction
    
    def build(self):
        """Build reaction display UI"""
        if not self.message.has_reactions():
            # Show only + button if no reactions
            return self._build_add_button()
        
        # Build reaction buttons
        reaction_widgets = []
        
        for emoji, users in self.message.reactions.items():
            count = len(users)
            is_my_reaction = self.message.has_reacted(emoji, self.current_user_id)
            
            # Style based on whether current user reacted
            bgcolor = config.PRIMARY_COLOR if is_my_reaction else ft.colors.SURFACE_VARIANT
            text_color = ft.colors.WHITE if is_my_reaction else config.TEXT_PRIMARY
            
            reaction_btn = ft.Container(
                content=ft.Row([
                    ft.Text(emoji, size=14),
                    ft.Text(str(count), size=12, weight=ft.FontWeight.BOLD)
                ], spacing=3, tight=True),
                padding=ft.padding.symmetric(horizontal=8, vertical=4),
                bgcolor=bgcolor,
                border_radius=12,
                ink=True,
                on_click=lambda e, em=emoji, mine=is_my_reaction: self._handle_reaction_click(em, mine),
                tooltip=self._get_tooltip(emoji, users)
            )
            reaction_widgets.append(reaction_btn)
        
        # Add + button
        reaction_widgets.append(self._build_add_button())
        
        return ft.Container(
            content=ft.Row(
                reaction_widgets,
                spacing=5,
                scroll=ft.ScrollMode.AUTO,
                wrap=True
            ),
            padding=ft.padding.only(top=5)
        )
    
    def _build_add_button(self):
        """Build the + add reaction button"""
        return ft.Container(
            content=ft.Icon(ft.icons.ADD, size=14, color=config.TEXT_SECONDARY),
            padding=ft.padding.symmetric(horizontal=6, vertical=4),
            bgcolor=ft.colors.SURFACE_VARIANT,
            border_radius=12,
            ink=True,
            on_click=lambda e: self._handle_add_click(),
            tooltip="Add reaction"
        )
    
    def _handle_reaction_click(self, emoji: str, is_my_reaction: bool):
        """Handle clicking on a reaction"""
        if self.on_reaction_click:
            self.on_reaction_click(emoji, is_my_reaction)
    
    def _handle_add_click(self):
        """Handle clicking the + button"""
        if self.on_add_reaction:
            self.on_add_reaction()
    
    def _get_tooltip(self, emoji: str, users: List[Dict[str, str]]) -> str:
        """Generate tooltip showing who reacted"""
        if not users:
            return emoji
        
        if len(users) == 1:
            return f"{users[0].get('username', 'Someone')} reacted with {emoji}"
        elif len(users) == 2:
            return f"{users[0].get('username', 'Someone')} and {users[1].get('username', 'someone else')} reacted with {emoji}"
        else:
            others_count = len(users) - 1
            return f"{users[0].get('username', 'Someone')} and {others_count} others reacted with {emoji}"


class ReactionPickerDialog:
    """
    Dialog showing reaction picker
    """
    
    def __init__(
        self,
        page: ft.Page,
        on_reaction_selected: Optional[Callable] = None
    ):
        """
        Initialize reaction picker dialog
        
        Args:
            page: Flet page
            on_reaction_selected: Callback when emoji selected
        """
        self.page = page
        self.on_reaction_selected = on_reaction_selected
        self.dialog = None
    
    def show(self):
        """Show reaction picker dialog"""
        picker = ReactionPicker(
            page=self.page,
            on_reaction_selected=self._handle_selection
        )
        
        self.dialog = ft.AlertDialog(
            title=ft.Text("React with emoji"),
            content=ft.Container(
                content=picker,
                width=300,
                padding=10
            ),
            actions=[
                ft.TextButton("Cancel", on_click=lambda _: self._close())
            ],
            actions_alignment=ft.MainAxisAlignment.CENTER
        )
        
        self.page.dialog = self.dialog
        self.dialog.open = True
        self.page.update()
    
    def _handle_selection(self, emoji: str):
        """Handle emoji selection"""
        self._close()
        if self.on_reaction_selected:
            self.on_reaction_selected(emoji)
    
    def _close(self):
        """Close dialog"""
        if self.dialog:
            self.dialog.open = False
            self.page.update()

