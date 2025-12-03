"""
Chat dialog components
New chat, group creation, group info dialogs
"""
import flet as ft
from typing import Optional, Callable, List

from ..models import User, Conversation
from ..config import config
from ..utils.formatters import format_timestamp


class NewChatDialog:
    """New chat type selection dialog"""
    
    def __init__(
        self,
        page: ft.Page,
        on_direct_chat: Optional[Callable] = None,
        on_group_chat: Optional[Callable] = None
    ):
        """
        Initialize new chat dialog
        
        Args:
            page: Flet page
            on_direct_chat: Callback for direct chat selection
            on_group_chat: Callback for group chat selection
        """
        self.page = page
        self.on_direct_chat = on_direct_chat
        self.on_group_chat = on_group_chat
        self.dialog = None
    
    def show(self):
        """Show new chat type selection dialog"""
        self.dialog = ft.AlertDialog(
            title=ft.Text("Start a conversation"),
            content=ft.Container(
                content=ft.Column([
                    ft.Text("Choose chat type:", size=14, weight=ft.FontWeight.BOLD),
                    ft.Divider(),
                    ft.ListTile(
                        leading=ft.Icon(ft.icons.PERSON, color=config.PRIMARY_COLOR),
                        title=ft.Text("Direct Chat (1-on-1)"),
                        subtitle=ft.Text("Chat with one person"),
                        on_click=self._handle_direct_chat
                    ),
                    ft.ListTile(
                        leading=ft.Icon(ft.icons.GROUP, color=config.PRIMARY_COLOR),
                        title=ft.Text("Group Chat"),
                        subtitle=ft.Text("Chat with multiple people"),
                        on_click=self._handle_group_chat
                    )
                ], spacing=10),
                width=400
            ),
            actions=[
                ft.TextButton("Cancel", on_click=self._close)
            ]
        )
        
        self.page.dialog = self.dialog
        self.dialog.open = True
        self.page.update()
    
    def _handle_direct_chat(self, e):
        """Handle direct chat selection"""
        self.close()
        if self.on_direct_chat:
            self.on_direct_chat()
    
    def _handle_group_chat(self, e):
        """Handle group chat selection"""
        self.close()
        if self.on_group_chat:
            self.on_group_chat()
    
    def _close(self, e):
        """Close dialog"""
        self.close()
    
    def close(self):
        """Close dialog"""
        if self.dialog:
            self.dialog.open = False
            self.page.update()


class DirectChatDialog:
    """Direct chat user selection dialog"""
    
    def __init__(
        self,
        users: List[User],
        page: ft.Page,
        on_select: Optional[Callable] = None
    ):
        """
        Initialize direct chat dialog
        
        Args:
            users: List of users to choose from
            page: Flet page
            on_select: Callback when user is selected (user)
        """
        self.users = users
        self.page = page
        self.on_select = on_select
        self.dialog = None
    
    def show(self):
        """Show user selection dialog"""
        # Create user list
        user_list = ft.ListView(
            controls=[
                ft.ListTile(
                    leading=ft.Icon(ft.icons.PERSON),
                    title=ft.Text(u.display_name),
                    subtitle=ft.Text(f"@{u.username}"),
                    on_click=lambda e, user=u: self._handle_select(user)
                )
                for u in self.users
            ],
            expand=True,
            height=300
        )
        
        self.dialog = ft.AlertDialog(
            title=ft.Text("Select user to chat with"),
            content=ft.Container(
                content=user_list,
                width=400,
                height=300
            ),
            actions=[
                ft.TextButton("Cancel", on_click=self._close)
            ]
        )
        
        self.page.dialog = self.dialog
        self.dialog.open = True
        self.page.update()
    
    def _handle_select(self, user: User):
        """Handle user selection"""
        self.close()
        if self.on_select:
            self.on_select(user)
    
    def _close(self, e):
        """Close dialog"""
        self.close()
    
    def close(self):
        """Close dialog"""
        if self.dialog:
            self.dialog.open = False
            self.page.update()


class GroupChatDialog:
    """Group chat creation dialog"""
    
    def __init__(
        self,
        users: List[User],
        page: ft.Page,
        on_create: Optional[Callable] = None
    ):
        """
        Initialize group chat dialog
        
        Args:
            users: List of users to choose from
            page: Flet page
            on_create: Callback when created (group_name, selected_users)
        """
        self.users = users
        self.page = page
        self.on_create = on_create
        self.dialog = None
        self.selected_members = []
        
        # Group name input
        self.group_name_input = ft.TextField(
            label="Group Name *",
            hint_text="Enter group name",
            width=380
        )
        
        # Member count text
        self.member_count_text = ft.Text(
            "Selected: 0 member(s)",
            size=12,
            color=config.TEXT_SECONDARY
        )
    
    def show(self):
        """Show group creation dialog"""
        # Create checkboxes for each user
        def create_user_checkbox(user):
            checkbox = ft.Checkbox(
                label=f"{user.display_name} (@{user.username})",
                value=False,
                on_change=lambda e: self._handle_member_toggle(user, e.control.value)
            )
            return checkbox
        
        user_checkboxes = ft.Column(
            controls=[create_user_checkbox(u) for u in self.users],
            scroll=ft.ScrollMode.AUTO,
            height=250
        )
        
        self.dialog = ft.AlertDialog(
            title=ft.Text("Create Group Chat"),
            content=ft.Container(
                content=ft.Column([
                    self.group_name_input,
                    ft.Divider(),
                    ft.Text("Select members:", size=14, weight=ft.FontWeight.BOLD),
                    self.member_count_text,
                    user_checkboxes
                ], spacing=10),
                width=400,
                height=400
            ),
            actions=[
                ft.TextButton("Cancel", on_click=self._close),
                ft.ElevatedButton(
                    "Create Group",
                    on_click=self._handle_create,
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
    
    def _handle_member_toggle(self, user: User, is_selected: bool):
        """Handle member checkbox toggle"""
        if is_selected:
            if user not in self.selected_members:
                self.selected_members.append(user)
        else:
            if user in self.selected_members:
                self.selected_members.remove(user)
        
        # Update member count text
        self.member_count_text.value = f"Selected: {len(self.selected_members)} member(s)"
        self.page.update()
    
    def _handle_create(self, e):
        """Handle create button click"""
        group_name = self.group_name_input.value
        
        # Validate
        if not group_name or not group_name.strip():
            self._show_error("Please enter a group name")
            return
        
        if not self.selected_members or len(self.selected_members) == 0:
            self._show_error("Please select at least one member")
            return
        
        self.close()
        
        if self.on_create:
            self.on_create(group_name.strip(), self.selected_members)
    
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


class GroupInfoDialog:
    """Group information dialog"""
    
    def __init__(
        self,
        conversation: Conversation,
        page: ft.Page
    ):
        """
        Initialize group info dialog
        
        Args:
            conversation: Group conversation
            page: Flet page
        """
        self.conversation = conversation
        self.page = page
        self.dialog = None
    
    def show(self):
        """Show group info dialog"""
        # Group info
        info_content = ft.Column([
            ft.Row([
                ft.Icon(ft.icons.GROUP, size=40, color=config.PRIMARY_COLOR),
                ft.Column([
                    ft.Text(
                        self.conversation.title or "Unnamed Group",
                        size=18,
                        weight=ft.FontWeight.BOLD
                    ),
                    ft.Text(
                        f"Created by: {self.conversation.created_by}",
                        size=12,
                        color=config.TEXT_SECONDARY
                    )
                ], expand=True)
            ], spacing=10),
            ft.Divider(),
            ft.Text(
                f"Group ID: {self.conversation.id}",
                size=10,
                color=config.TEXT_SECONDARY
            ),
            ft.Text(
                f"Created: {format_timestamp(self.conversation.created_at)}",
                size=12
            ),
        ], spacing=10)
        
        self.dialog = ft.AlertDialog(
            title=ft.Text("Group Information"),
            content=ft.Container(
                content=info_content,
                width=400
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

