"""
Friend Requests Dialog
Shows pending friend requests with accept/reject options
"""
import flet as ft
from typing import Optional, Callable, List
from datetime import datetime

from ..api.client import APIClient
from ..models import User
from ..config import config


class FriendRequestsDialog:
    """Dialog for managing friend requests"""
    
    def __init__(
        self,
        page: ft.Page,
        api_client: APIClient,
        current_user: User,
        on_request_handled: Optional[Callable] = None
    ):
        """
        Initialize friend requests dialog
        
        Args:
            page: Flet page
            api_client: API client instance
            current_user: Current logged-in user
            on_request_handled: Callback when a request is accepted/rejected
        """
        self.page = page
        self.api_client = api_client
        self.current_user = current_user
        self.on_request_handled = on_request_handled
        
        # State
        self.pending_requests: List[dict] = []
        
        # UI Components
        self.requests_list = ft.Column(
            spacing=10,
            scroll=ft.ScrollMode.AUTO,
            expand=True
        )
        
        self.loading_indicator = ft.ProgressRing()
        
        self.dialog = ft.AlertDialog(
            title=ft.Text("Friend Requests", size=20, weight=ft.FontWeight.BOLD),
            content=ft.Container(
                content=ft.Column([
                    self.loading_indicator,
                    self.requests_list
                ], spacing=15, expand=True),
                width=500,
                height=400
            ),
            actions=[
                ft.TextButton("Close", on_click=self._handle_close)
            ],
            actions_alignment=ft.MainAxisAlignment.END
        )
    
    def show(self):
        """Show the dialog"""
        self.page.dialog = self.dialog
        self.dialog.open = True
        self.page.update()
        
        # Load requests
        self.page.run_task(self._load_requests)
    
    async def _load_requests(self):
        """Load pending friend requests"""
        try:
            self.loading_indicator.visible = True
            self.requests_list.visible = False
            self.page.update()
            
            # Get pending friend requests from API (received)
            response = await self.api_client.get("/friendships/requests/received")
            
            if response.status_code == 200:
                data = response.json()
                # All received requests are for current user, just filter by status
                self.pending_requests = [
                    req for req in data 
                    if req.get("status") == "pending"
                ]
                
                self._render_requests()
            else:
                self._show_error(f"Failed to load requests: {response.status_code}")
        
        except Exception as e:
            print(f"Error loading friend requests: {e}")
            self._show_error(str(e))
        
        finally:
            self.loading_indicator.visible = False
            self.requests_list.visible = True
            self.page.update()
    
    def _render_requests(self):
        """Render friend requests list"""
        self.requests_list.controls.clear()
        
        if not self.pending_requests:
            self.requests_list.controls.append(
                ft.Container(
                    content=ft.Column([
                        ft.Icon(ft.icons.INBOX, size=64, color=config.TEXT_SECONDARY),
                        ft.Text(
                            "No pending requests",
                            size=16,
                            color=config.TEXT_SECONDARY,
                            text_align=ft.TextAlign.CENTER
                        ),
                        ft.Text(
                            "When someone sends you a friend request, it will appear here.",
                            size=12,
                            color=config.TEXT_SECONDARY,
                            text_align=ft.TextAlign.CENTER
                        )
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10),
                    padding=40,
                    alignment=ft.alignment.center
                )
            )
        else:
            for request in self.pending_requests:
                self.requests_list.controls.append(
                    self._build_request_card(request)
                )
        
        self.page.update()
    
    def _build_request_card(self, request: dict) -> ft.Container:
        """Build a card for a single friend request"""
        user_id = request.get("user_id")
        username = request.get("username", "Unknown")
        display_name = request.get("display_name", username)
        email = request.get("email", "")
        created_at = request.get("created_at")
        friendship_id = request.get("friendship_id")
        
        # Format timestamp
        time_text = "Just now"
        if created_at:
            try:
                dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                now = datetime.now(dt.tzinfo)
                diff = now - dt
                
                if diff.days > 0:
                    time_text = f"{diff.days}d ago"
                elif diff.seconds >= 3600:
                    time_text = f"{diff.seconds // 3600}h ago"
                elif diff.seconds >= 60:
                    time_text = f"{diff.seconds // 60}m ago"
                else:
                    time_text = "Just now"
            except:
                pass
        
        return ft.Container(
            content=ft.Row([
                # Avatar
                ft.Container(
                    content=ft.CircleAvatar(
                        content=ft.Text(display_name[0].upper(), size=20),
                        bgcolor=config.PRIMARY_COLOR,
                        color=ft.colors.WHITE,
                        radius=25
                    ),
                    padding=5
                ),
                
                # User info
                ft.Column([
                    ft.Text(display_name, size=16, weight=ft.FontWeight.BOLD),
                    ft.Text(f"@{username}", size=12, color=config.TEXT_SECONDARY),
                    ft.Text(time_text, size=11, color=config.TEXT_SECONDARY, italic=True)
                ], spacing=2, expand=True),
                
                # Actions
                ft.Row([
                    ft.ElevatedButton(
                        "Accept",
                        icon=ft.icons.CHECK,
                        bgcolor=ft.colors.GREEN,
                        color=ft.colors.WHITE,
                        on_click=lambda e, fid=friendship_id, uid=user_id: 
                            self.page.run_task(self._handle_accept, fid, uid)
                    ),
                    ft.OutlinedButton(
                        "Reject",
                        icon=ft.icons.CLOSE,
                        on_click=lambda e, fid=friendship_id: 
                            self.page.run_task(self._handle_reject, fid)
                    )
                ], spacing=10)
            ], alignment=ft.MainAxisAlignment.START, spacing=10),
            bgcolor=ft.colors.SURFACE_VARIANT,
            border_radius=10,
            padding=15,
            border=ft.border.all(1, config.BORDER_COLOR)
        )
    
    async def _handle_accept(self, friendship_id: str, user_id: str):
        """Handle accepting a friend request"""
        try:
            print(f"Accepting friend request: {friendship_id}")
            
            # Call API to accept request
            response = await self.api_client.post(
                "/friendships/respond",
                json={
                    "friendship_id": friendship_id,
                    "action": "accept"
                }
            )
            
            if response.status_code == 200:
                # Get friend info from the pending requests list
                friend_info = next((req for req in self.pending_requests if req.get("friendship_id") == friendship_id), None)
                
                if friend_info:
                    # Auto-create conversation with the friend
                    try:
                        conv_response = await self.api_client.post(
                            "/conversations/",
                            json={
                                "type": "direct",
                                "title": friend_info.get("display_name", friend_info.get("username")),
                                "participant_ids": [user_id]
                            }
                        )
                        
                        if conv_response.status_code in [200, 201]:
                            print(f"✅ Conversation created with {friend_info.get('username')}")
                        elif conv_response.status_code == 400:
                            # Conversation already exists, that's fine
                            print(f"⚠️ Conversation already exists with {friend_info.get('username')}")
                        else:
                            print(f"⚠️ Failed to create conversation: {conv_response.status_code}")
                    except Exception as conv_error:
                        print(f"⚠️ Error creating conversation: {conv_error}")
                
                self.page.snack_bar = ft.SnackBar(
                    content=ft.Text("Friend request accepted! ✅ Chat created!"),
                    bgcolor=ft.colors.GREEN
                )
                self.page.snack_bar.open = True
                
                # Reload requests
                await self._load_requests()
                
                # Notify parent to reload conversations
                if self.on_request_handled:
                    self.on_request_handled()
            else:
                self._show_error(f"Failed to accept request: {response.status_code}")
        
        except Exception as e:
            print(f"Error accepting friend request: {e}")
            self._show_error(str(e))
    
    async def _handle_reject(self, friendship_id: str):
        """Handle rejecting a friend request"""
        try:
            print(f"Rejecting friend request: {friendship_id}")
            
            # Call API to reject request
            response = await self.api_client.post(
                "/friendships/respond",
                json={
                    "friendship_id": friendship_id,
                    "action": "reject"
                }
            )
            
            if response.status_code == 200:
                self.page.snack_bar = ft.SnackBar(
                    content=ft.Text("Friend request rejected"),
                    bgcolor=ft.colors.ORANGE
                )
                self.page.snack_bar.open = True
                
                # Reload requests
                await self._load_requests()
                
                # Notify parent
                if self.on_request_handled:
                    self.on_request_handled()
            else:
                self._show_error(f"Failed to reject request: {response.status_code}")
        
        except Exception as e:
            print(f"Error rejecting friend request: {e}")
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
        self.dialog.open = False
        self.page.update()
    
    def close(self):
        """Close the dialog"""
        self.dialog.open = False
        self.page.update()

