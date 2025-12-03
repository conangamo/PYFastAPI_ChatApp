"""
Group Chat Creation Dialog
Allow selecting multiple friends and creating a group
"""
import flet as ft
from typing import Optional, Callable, List
from ..api.client import APIClient
from ..models import User
from ..config import config


class GroupCreationDialog:
    """Dialog for creating group chats with friend selection"""
    
    def __init__(
        self,
        page: ft.Page,
        api_client: APIClient,
        current_user: User,
        on_group_created: Optional[Callable] = None
    ):
        """
        Initialize group creation dialog
        
        Args:
            page: Flet page
            api_client: API client instance
            current_user: Current logged-in user
            on_group_created: Callback when group is created
        """
        self.page = page
        self.api_client = api_client
        self.current_user = current_user
        self.on_group_created = on_group_created
        
        # State
        self.friends: List[dict] = []
        self.selected_friends: set = set()  # Set of selected user_ids
        self.search_query: str = ""
        
        # UI Components
        self.group_name_input = ft.TextField(
            label="Group Name",
            hint_text="Enter group name...",
            border_color=config.PRIMARY_COLOR,
            focused_border_color=config.PRIMARY_COLOR,
            autofocus=True
        )
        
        self.search_input = ft.TextField(
            label="Search Friends",
            hint_text="Search by name...",
            prefix_icon=ft.icons.SEARCH,
            border_color=config.BORDER_COLOR,
            on_change=self._handle_search
        )
        
        self.friends_list = ft.Column(
            spacing=5,
            scroll=ft.ScrollMode.AUTO,
            height=300
        )
        
        self.selected_count_text = ft.Text(
            "Selected: 0 friends",
            size=14,
            color=config.TEXT_SECONDARY
        )
        
        self.loading_indicator = ft.ProgressRing(visible=False)
        
        self.dialog = ft.AlertDialog(
            title=ft.Text("Create Group Chat", size=20, weight=ft.FontWeight.BOLD),
            content=ft.Container(
                content=ft.Column([
                    self.group_name_input,
                    ft.Divider(height=10, color=config.DIVIDER_COLOR),
                    self.search_input,
                    self.selected_count_text,
                    ft.Container(
                        content=self.friends_list,
                        border=ft.border.all(1, config.BORDER_COLOR),
                        border_radius=8,
                        padding=10
                    ),
                    ft.Row([
                        self.loading_indicator,
                        ft.Text("Loading friends...", visible=False)
                    ], alignment=ft.MainAxisAlignment.CENTER)
                ], spacing=15),
                width=500
            ),
            actions=[
                ft.TextButton("Cancel", on_click=self._handle_close),
                ft.ElevatedButton(
                    "Create Group",
                    icon=ft.icons.GROUP_ADD,
                    bgcolor=config.SUCCESS_COLOR,
                    color=ft.colors.WHITE,
                    on_click=lambda e: self.page.run_task(self._handle_create)
                )
            ],
            actions_alignment=ft.MainAxisAlignment.END
        )
    
    def show(self):
        """Show the dialog"""
        self.page.dialog = self.dialog
        self.dialog.open = True
        self.page.update()
        
        # Load friends
        self.page.run_task(self._load_friends)
    
    async def _load_friends(self):
        """Load friends list from API"""
        try:
            self.loading_indicator.visible = True
            self.page.update()
            
            response = await self.api_client.get("/friendships/friends")
            
            if response.status_code == 200:
                self.friends = response.json()
                self._render_friends()
            else:
                self._show_error(f"Failed to load friends: {response.status_code}")
        
        except Exception as e:
            print(f"Error loading friends: {e}")
            self._show_error(str(e))
        
        finally:
            self.loading_indicator.visible = False
            self.page.update()
    
    def _handle_search(self, e):
        """Handle search input change"""
        self.search_query = e.control.value.lower()
        self._render_friends()
    
    def _render_friends(self):
        """Render friends list with checkboxes"""
        self.friends_list.controls.clear()
        
        # Filter friends by search query
        filtered_friends = [
            f for f in self.friends
            if not self.search_query or 
            self.search_query in f.get("username", "").lower() or
            self.search_query in f.get("display_name", "").lower()
        ]
        
        if not filtered_friends:
            self.friends_list.controls.append(
                ft.Container(
                    content=ft.Text(
                        "No friends found" if self.search_query else "No friends yet\nAdd friends first",
                        text_align=ft.TextAlign.CENTER,
                        color=config.TEXT_SECONDARY,
                        size=14
                    ),
                    padding=20,
                    alignment=ft.alignment.center
                )
            )
        else:
            for friend in filtered_friends:
                self.friends_list.controls.append(
                    self._build_friend_checkbox(friend)
                )
        
        self.page.update()
    
    def _build_friend_checkbox(self, friend: dict) -> ft.Container:
        """Build checkbox for a friend"""
        user_id = friend.get("user_id")
        username = friend.get("username", "Unknown")
        display_name = friend.get("display_name", username)
        is_active = friend.get("is_active", False)
        is_selected = user_id in self.selected_friends
        
        checkbox = ft.Checkbox(
            value=is_selected,
            on_change=lambda e, uid=user_id: self._handle_checkbox_change(uid, e.control.value)
        )
        
        return ft.Container(
            content=ft.Row([
                checkbox,
                # Avatar
                ft.CircleAvatar(
                    content=ft.Text(display_name[0].upper(), size=14),
                    bgcolor=config.PRIMARY_COLOR,
                    color=ft.colors.WHITE,
                    radius=18
                ),
                # Name and status
                ft.Column([
                    ft.Text(display_name, size=14, weight=ft.FontWeight.BOLD),
                    ft.Row([
                        ft.Icon(
                            ft.icons.CIRCLE,
                            size=8,
                            color=ft.colors.GREEN if is_active else ft.colors.GREY
                        ),
                        ft.Text(f"@{username}", size=12, color=config.TEXT_SECONDARY)
                    ], spacing=5)
                ], spacing=2, expand=True),
            ], spacing=10, alignment=ft.MainAxisAlignment.START),
            bgcolor=ft.colors.BLUE_50 if is_selected else ft.colors.WHITE,
            border_radius=8,
            padding=10,
            border=ft.border.all(2, config.PRIMARY_COLOR if is_selected else config.BORDER_COLOR),
            ink=True,
            on_click=lambda e, uid=user_id: self._toggle_selection(uid)
        )
    
    def _handle_checkbox_change(self, user_id: str, is_checked: bool):
        """Handle checkbox change"""
        if is_checked:
            self.selected_friends.add(user_id)
        else:
            self.selected_friends.discard(user_id)
        
        self._update_selected_count()
        self._render_friends()
    
    def _toggle_selection(self, user_id: str):
        """Toggle friend selection"""
        if user_id in self.selected_friends:
            self.selected_friends.discard(user_id)
        else:
            self.selected_friends.add(user_id)
        
        self._update_selected_count()
        self._render_friends()
    
    def _update_selected_count(self):
        """Update selected count text"""
        count = len(self.selected_friends)
        self.selected_count_text.value = f"Selected: {count} friend{'s' if count != 1 else ''}"
        self.page.update()
    
    async def _handle_create(self):
        """Handle create group button"""
        try:
            # Validate
            group_name = self.group_name_input.value
            if not group_name or not group_name.strip():
                self._show_error("Please enter a group name")
                return
            
            if len(self.selected_friends) == 0:
                self._show_error("Please select at least one friend")
                return
            
            # Create group
            print(f"Creating group: {group_name} with {len(self.selected_friends)} members")
            
            response = await self.api_client.post(
                "/conversations/",
                json={
                    "type": "group",
                    "title": group_name.strip(),
                    "participant_ids": list(self.selected_friends)
                }
            )
            
            if response.status_code in [200, 201]:
                self.page.snack_bar = ft.SnackBar(
                    content=ft.Text(f"Group '{group_name}' created! ✅"),
                    bgcolor=ft.colors.GREEN
                )
                self.page.snack_bar.open = True
                
                # Close dialog
                self.close()
                
                # Notify parent
                if self.on_group_created:
                    self.on_group_created()
            else:
                error_text = response.text
                self._show_error(f"Failed to create group: {error_text}")
        
        except Exception as e:
            print(f"Error creating group: {e}")
            self._show_error(str(e))
    
    def _show_error(self, message: str):
        """Show error message"""
        self.page.snack_bar = ft.SnackBar(
            content=ft.Text(message),
            bgcolor=config.ERROR_COLOR
        )
        self.page.snack_bar.open = True
        self.page.update()
    
    def _handle_close(self, e):
        """Handle close button"""
        self.close()
    
    def close(self):
        """Close the dialog"""
        self.dialog.open = False
        self.page.update()

