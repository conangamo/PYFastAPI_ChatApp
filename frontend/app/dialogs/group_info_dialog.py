import flet as ft
from typing import List, Callable, Awaitable

from ..models import Conversation, ConversationParticipant, User


class GroupInfoDialog:

    def __init__(
        self,
        conversation: Conversation,
        current_user: User,
        on_add_members: Callable[[List[str]], Awaitable[None]],
        on_remove_member: Callable[[str], Awaitable[None]],
    ):
        self.conversation = conversation
        self.current_user = current_user
        self.on_add_members = on_add_members
        self.on_remove_member = on_remove_member

        # Flet controls
        self.dialog: ft.AlertDialog | None = None
        self._members_column: ft.Column | None = None


    def open(self, page: ft.Page):
        self._build_dialog()
        page.dialog = self.dialog
        self.dialog.open = True
        page.update()


    def _build_dialog(self):
        # Danh sách thành viên
        members_controls: List[ft.Control] = []
        for p in self.conversation.participants:
            members_controls.append(self._build_member_row(p))

        self._members_column = ft.Column(
            controls=members_controls,
            tight=True,
            spacing=4,
            scroll=ft.ScrollMode.AUTO,
            height=300,
        )

        self.dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text(f"Thông tin nhóm: {self.conversation.name or ''}"),
            content=ft.Column(
                controls=[
                    ft.Text(
                        f"Số thành viên: {len(self.conversation.participants)}",
                        weight=ft.FontWeight.BOLD,
                    ),
                    ft.Divider(),
                    self._members_column,
                ],
                tight=True,
                spacing=10,
            ),
            actions=[
                ft.TextButton(
                    "Thêm thành viên",
                    on_click=self._handle_add_members_click,
                ),
                ft.TextButton(
                    "Đóng",
                    on_click=lambda e: self._close(e.page),
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )

    def _build_member_row(self, participant: ConversationParticipant) -> ft.Control:
        # Hiển thị username + role
        subtitle = []
        if participant.user_id == self.current_user.id:
            subtitle.append("Bạn")
        if getattr(participant, "is_admin", False):
            subtitle.append("Quản trị viên")

        subtitle_text = " • ".join(subtitle) if subtitle else ""

        # Nút xoá thành viên (ẩn với chính mình để tránh xoá nhầm)
        remove_button: ft.Control | None = None
        if participant.user_id != self.current_user.id:
            remove_button = ft.IconButton(
                icon=ft.icons.REMOVE_CIRCLE_OUTLINE,
                icon_color=ft.colors.RED,
                tooltip="Xoá khỏi nhóm",
                on_click=lambda e, uid=participant.user_id: self._handle_remove_member(
                    e, uid
                ),
            )

        row = ft.Row(
            controls=[
                ft.CircleAvatar(
                    content=ft.Text(
                        (participant.username or "?")[:1].upper(),
                    ),
                ),
                ft.Column(
                    controls=[
                        ft.Text(participant.username or "Unknown user"),
                        ft.Text(
                            subtitle_text,
                            size=12,
                            color=ft.colors.GREY,
                        ),
                    ],
                    tight=True,
                    spacing=2,
                ),
                ft.Container(expand=True),
                remove_button or ft.Container(),
            ],
            alignment=ft.MainAxisAlignment.START,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

        return row

    # ---------- Handlers ----------

    def _close(self, page: ft.Page | None):
        if not page or not self.dialog:
            return
        self.dialog.open = False
        page.update()

    def _handle_add_members_click(self, e: ft.ControlEvent):
        page = e.page
        if page and self.dialog:
            self.dialog.open = False
            page.update()

        if self.on_add_members:
            page.run_task(self.on_add_members, [])

    def _handle_remove_member(self, e: ft.ControlEvent, user_id: str):
        page = e.page
        if self.on_remove_member and page:
            page.run_task(self.on_remove_member, user_id)


