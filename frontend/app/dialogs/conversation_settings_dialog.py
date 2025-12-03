"""
Conversation Settings Dialog
Settings for each conversation (1-1 or group)
"""
import flet as ft
from typing import Callable, Optional
from ..models import Conversation
from ..api.client import get_api_client
from ..config import config


class ConversationSettingsDialog:
    """Settings dialog for conversation"""
    
    def __init__(
        self,
        page: ft.Page,
        conversation: Conversation,
        current_user_id: str,
        on_action: Callable[[str], None]  # Callback: "unfriend", "delete", "leave", "add_member"
    ):
        """
        Initialize conversation settings dialog
        
        Args:
            page: Flet page
            conversation: Conversation object
            current_user_id: Current user ID
            on_action: Callback when action is performed
        """
        self.page = page
        self.conversation = conversation
        self.current_user_id = current_user_id
        self.on_action = on_action
        
        # Build UI based on conversation type
        if conversation.type.value == "direct":
            self._build_direct_chat_ui()
        else:
            self._build_group_chat_ui()
    
    def _build_direct_chat_ui(self):
        """Build UI for direct chat (1-1)"""
        # Get other user info
        other_user = None
        for p in self.conversation.participants:
            if p.user_id != self.current_user_id:
                other_user = p
                break
        
        other_user_name = other_user.display_name if other_user else "Unknown"
        
        self.dialog = ft.AlertDialog(
            title=ft.Text("Cài đặt cuộc trò chuyện", size=18, weight=ft.FontWeight.BOLD),
            content=ft.Container(
                content=ft.Column(
                    controls=[
                        ft.Text(f"Chat với: {other_user_name}", size=16, weight=ft.FontWeight.BOLD),
                        ft.Divider(height=10),
                        
                        # Unfriend button
                        ft.ElevatedButton(
                            "Xóa bạn",
                            icon=ft.icons.PERSON_REMOVE,
                            color=ft.colors.ORANGE,
                            bgcolor=ft.colors.ORANGE_50,
                            on_click=lambda e: self.page.run_task(self._handle_unfriend)
                        ),
                        
                        # Delete conversation button
                        ft.ElevatedButton(
                            "Xóa cuộc trò chuyện",
                            icon=ft.icons.DELETE,
                            color=ft.colors.RED,
                            bgcolor=ft.colors.RED_50,
                            on_click=lambda e: self.page.run_task(self._handle_delete)
                        )
                    ],
                    spacing=15,
                    scroll=ft.ScrollMode.AUTO
                ),
                width=350,
                height=250,
                padding=20
            ),
            actions=[
                ft.TextButton("Đóng", on_click=self._handle_close)
            ]
        )
    
    def _build_group_chat_ui(self):
        """Build UI for group chat"""
        is_creator = self.conversation.created_by == self.current_user_id
        
        controls = [
            ft.Text(f"Nhóm: {self.conversation.title}", size=16, weight=ft.FontWeight.BOLD),
            ft.Divider(height=10),
        ]
        
        # Add member button (only for creator)
        if is_creator:
            controls.append(
                ft.ElevatedButton(
                    "Thêm thành viên",
                    icon=ft.icons.PERSON_ADD,
                    color=ft.colors.BLUE,
                    bgcolor=ft.colors.BLUE_50,
                    on_click=lambda e: self._handle_add_member()
                )
            )
        
        # Leave group button
        controls.append(
            ft.ElevatedButton(
                "Rời nhóm",
                icon=ft.icons.EXIT_TO_APP,
                color=ft.colors.RED,
                bgcolor=ft.colors.RED_50,
                on_click=lambda e: self.page.run_task(self._handle_leave)
            )
        )
        
        self.dialog = ft.AlertDialog(
            title=ft.Text("Cài đặt nhóm", size=18, weight=ft.FontWeight.BOLD),
            content=ft.Container(
                content=ft.Column(
                    controls=controls,
                    spacing=15,
                    scroll=ft.ScrollMode.AUTO
                ),
                width=350,
                height=250,
                padding=20
            ),
            actions=[
                ft.TextButton("Đóng", on_click=self._handle_close)
            ]
        )
    
    async def _handle_unfriend(self):
        """Handle unfriend action"""
        try:
            api = get_api_client()
            await api.unfriend_in_conversation(self.conversation.id)
            
            self.on_action("unfriend")
            self._handle_close(None)
            
            # Show success message
            self.page.snack_bar = ft.SnackBar(
                content=ft.Text("Đã xóa bạn thành công"),
                bgcolor=config.SUCCESS_COLOR
            )
            self.page.snack_bar.open = True
            self.page.update()
            
        except Exception as e:
            print(f"❌ Error unfriending: {e}")
            self.page.snack_bar = ft.SnackBar(
                content=ft.Text(f"Lỗi: {str(e)}"),
                bgcolor=config.ERROR_COLOR
            )
            self.page.snack_bar.open = True
            self.page.update()
    
    async def _handle_delete(self):
        """Handle delete conversation"""
        # Confirm dialog
        def confirm_delete(e):
            self.page.close_dialog()
            self.page.run_task(self._confirm_delete)
        
        confirm_dialog = ft.AlertDialog(
            title=ft.Text("Xác nhận"),
            content=ft.Text("Bạn có chắc muốn xóa cuộc trò chuyện này? Bạn sẽ không thấy nó trong danh sách nữa."),
            actions=[
                ft.TextButton("Hủy", on_click=lambda e: self.page.close_dialog()),
                ft.ElevatedButton(
                    "Xóa",
                    color=ft.colors.RED,
                    on_click=confirm_delete
                )
            ]
        )
        
        self.page.dialog = confirm_dialog
        confirm_dialog.open = True
        self.page.update()
    
    async def _confirm_delete(self):
        """Confirm and execute delete"""
        try:
            api = get_api_client()
            await api.leave_conversation(self.conversation.id)
            
            self.on_action("delete")
            self._handle_close(None)
            
            # Show success message
            self.page.snack_bar = ft.SnackBar(
                content=ft.Text("Đã xóa cuộc trò chuyện"),
                bgcolor=config.SUCCESS_COLOR
            )
            self.page.snack_bar.open = True
            self.page.update()
            
        except Exception as e:
            print(f"❌ Error deleting conversation: {e}")
            self.page.snack_bar = ft.SnackBar(
                content=ft.Text(f"Lỗi: {str(e)}"),
                bgcolor=config.ERROR_COLOR
            )
            self.page.snack_bar.open = True
            self.page.update()
    
    async def _handle_leave(self):
        """Handle leave group"""
        # Confirm dialog
        def confirm_leave(e):
            self.page.close_dialog()
            self.page.run_task(self._confirm_leave)
        
        confirm_dialog = ft.AlertDialog(
            title=ft.Text("Xác nhận"),
            content=ft.Text("Bạn có chắc muốn rời nhóm này? Bạn sẽ không thấy tin nhắn trong nhóm nữa."),
            actions=[
                ft.TextButton("Hủy", on_click=lambda e: self.page.close_dialog()),
                ft.ElevatedButton(
                    "Rời nhóm",
                    color=ft.colors.RED,
                    on_click=confirm_leave
                )
            ]
        )
        
        self.page.dialog = confirm_dialog
        confirm_dialog.open = True
        self.page.update()
    
    async def _confirm_leave(self):
        """Confirm and execute leave"""
        try:
            api = get_api_client()
            await api.leave_conversation(self.conversation.id)
            
            self.on_action("leave")
            self._handle_close(None)
            
            # Show success message
            self.page.snack_bar = ft.SnackBar(
                content=ft.Text("Đã rời nhóm"),
                bgcolor=config.SUCCESS_COLOR
            )
            self.page.snack_bar.open = True
            self.page.update()
            
        except Exception as e:
            print(f"❌ Error leaving group: {e}")
            self.page.snack_bar = ft.SnackBar(
                content=ft.Text(f"Lỗi: {str(e)}"),
                bgcolor=config.ERROR_COLOR
            )
            self.page.snack_bar.open = True
            self.page.update()
    
    def _handle_add_member(self):
        """Handle add member to group"""
        # Close settings dialog first
        self.page.close_dialog()
        self.page.update()
        
        # Call callback to open add member dialog
        self.on_action("add_member")
    
    def _handle_close(self, e):
        """Close dialog"""
        self.page.close_dialog()
        self.page.update()
    
    def open(self):
        """Open the dialog"""
        self.page.dialog = self.dialog
        self.dialog.open = True
        self.page.update()

