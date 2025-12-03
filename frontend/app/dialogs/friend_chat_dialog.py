"""
Friend Chat Dialog - Search users, send friend requests, start chat
"""
import flet as ft
from typing import Optional, Callable, List, Dict, Any
import httpx
from datetime import datetime

from ..models import User
from ..config import config
from ..api.client import APIClient


class FriendChatDialog:
    """Dialog for searching users, sending friend requests, and starting chats"""
    
    def __init__(
        self,
        page: ft.Page,
        api_client: APIClient,
        current_user: User,
        on_chat_created: Optional[Callable] = None
    ):
        """
        Initialize friend chat dialog
        
        Args:
            page: Flet page
            api_client: API client instance
            current_user: Current logged-in user
            on_chat_created: Callback when chat is created/friend is accepted
        """
        self.page = page
        self.api_client = api_client
        self.current_user = current_user
        self.on_chat_created = on_chat_created
        
        # UI components
        self.dialog = None
        self.search_field = None
        self.search_results = None
        self.loading_indicator = None
        self.empty_state = None
        
    def show(self):
        """Show friend chat dialog"""
        # Search field
        self.search_field = ft.TextField(
            label="Search users",
            hint_text="Enter username or name...",
            prefix_icon=ft.icons.SEARCH,
            on_submit=lambda e: self.page.run_task(self._handle_search, e),
            autofocus=True,
            width=500
        )
        
        # Search button
        search_btn = ft.ElevatedButton(
            "Search",
            icon=ft.icons.SEARCH,
            on_click=lambda e: self.page.run_task(self._handle_search, e),
            bgcolor=config.PRIMARY_COLOR,
            color="white"
        )
        
        # Loading indicator
        self.loading_indicator = ft.ProgressRing(visible=False)
        
        # Empty state
        self.empty_state = ft.Container(
            content=ft.Column([
                ft.Icon(ft.icons.SEARCH, size=64, color=ft.colors.GREY_400),
                ft.Text(
                    "Search for users to connect",
                    size=16,
                    color=ft.colors.GREY_600,
                    text_align=ft.TextAlign.CENTER
                ),
                ft.Text(
                    "Enter a username or name above",
                    size=12,
                    color=ft.colors.GREY_400,
                    text_align=ft.TextAlign.CENTER
                )
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10),
            padding=40,
            alignment=ft.alignment.center
        )
        
        # Search results container
        self.search_results = ft.Column(
            controls=[self.empty_state],
            scroll=ft.ScrollMode.AUTO,
            spacing=10,
            height=400
        )
        
        # Create dialog
        self.dialog = ft.AlertDialog(
            title=ft.Text("Find Friends & Start Chat", weight=ft.FontWeight.BOLD),
            content=ft.Container(
                content=ft.Column([
                    # Search section
                    ft.Row([
                        self.search_field,
                        search_btn
                    ], spacing=10),
                    ft.Divider(),
                    
                    # Loading indicator
                    ft.Container(
                        content=self.loading_indicator,
                        alignment=ft.alignment.center,
                        height=50
                    ),
                    
                    # Results section
                    self.search_results
                ], spacing=10),
                width=600,
                height=500
            ),
            actions=[
                ft.TextButton("Close", on_click=self._close)
            ]
        )
        
        self.page.dialog = self.dialog
        self.dialog.open = True
        self.page.update()
    
    async def _handle_search(self, e):
        """Handle search button click"""
        query = self.search_field.value
        print(f"[DEBUG] Searching for: {query}")
        
        if not query or len(query.strip()) < 2:
            self._show_error("Please enter at least 2 characters")
            return
        
        # Show loading
        self.loading_indicator.visible = True
        self.search_results.controls = []
        self.page.update()
        
        try:
            # Search users via API
            endpoint = f"/friendships/search/{query}"
            print(f"[DEBUG] Calling endpoint: {endpoint}")
            
            response = await self.api_client.get(endpoint)
            print(f"[DEBUG] Response status: {response.status_code}")
            
            if response.status_code == 200:
                users = response.json()
                print(f"[DEBUG] Found {len(users)} users")
                print(f"[DEBUG] Users data: {users}")
                self._display_results(users)
            else:
                error_msg = f"Search failed: {response.status_code}"
                print(f"[ERROR] {error_msg}")
                print(f"[ERROR] Response: {response.text}")
                self._show_error(error_msg)
                
        except Exception as e:
            error_msg = f"Error: {str(e)}"
            print(f"[ERROR] Exception: {error_msg}")
            import traceback
            traceback.print_exc()
            self._show_error(error_msg)
        finally:
            self.loading_indicator.visible = False
            self.page.update()
    
    def _display_results(self, users: List[Dict[str, Any]]):
        """Display search results"""
        self.search_results.controls.clear()
        
        if not users:
            # No results
            self.search_results.controls.append(
                ft.Container(
                    content=ft.Column([
                        ft.Icon(ft.icons.PERSON_OFF, size=48, color=ft.colors.GREY_400),
                        ft.Text(
                            "No users found",
                            size=14,
                            color=ft.colors.GREY_600,
                            text_align=ft.TextAlign.CENTER
                        ),
                        ft.Text(
                            "Try a different search term",
                            size=12,
                            color=ft.colors.GREY_400,
                            text_align=ft.TextAlign.CENTER
                        )
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10),
                    padding=40,
                    alignment=ft.alignment.center
                )
            )
        else:
            # Display user results
            for user in users:
                self.search_results.controls.append(
                    self._build_user_card(user)
                )
        
        self.page.update()
    
    def _build_user_card(self, user: Dict[str, Any]) -> ft.Container:
        """Build user card with friend request button"""
        username = user.get('username', 'Unknown')
        display_name = user.get('display_name', username)
        email = user.get('email', '')
        status = user.get('status')  # None, 'pending', 'accepted', etc.
        user_id = user.get('user_id')
        
        # Determine action button based on status
        if status == 'accepted':
            # Already friends - can start chat directly
            action_btn = ft.ElevatedButton(
                "Start Chat",
                icon=ft.icons.CHAT,
                bgcolor=config.PRIMARY_COLOR,
                color="white",
                on_click=lambda e, uid=user_id, uname=username: self.page.run_task(self._start_chat, uid, uname)
            )
            status_chip = ft.Chip(
                label=ft.Text("Friend", size=12),
                leading=ft.Icon(ft.icons.CHECK_CIRCLE, size=16, color=ft.colors.GREEN),
                bgcolor=ft.colors.GREEN_100
            )
        elif status == 'pending':
            # Friend request pending
            action_btn = ft.Text("Pending...", color=ft.colors.ORANGE, weight=ft.FontWeight.BOLD)
            status_chip = ft.Chip(
                label=ft.Text("Pending", size=12),
                leading=ft.Icon(ft.icons.SCHEDULE, size=16, color=ft.colors.ORANGE),
                bgcolor=ft.colors.ORANGE_100
            )
        else:
            # Not friends - show add friend button
            action_btn = ft.ElevatedButton(
                "Add Friend",
                icon=ft.icons.PERSON_ADD,
                bgcolor=config.SECONDARY_COLOR,
                color="white",
                on_click=lambda e, uid=user_id, uname=username: self.page.run_task(self._send_friend_request, uid, uname)
            )
            status_chip = None
        
        # Build card
        return ft.Container(
            content=ft.Row([
                # Avatar
                ft.Container(
                    content=ft.CircleAvatar(
                        content=ft.Text(
                            username[0].upper() if username else "?",
                            size=20,
                            weight=ft.FontWeight.BOLD,
                            color="white"
                        ),
                        bgcolor=config.PRIMARY_COLOR,
                        radius=25
                    ),
                    margin=ft.margin.only(right=15)
                ),
                
                # User info
                ft.Column([
                    ft.Row([
                        ft.Text(display_name, weight=ft.FontWeight.BOLD, size=16),
                        status_chip if status_chip else ft.Container()
                    ], spacing=10),
                    ft.Text(f"@{username}", size=12, color=ft.colors.GREY_600),
                    ft.Text(email, size=11, color=ft.colors.GREY_500)
                ], spacing=2, expand=True),
                
                # Action button
                action_btn
                
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            padding=15,
            border=ft.border.all(1, ft.colors.GREY_300),
            border_radius=10,
            bgcolor=ft.colors.WHITE
        )
    
    async def _send_friend_request(self, user_id: str, username: str):
        """Send friend request to user"""
        try:
            response = await self.api_client.post(
                "/friendships/send-request",
                json={"friend_id": user_id}
            )
            
            if response.status_code == 201:
                self._show_success(f"Friend request sent to @{username}!")
                # Refresh search results
                await self._handle_search(None)
            else:
                error_detail = response.json().get('detail', 'Unknown error')
                self._show_error(f"Failed to send request: {error_detail}")
                
        except Exception as e:
            self._show_error(f"Error: {str(e)}")
    
    async def _start_chat(self, user_id: str, username: str):
        """Start chat with friend (create conversation)"""
        try:
            # Create direct conversation
            response = await self.api_client.post(
                "/conversations/",
                json={
                    "type": "direct",
                    "title": username,
                    "participant_ids": [user_id]
                }
            )
            
            if response.status_code in [200, 201]:
                self._show_success(f"Chat with @{username} started!")
                self.close()
                
                # Callback to refresh conversation list
                if self.on_chat_created:
                    self.on_chat_created()
            else:
                error_detail = response.json().get('detail', 'Unknown error')
                self._show_error(f"Failed to create chat: {error_detail}")
                
        except Exception as e:
            self._show_error(f"Error: {str(e)}")
    
    def _show_success(self, message: str):
        """Show success snackbar"""
        self.page.snack_bar = ft.SnackBar(
            content=ft.Text(message),
            bgcolor=ft.colors.GREEN
        )
        self.page.snack_bar.open = True
        self.page.update()
    
    def _show_error(self, message: str):
        """Show error snackbar"""
        self.page.snack_bar = ft.SnackBar(
            content=ft.Text(message),
            bgcolor=ft.colors.RED
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

