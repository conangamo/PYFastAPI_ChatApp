"""
Add Member Dialog
Dialog to add friends to an existing group
"""
import flet as ft
from typing import Callable, List, Optional
from ..api.client import get_api_client
from ..config import config


class AddMemberDialog:
    """Dialog to add members to group"""
    
    def __init__(
        self,
        page: ft.Page,
        conversation_id: str,
        existing_participant_ids: List[str],
        on_add: Callable[[str], None]
    ):
        """
        Initialize add member dialog
        
        Args:
            page: Flet page
            conversation_id: Conversation ID
            existing_participant_ids: List of user IDs already in group
            on_add: Callback when member is added
        """
        self.page = page
        self.conversation_id = conversation_id
        self.existing_participant_ids = existing_participant_ids
        self.on_add = on_add
        self.friends: List[dict] = []
        
        self.friends_list = ft.ListView(
            spacing=5,
            height=300,
            width=400
        )
        
        self.loading_indicator = ft.ProgressRing(visible=False)
        self.error_text = ft.Text("", color=config.ERROR_COLOR, visible=False)
        
        self.dialog = ft.AlertDialog(
            title=ft.Text("Thêm thành viên", size=18, weight=ft.FontWeight.BOLD),
            content=ft.Container(
                content=ft.Column(
                    controls=[
                        ft.Row([
                            self.loading_indicator,
                            ft.Text("Đang tải danh sách bạn bè...", visible=False)
                        ], alignment=ft.MainAxisAlignment.CENTER),
                        self.error_text,
                        ft.Container(
                            content=self.friends_list,
                            border=ft.border.all(1, config.BORDER_COLOR),
                            border_radius=8,
                            padding=10
                        )
                    ],
                    spacing=10
                ),
                padding=10,
                width=450
            ),
            actions=[
                ft.TextButton("Đóng", on_click=self._handle_close)
            ]
        )
    
    async def load_friends(self):
        """Load friends list (excluding existing participants)"""
        try:
            self.loading_indicator.visible = True
            self.error_text.visible = False
            self.page.update()
            
            api = get_api_client()
            all_friends = await api.get_friends()
            
            # Filter: Only show friends who are not already in group
            self.friends = [
                f for f in all_friends
                if str(f["user_id"]) not in [str(pid) for pid in self.existing_participant_ids]
            ]
            
            # Render friends list
            self.friends_list.controls.clear()
            
            if not self.friends:
                self.friends_list.controls.append(
                    ft.Container(
                        content=ft.Text(
                            "Không có bạn bè nào để thêm",
                            color=config.TEXT_SECONDARY,
                            text_align=ft.TextAlign.CENTER
                        ),
                        padding=20,
                        alignment=ft.alignment.center
                    )
                )
            else:
                for friend in self.friends:
                    item = ft.Container(
                        content=ft.Row(
                            controls=[
                                ft.Icon(ft.icons.PERSON, size=24, color=config.PRIMARY_COLOR),
                                ft.Column(
                                    controls=[
                                        ft.Text(
                                            friend.get("display_name", friend.get("username", "Unknown")),
                                            weight=ft.FontWeight.BOLD,
                                            size=14
                                        ),
                                        ft.Text(
                                            f"@{friend.get('username', '')}",
                                            size=12,
                                            color=config.TEXT_SECONDARY
                                        )
                                    ],
                                    spacing=2,
                                    expand=True
                                ),
                                ft.ElevatedButton(
                                    "Thêm",
                                    icon=ft.icons.ADD,
                                    on_click=lambda e, f=friend: self.page.run_task(self._add_friend, f["user_id"])
                                )
                            ],
                            spacing=10,
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN
                        ),
                        padding=10,
                        border_radius=8,
                        bgcolor=ft.colors.WHITE,
                        border=ft.border.all(1, config.BORDER_COLOR)
                    )
                    self.friends_list.controls.append(item)
            
            self.loading_indicator.visible = False
            self.page.update()
            
        except Exception as e:
            print(f"❌ Error loading friends: {e}")
            self.loading_indicator.visible = False
            self.error_text.value = f"Lỗi: {str(e)}"
            self.error_text.visible = True
            self.page.update()
    
    async def _add_friend(self, user_id: str):
        """Add friend to group (single)"""
        try:
            api = get_api_client()
            await api.add_participant_to_group(self.conversation_id, user_id)
            
            self.on_add(user_id)
            # Don't close dialog - allow adding more
            self.page.update()
            
            # Show success message
            self.page.snack_bar = ft.SnackBar(
                content=ft.Text("Đã thêm thành viên thành công"),
                bgcolor=config.SUCCESS_COLOR
            )
            self.page.snack_bar.open = True
            self.page.update()
            
            # Reload friends list to remove added user
            await self.load_friends()
            
        except Exception as e:
            print(f"❌ Error adding member: {e}")
            self.page.snack_bar = ft.SnackBar(
                content=ft.Text(f"Lỗi: {str(e)}"),
                bgcolor=config.ERROR_COLOR
            )
            self.page.snack_bar.open = True
            self.page.update()
    
    def _handle_close(self, e):
        """Close dialog"""
        self.page.close_dialog()
        self.page.update()
    
    def open(self):
        """Open the dialog"""
        self.page.dialog = self.dialog
        self.dialog.open = True
        self.page.update()
        # Load friends when dialog opens
        self.page.run_task(self.load_friends)

