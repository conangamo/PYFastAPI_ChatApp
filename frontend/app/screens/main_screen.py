import flet as ft
import uuid
import asyncio
from typing import Optional, List
from pathlib import Path

from ..models import User, Conversation, Message
from ..api.client import get_api_client
from ..websocket.client import WebSocketClient
from ..utils.formatters import format_timestamp, truncate_text
from ..config import config
from ..components import MessageBubble, ConversationItem, MessageInput, TypingIndicator
# Conditional import for video call page
try:
    from ..pages.video_call_page import VideoCallPage
    VIDEO_CALL_AVAILABLE = True
except ImportError:
    VIDEO_CALL_AVAILABLE = False
    VideoCallPage = None

from ..dialogs import (
    ProfileDialog,
    EditProfileDialog,
    SettingsDialog,
    NewChatDialog,
    DirectChatDialog,
    GroupChatDialog,
    GroupInfoDialog,
    FriendChatDialog,
    FriendRequestsDialog,
    GroupCreationDialog,
    EditMessageDialog,
    DeleteMessageDialog,
    ConversationSettingsDialog,
    AddMemberDialog
)


class MainChatScreen(ft.UserControl):
    def __init__(self, page: ft.Page, user: User, token: str, on_logout):
        super().__init__()
        self.expand = True  # Fill entire page
        self.page = page
        self.user = user
        self.token = token
        self.on_logout = on_logout
        
        # Data
        self.conversations: List[Conversation] = []
        self.current_conversation: Optional[Conversation] = None
        self.messages: List[Message] = []
        self.pending_requests_count: int = 0
        self.friends: List[dict] = []  # Friends list
        
        # WebSocket
        self.ws_client: Optional[WebSocketClient] = None
        
        # Video Call State
        self.current_call_id: Optional[str] = None
        self.current_call_page: Optional[VideoCallPage] = None
        self.call_timeout_timer_task: Optional[asyncio.Task] = None
        self.incoming_call_dialog: Optional[ft.AlertDialog] = None
        self.call_ringtone: Optional[ft.Audio] = None
        
        # UI Components
        self.conversation_list_view = ft.ListView(spacing=5, padding=10, auto_scroll=True)
        self.friends_list_view = ft.ListView(spacing=5, padding=10, auto_scroll=True)
        self.messages_list_view = ft.ListView(expand=True, spacing=10, padding=20, auto_scroll=True)
        
        # Message input component (replaces old input + file upload)
        self.message_input_widget = MessageInput(
            page=page,
            on_send=self.handle_send_message,
            on_typing=self.handle_typing
        )
        
        # Typing indicator
        self.typing_indicator = ft.Text(
            "",
            size=12,
            color=config.TEXT_SECONDARY,
            italic=True,
            visible=False
        )
        self.typing_users = set()  # Track who is typing
        self.typing_timer = None  # Debounce timer for sending typing events
        
        self.chat_header = ft.Text("Select a conversation", size=18, weight=ft.FontWeight.BOLD)
        self.chat_header_row = ft.Row([self.chat_header], expand=True, alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
        self.status_text = ft.Text("Loading...", size=12, color=config.TEXT_SECONDARY)
        
        # Friend requests badge
        self.friend_requests_badge = ft.Badge(
            content=ft.Text("0", size=10, color=ft.colors.WHITE),
            bgcolor=ft.colors.RED,
            small_size=18,
            visible=False
        )
        
        # Initialize data on startup
        print("MainChatScreen initialized")
    
    def did_mount(self):
        print("MainChatScreen mounted, loading data...")
        self.page.run_task(self.initialize_screen)
    
    async def initialize_screen(self):
        """Initialize screen with data"""
        print("Loading conversations, friends and connecting websocket...")
        await self.load_conversations()
        await self.load_friends()
        await self.load_pending_requests_count()
        await self.connect_websocket()
        self.page.run_task(self._periodic_refresh_conversations)
        
        print("Screen initialization complete")
    
    async def _periodic_refresh_conversations(self):
        """Periodically refresh conversations to catch any missed WebSocket events"""
        import asyncio
        while True:
            try:
                await asyncio.sleep(30)
                if not self.page:
                    break
                await self.load_conversations()
            except asyncio.CancelledError:
                break
            except Exception as e:
                import traceback
                traceback.print_exc()
                await asyncio.sleep(60)
    
    def build(self):
        print("Building main screen UI...")
        
        # Sidebar with conversations
        sidebar = ft.Container(
            content=ft.Column([
                # Header
                ft.Container(
                    content=ft.Row([
                        ft.Column([
                            ft.Text(self.user.display_name, size=16, weight=ft.FontWeight.BOLD),
                            ft.Text(f"@{self.user.username}", size=12, color=config.TEXT_SECONDARY)
                        ], expand=True),
                        ft.IconButton(
                            icon=ft.icons.SETTINGS,
                            tooltip="Settings",
                            on_click=lambda _: self.show_settings()
                        ),
                        ft.IconButton(
                            icon=ft.icons.PERSON,
                            tooltip="Profile",
                            on_click=lambda _: self.show_profile()
                        ),
                        ft.IconButton(
                            icon=ft.icons.LOGOUT,
                            tooltip="Logout",
                            on_click=lambda _: self.handle_logout()
                        )
                    ]),
                    bgcolor=config.PRIMARY_COLOR,
                    padding=15
                ),
                # New chat button
                ft.Container(
                    content=ft.ElevatedButton(
                        text="+ New Chat",
                        width=280,
                        on_click=self.show_new_chat_dialog,
                        style=ft.ButtonStyle(
                            bgcolor=config.SUCCESS_COLOR,
                            color=ft.colors.WHITE
                        )
                    ),
                    padding=10
                ),
                # Friend requests button with badge
                ft.Container(
                    content=ft.Stack([
                        ft.ElevatedButton(
                            text="Friend Requests",
                            icon=ft.icons.PERSON_ADD,
                            width=280,
                            on_click=lambda _: self.show_friend_requests(),
                            style=ft.ButtonStyle(
                                bgcolor=ft.colors.BLUE_400,
                                color=ft.colors.WHITE
                            )
                        ),
                        ft.Container(
                            content=self.friend_requests_badge,
                            right=10,
                            top=5
                        )
                    ]),
                    padding=ft.padding.only(left=10, right=10, bottom=10)
                ),
                # Tabs for Conversations and Friends
                ft.Container(
                    content=ft.Tabs(
                        selected_index=0,
                        animation_duration=300,
                        tabs=[
                            ft.Tab(
                                text="Chats",
                                icon=ft.icons.CHAT_BUBBLE_OUTLINE,
                                content=ft.Container(
                                    content=self.conversation_list_view,
                                    padding=ft.padding.only(top=10)
                                )
                            ),
                            ft.Tab(
                                text="Friends",
                                icon=ft.icons.PEOPLE_OUTLINE,
                                content=ft.Container(
                                    content=self.friends_list_view,
                                    padding=ft.padding.only(top=10)
                                )
                            ),
                        ],
                        expand=True,
                    ),
                    expand=True
                ),
                # Status
                ft.Container(
                    content=self.status_text,
                    padding=10
                )
            ]),
            width=320,
            bgcolor=ft.colors.BLUE_GREY_50,
            border=ft.border.only(right=ft.BorderSide(1, ft.colors.GREY_300))
        )
        
        # Main chat area
        chat_area = ft.Container(
            content=ft.Column([
                # Chat header
                ft.Container(
                    content=self.chat_header_row,
                    bgcolor=ft.colors.WHITE,
                    padding=15,
                    border=ft.border.only(bottom=ft.BorderSide(1, ft.colors.GREY_300))
                ),
                # Messages
                ft.Container(
                    content=ft.Column([
                        # Messages list
                        ft.Container(
                            content=self.messages_list_view,
                            expand=True
                        ),
                        # Typing indicator
                        ft.Container(
                            content=self.typing_indicator,
                            padding=ft.padding.only(left=20, right=20, bottom=5),
                            visible=False  # Hidden by default
                        )
                    ]),
                    bgcolor=config.BACKGROUND_COLOR,
                    expand=True
                ),
                # Input area (using MessageInput component)
                self.message_input_widget
            ]),
            expand=True
        )
        
        main_row = ft.Row(
            controls=[sidebar, chat_area],
            expand=True,
            spacing=0,
            vertical_alignment=ft.CrossAxisAlignment.START
        )
        # Wrap in container to ensure proper sizing
        return ft.Container(
            content=main_row,
            expand=True,
            padding=0,
            margin=0
        )
    
    def will_unmount(self):
        """Called when component will unmount"""
        print("👋 MainChatScreen unmounting...")
        # Disconnect WebSocket
        if self.ws_client:
            self.page.run_task(self.ws_client.disconnect)
        # Stop periodic refresh
        # Note: The periodic refresh task will check for page availability and stop itself
    
    async def load_conversations(self):
        """Load user's conversations"""
        try:
            print("Loading conversations from API...")

            if not self.page:
                return
            
            if hasattr(self, 'status_text') and self.status_text:
                self.status_text.value = "Loading conversations..."
                if self.page:
                    self.update()
            
            api = get_api_client()
            api.set_token(self.token)
            new_conversations = await api.get_conversations()
            
            self.conversations = new_conversations
            
            if self.page:
                self.render_conversations()
                
                if hasattr(self, 'status_text') and self.status_text:
                    self.status_text.value = f"{len(self.conversations)} conversations"
                self.update()
        
        except Exception as e:
            print(f"Error loading conversations: {e}")
            import traceback
            traceback.print_exc()
            # Only update UI if page is available
            if self.page and hasattr(self, 'status_text') and self.status_text:
                self.status_text.value = "Error loading conversations"
                self.update()
    
    def render_conversations(self):
        """Render conversations list"""
        self.conversation_list_view.controls.clear()
        
        if not self.conversations:
            self.conversation_list_view.controls.append(
                ft.Container(
                    content=ft.Text(
                        "No conversations yet\nClick '+ New Chat' to start",
                        text_align=ft.TextAlign.CENTER,
                        color=config.TEXT_SECONDARY
                    ),
                    padding=20,
                    alignment=ft.alignment.center
                )
            )
        else:
            for conv in self.conversations:
                is_selected = (self.current_conversation and 
                              self.current_conversation.id == conv.id)
                
                item = ConversationItem(
                    conversation=conv,
                    current_user=self.user,
                    page=self.page,
                    is_selected=is_selected,
                    on_click=self.handle_conversation_click
                )
                self.conversation_list_view.controls.append(item)
        
        self.update()
    
    async def load_friends(self):
        """Load friends list"""
        try:
            print("Loading friends from API...")
            
            api = get_api_client()
            api.set_token(self.token)
            response = await api.get("/friendships/friends")
            
            if response.status_code == 200:
                self.friends = response.json()
                print(f"Loaded {len(self.friends)} friends")
                
                # Render friends
                self.render_friends()
            else:
                print(f"Error loading friends: {response.status_code}")
                self.friends = []
                self.render_friends()
        
        except Exception as e:
            print(f"Error loading friends: {e}")
            self.friends = []
            self.render_friends()
    
    def render_friends(self):
        """Render friends list"""
        self.friends_list_view.controls.clear()
        
        if not self.friends:
            self.friends_list_view.controls.append(
                ft.Container(
                    content=ft.Text(
                        "No friends yet\nAdd friends to chat",
                        text_align=ft.TextAlign.CENTER,
                        color=config.TEXT_SECONDARY,
                        size=12
                    ),
                    padding=10,
                    alignment=ft.alignment.center
                )
            )
        else:
            for friend in self.friends:
                friend_item = self.build_friend_item(friend)
                self.friends_list_view.controls.append(friend_item)
        
        self.update()
    
    def build_friend_item(self, friend: dict) -> ft.Container:
        """Build UI for a single friend item"""
        username = friend.get("username", "Unknown")
        display_name = friend.get("display_name", username)
        is_active = friend.get("is_active", False)
        
        return ft.Container(
            content=ft.Row([
                # Avatar
                ft.Container(
                    content=ft.CircleAvatar(
                        content=ft.Text(display_name[0].upper(), size=14),
                        bgcolor=config.PRIMARY_COLOR,
                        color=ft.colors.WHITE,
                        radius=18
                    ),
                    padding=5
                ),
                # Name and status
                ft.Column([
                    ft.Text(display_name, size=13, weight=ft.FontWeight.BOLD),
                    ft.Row([
                        ft.Icon(
                            ft.icons.CIRCLE,
                            size=8,
                            color=ft.colors.GREEN if is_active else ft.colors.GREY
                        ),
                        ft.Text(f"@{username}", size=11, color=config.TEXT_SECONDARY)
                    ], spacing=5)
                ], spacing=2, expand=True),
                # Chat icon
                ft.IconButton(
                    icon=ft.icons.CHAT_BUBBLE_OUTLINE,
                    icon_size=18,
                    tooltip="Start chat",
                    on_click=lambda e, f=friend: self.page.run_task(self.handle_friend_click, f)
                )
            ], spacing=10, alignment=ft.MainAxisAlignment.START),
            bgcolor=ft.colors.WHITE,
            border_radius=8,
            padding=10,
            ink=True,
            on_click=lambda e, f=friend: self.page.run_task(self.handle_friend_click, f)
        )
    
    async def handle_friend_click(self, friend: dict):
        """Handle clicking on a friend to start/open chat"""
        try:
            friend_id = friend.get("user_id")
            friend_username = friend.get("username")
            friend_name = friend.get("display_name", friend_username)
            
            # Check if conversation already exists
            existing_conv = None
            for conv in self.conversations:
                if conv.type.value == "direct":
                    # Check if this conversation includes the friend
                    participant_ids = [str(p.user_id) for p in conv.participants]
                    if str(friend_id) in participant_ids:
                        existing_conv = conv
                        break
            
            if existing_conv:
                # Open existing conversation
                print(f"Opening existing conversation with {friend_username}")
                await self.select_conversation(existing_conv)
            else:
                api = get_api_client()
                api.set_token(self.token)
                
                response = await api.post(
                    "/conversations/",
                    json={
                        "type": "direct",
                        "title": friend_name,
                        "participant_ids": [friend_id]
                    }
                )
                
                if response.status_code in [200, 201]:
                    # Reload conversations to get the new one
                    await self.load_conversations()
                    
                    # Find and select the new conversation
                    for conv in self.conversations:
                        if conv.type.value == "direct":
                            participant_ids = [str(p.user_id) for p in conv.participants]
                            if str(friend_id) in participant_ids:
                                await self.select_conversation(conv)
                                break
                    
                    self.page.snack_bar = ft.SnackBar(
                        content=ft.Text(f"Chat with {friend_name} opened!"),
                        bgcolor=ft.colors.GREEN
                    )
                    self.page.snack_bar.open = True
                    self.page.update()
                else:
                    self.page.snack_bar = ft.SnackBar(
                        content=ft.Text(f"Failed to create chat: {response.status_code}"),
                        bgcolor=config.ERROR_COLOR
                    )
                    self.page.snack_bar.open = True
                    self.page.update()
        
        except Exception as e:
            print(f"Error starting chat with friend: {e}")
            self.page.snack_bar = ft.SnackBar(
                content=ft.Text(f"Error: {str(e)}"),
                bgcolor=config.ERROR_COLOR
            )
            self.page.snack_bar.open = True
            self.page.update()
    
    async def handle_conversation_click(self, conversation: Conversation):
        """Handle conversation click from ConversationItem"""
        await self.select_conversation(conversation)
    
    
    async def select_conversation(self, conv: Conversation):
        """Select and load conversation"""
        self.current_conversation = conv
        self.chat_header.value = conv.get_display_name(self.user.id)
        
        # Update chat header with buttons
        settings_button = ft.IconButton(
            icon=ft.icons.SETTINGS,
            tooltip="Cài đặt",
            icon_color=config.PRIMARY_COLOR,
            on_click=lambda e: self.page.run_task(self.open_conversation_settings)
        )
        
        if conv.type.value == "group":
            self.chat_header_row.controls = [
                self.chat_header,
                ft.Row([
                    ft.IconButton(
                        icon=ft.icons.INFO_OUTLINE,
                        tooltip="Group Info",
                        icon_color=config.PRIMARY_COLOR,
                        on_click=lambda e: self.show_group_info()
                    ),
                    settings_button
                ], spacing=5)
            ]
        else:
            # Direct chat: Add video call button
            video_call_button = ft.IconButton(
                icon=ft.icons.VIDEOCAM,
                tooltip="Video Call",
                icon_color=config.PRIMARY_COLOR,
                on_click=lambda e: self.page.run_task(self._start_video_call)
            )
            self.chat_header_row.controls = [
                self.chat_header,
                ft.Row([
                    video_call_button,
                    settings_button
                ], spacing=5)
            ]
        
        # Refresh conversation list to show selection
        self.render_conversations()
        
        # Load messages
        await self.load_messages()
    
    async def load_messages(self):
        """Load messages for current conversation"""
        if not self.current_conversation:
            print("load_messages: No current conversation selected")
            return
        
        try:
            print(f"Loading messages for conversation: {self.current_conversation.id}")
            api = get_api_client()
            api.set_token(self.token)
            messages = await api.get_messages(self.current_conversation.id)
            
            print(f"Loaded {len(messages)} messages from API")
            
            # Sort messages by created_at (oldest first)
            self.messages = sorted(messages, key=lambda m: m.created_at)
            
            # Mark unread messages from others as read
            for msg in self.messages:
                # Only mark messages from others that haven't been read yet
                if str(msg.sender_id) != str(self.user.id) and not msg.read_at:
                    try:
                        await api.put(f"/messages/{msg.id}/read")
                    except Exception as e:
                        pass
            
            # Load reactions for each message
            for msg in self.messages:
                try:
                    response = await api.get(f"/messages/{msg.id}/reactions")
                    reactions_data = response.json()  # Parse Response to dict
                    
                    # Convert reactions to dict format
                    reactions_dict = {}
                    for reaction_summary in reactions_data.get("reactions", []):
                        emoji = reaction_summary["emoji"]
                        users = reaction_summary["users"]
                        reactions_dict[emoji] = users
                    
                    msg.reactions = reactions_dict
                except Exception as e:
                    pass
                    msg.reactions = {}
            
            # Render messages
            self.render_messages()
            
            # Scroll to bottom to show latest message
            self.scroll_to_bottom()
        
        except Exception as e:
            print(f"Error loading messages: {e}")
    
    def scroll_to_bottom(self):
        """Scroll messages list to bottom"""
        try:
            if self.messages_list_view and len(self.messages_list_view.controls) > 0:
                # Scroll to the last message
                self.messages_list_view.scroll_to(
                    offset=-1,
                    duration=300,
                    curve=ft.AnimationCurve.EASE_OUT
                )
        except Exception as e:
            pass
    
    def render_messages(self):
        """Render messages in chat"""
        self.messages_list_view.controls.clear()
        
        if not self.messages:
            self.messages_list_view.controls.append(
                ft.Container(
                    content=ft.Text(
                        "No messages yet\nSay hi! 👋",
                        text_align=ft.TextAlign.CENTER,
                        color=config.TEXT_SECONDARY
                    ),
                    padding=40,
                    alignment=ft.alignment.center
                )
            )
        else:
            is_group_chat = (self.current_conversation and 
                            self.current_conversation.type.value == "group")
            
            # Render messages in order (oldest to newest)
            for msg in self.messages:
                bubble = MessageBubble(
                    message=msg,
                    current_user=self.user,
                    is_group_chat=is_group_chat,
                    on_download=self.download_file,
                    on_edit=self.handle_edit_message,
                    on_delete=self.handle_delete_message,
                    on_copy=self.handle_copy_message,
                    on_reaction_click=self.handle_reaction_click,
                    on_add_reaction=self.handle_add_reaction
                )
                self.messages_list_view.controls.append(bubble)
        
        self.update()
        
        # Auto-scroll to bottom after rendering
        try:
            self.messages_list_view.scroll_to(offset=-1, duration=100)
        except:
            pass
    
    
    async def handle_send_message(self, content: str, file_path: Optional[Path]):
        """Handle send message from MessageInput component"""
        # Check if we have content or file
        if not content and not file_path:
            return
        
        if not self.current_conversation:
            self.page.snack_bar = ft.SnackBar(
                content=ft.Text("Please select a conversation first"),
                bgcolor=config.ERROR_COLOR
            )
            self.page.snack_bar.open = True
            self.page.update()
            return
        
        # Prepare message data
        file_url = None
        file_type = None
        file_name = None
        
        # Upload file if provided
        if file_path:
            try:
                # Show upload progress
                self.message_input_widget.show_upload_progress()
                
                # Upload file
                api = get_api_client()
                upload_result = await api.upload_file(file_path)
                
                # Get file info from response
                file_url = upload_result.get("file_url")
                file_type = upload_result.get("file_type")
                file_name = upload_result.get("file_name")
                
                
                # Hide progress
                self.message_input_widget.hide_upload_progress()
                
            except Exception as e:
                print(f"Error uploading file: {e}")
                self.message_input_widget.hide_upload_progress()
                
                self.page.snack_bar = ft.SnackBar(
                    content=ft.Text(f"Failed to upload file: {str(e)}"),
                    bgcolor=config.ERROR_COLOR
                )
                self.page.snack_bar.open = True
                self.page.update()
                return
        
        try:
            # Send via API
            api = get_api_client()
            message = await api.send_message(
                conversation_id=self.current_conversation.id,
                content=content or "(File)",  # Default content if only file
                file_url=file_url,
                file_type=file_type,
                file_name=file_name
            )
            
            # Add to messages list
            self.messages.append(message)
            self.render_messages()
            
            # Note: WebSocket will broadcast, but we already show it locally
        
        except Exception as e:
            print(f"Error sending message: {e}")
            self.page.snack_bar = ft.SnackBar(
                content=ft.Text(f"Failed to send message: {str(e)}"),
                bgcolor=config.ERROR_COLOR
            )
            self.page.snack_bar.open = True
            self.page.update()
    
    async def connect_websocket(self):
        """Connect to WebSocket for real-time updates"""
        try:
            print("Connecting to WebSocket...")
            self.ws_client = WebSocketClient(self.token)
            self.ws_client.add_message_callback(self.handle_ws_message)
            self.ws_client.add_call_callback(self.handle_call_message)
            
            await self.ws_client.connect()
            
            if hasattr(self, 'status_text') and self.status_text:
                self.status_text.value = "Connected"
            
            await self.load_conversations()
            
            if self.page:
                self.update()
        
        except Exception as e:
            print(f"WebSocket connection error: {e}")
            import traceback
            traceback.print_exc()
            if hasattr(self, 'status_text') and self.status_text:
                self.status_text.value = "Offline"
            if self.page:
                self.update()
    
    def handle_ws_message(self, data: dict):
        """Handle incoming WebSocket message"""
        try:
            print(f"WebSocket message received: {data}")
            
            msg_type = data.get("type")
            msg_data = data.get("data", {})
            
            if not msg_data and "conversation" in data:
                msg_data = data
            
            if msg_type == "new_message":
                message_id = msg_data.get("message_id")
                conversation_id = msg_data.get("conversation_id")
                sender_id = msg_data.get("sender_id")
                
                conv_exists = any(str(c.id) == str(conversation_id) for c in self.conversations)
                
                if not conv_exists:
                    self.page.run_task(self._fetch_and_add_conversation, str(conversation_id))
                    self.page.run_task(self.load_conversations)
                
                if self.current_conversation:
                    conv_match = str(conversation_id) == str(self.current_conversation.id)
                    
                    if conv_match:
                        self.page.run_task(self.load_messages)
                
                self.page.run_task(self.load_conversations)
            
            elif msg_type == "typing":
                # Typing indicator from another user
                conversation_id = msg_data.get("conversation_id")
                user_id = msg_data.get("user_id")
                username = msg_data.get("username")
                is_typing = msg_data.get("is_typing", False)
                
                # Only show if it's for current conversation and not from me
                if (self.current_conversation and 
                    conversation_id == self.current_conversation.id and
                    user_id != self.user.id):
                    
                    if is_typing:
                        self.typing_users.add(username)
                    else:
                        self.typing_users.discard(username)
                    
                    self.update_typing_indicator()
            
            elif msg_type == "user_online":
                username = msg_data.get("username")
                print(f"User {username} is online")
            
            elif msg_type == "user_offline":
                username = msg_data.get("username")
                print(f"User {username} is offline")
            
            elif msg_type == "message_edited":
                # Message was edited
                message_id = msg_data.get("message_id")
                conversation_id = msg_data.get("conversation_id")
                new_content = msg_data.get("content")
                
                print(f"MESSAGE EDITED EVENT: {message_id}")
                
                # If it's for current conversation, reload messages
                if (self.current_conversation and 
                    str(conversation_id) == str(self.current_conversation.id)):
                    self.page.run_task(self.load_messages)
                
                # Update conversation list (in case edited message was last message)
                self.page.run_task(self.load_conversations)
            
            elif msg_type == "message_deleted":
                # Message was deleted
                message_id = msg_data.get("message_id")
                conversation_id = msg_data.get("conversation_id")
                
                print(f"MESSAGE DELETED EVENT: {message_id}")
                
                # If it's for current conversation, reload messages
                if (self.current_conversation and 
                    str(conversation_id) == str(self.current_conversation.id)):
                    self.page.run_task(self.load_messages)
                
                # Update conversation list
                self.page.run_task(self.load_conversations)
            
            elif msg_type == "message_read":
                # Message was read by recipient
                message_id = msg_data.get("message_id")
                read_at_str = msg_data.get("read_at")
                read_by_user_id = msg_data.get("read_by_user_id")
                
                print(f"✓✓ MESSAGE READ EVENT: {message_id}")
                
                # Update message status in local messages list
                for msg in self.messages:
                    if str(msg.id) == str(message_id):
                        # Parse datetime
                        from datetime import datetime
                        try:
                            msg.read_at = datetime.fromisoformat(read_at_str.replace("Z", "+00:00"))
                            msg.read_by_user_id = read_by_user_id
                        except Exception as e:
                            pass
                        break
                
                # Update UI to show new status
                if self.current_conversation:
                    # Re-render messages to show updated read status
                    self.render_messages()
            
            elif msg_type == "reaction_added":
                # Reaction was added
                message_id = msg_data.get("message_id")
                conversation_id = msg_data.get("conversation_id")
                emoji = msg_data.get("emoji")
                username = msg_data.get("username")
                user_id = msg_data.get("user_id")
                
                print(f"REACTION ADDED: {emoji} by {username} on {message_id}")
                print(f"   - Conversation ID: {conversation_id}")
                print(f"   - Current conversation: {self.current_conversation.id if self.current_conversation else None}")
                
                # Check if it's for current conversation
                if (self.current_conversation and 
                    str(conversation_id) == str(self.current_conversation.id)):
                    
                    # Try to update reaction in local messages list first
                    reaction_updated = False
                    for msg in self.messages:
                        if str(msg.id) == str(message_id):
                            # Initialize reactions dict if not exists
                            if not hasattr(msg, 'reactions') or msg.reactions is None:
                                msg.reactions = {}
                            
                            # Add reaction to message
                            if emoji not in msg.reactions:
                                msg.reactions[emoji] = []
                            
                            # Add user to reaction list if not already there
                            user_already_reacted = any(
                                u.get("user_id") == str(user_id) or u.get("id") == str(user_id)
                                for u in msg.reactions[emoji]
                            )
                            
                            if not user_already_reacted:
                                msg.reactions[emoji].append({
                                    "user_id": str(user_id),
                                    "username": username
                                })
                                reaction_updated = True
                            break
                    
                    # If reaction was updated locally, re-render messages
                    if reaction_updated:
                        print(f"Re-rendering messages to show updated reaction")
                        self.render_messages()
                    else:
                        print(f"Message not found in local list, reloading from API...")
                        self.page.run_task(self.load_messages)
                else:
                    print(f"Conversation doesn't match, skipping reaction update")
            
            elif msg_type == "reaction_removed":
                # Reaction was removed
                message_id = msg_data.get("message_id")
                conversation_id = msg_data.get("conversation_id")
                emoji = msg_data.get("emoji")
                user_id = msg_data.get("user_id")
                
                print(f"REACTION REMOVED: {emoji} from {message_id}")
                print(f"   - Conversation ID: {conversation_id}")
                print(f"   - Current conversation: {self.current_conversation.id if self.current_conversation else None}")
                
                # Check if it's for current conversation
                if (self.current_conversation and 
                    str(conversation_id) == str(self.current_conversation.id)):
                    
                    # Try to update reaction in local messages list first
                    reaction_updated = False
                    for msg in self.messages:
                        if str(msg.id) == str(message_id):
                            # Initialize reactions dict if not exists
                            if not hasattr(msg, 'reactions') or msg.reactions is None:
                                msg.reactions = {}
                            
                            # Remove reaction from message
                            if emoji in msg.reactions:
                                # Remove user from reaction list
                                original_count = len(msg.reactions[emoji])
                                msg.reactions[emoji] = [
                                    u for u in msg.reactions[emoji]
                                    if u.get("user_id") != str(user_id) and u.get("id") != str(user_id)
                                ]
                                
                                # If no users left, remove emoji key
                                if len(msg.reactions[emoji]) == 0:
                                    del msg.reactions[emoji]
                                
                                if len(msg.reactions[emoji]) < original_count:
                                    reaction_updated = True
                            break
                    
                    if reaction_updated:
                        self.render_messages()
                    else:
                        self.page.run_task(self.load_messages)
            
            elif msg_type == "new_conversation":
                conversation_data = None
                if isinstance(msg_data, dict):
                    if "conversation" in msg_data:
                        conversation_data = msg_data.get("conversation")
                    elif "conversation" in data:
                        conversation_data = data.get("conversation")
                
                if conversation_data:
                    try:
                        new_conv = Conversation.from_dict(conversation_data)
                        exists = any(str(c.id) == str(new_conv.id) for c in self.conversations)
                        
                        if not exists:
                            self.conversations.insert(0, new_conv)
                            self.render_conversations()
                        else:
                            self.page.run_task(self.load_conversations)
                    except Exception as e:
                        import traceback
                        traceback.print_exc()
                        self.page.run_task(self.load_conversations)
                else:
                    self.page.run_task(self.load_conversations)
        
        except Exception as e:
            print(f"Error in handle_ws_message: {e}")
            import traceback
            traceback.print_exc()
    
    def update_typing_indicator(self):
        """Update typing indicator UI"""
        if not self.typing_users:
            self.typing_indicator.visible = False
            self.typing_indicator.value = ""
        else:
            self.typing_indicator.visible = True
            
            if len(self.typing_users) == 1:
                username = list(self.typing_users)[0]
                self.typing_indicator.value = f"{username} is typing..."
            elif len(self.typing_users) == 2:
                users = list(self.typing_users)
                self.typing_indicator.value = f"{users[0]} and {users[1]} are typing..."
            else:
                self.typing_indicator.value = f"{len(self.typing_users)} people are typing..."
        
        self.page.update()
    
    def handle_typing(self, e):
        """Handle user typing in message input"""
        if not self.current_conversation:
            return
        
        # Debounce: Send typing event only if user is actually typing
        # Cancel previous timer
        if self.typing_timer:
            self.typing_timer.cancel()
        
        # Send typing=True
        if self.ws_client:
            self.page.run_task(self.send_typing_event, True)
        
        # Set timer to send typing=False after 3 seconds of inactivity
        import threading
        self.typing_timer = threading.Timer(3.0, lambda: self.page.run_task(self.send_typing_event, False))
        self.typing_timer.start()
    
    async def send_typing_event(self, is_typing: bool):
        """Send typing event via WebSocket"""
        if not self.ws_client or not self.current_conversation:
            return
        
        # Check if WebSocket is actually connected
        if not self.ws_client.connected:
            return  # Silently skip if not connected yet
        
        try:
            await self.ws_client.send_typing(
                str(self.current_conversation.id),
                is_typing
            )
        except Exception as e:
            print(f"Error sending typing event: {e}")
    
    async def show_new_chat_dialog(self, e):
        """Show dialog to create new conversation (direct or group)"""
        try:
            # Show chat type selection dialog
            dialog = NewChatDialog(
                page=self.page,
                on_direct_chat=self.show_friend_chat_dialog,
                on_group_chat=self.show_group_chat_dialog
            )
            dialog.show()
        
        except Exception as e:
            print(f"Error loading users: {e}")
            self.page.snack_bar = ft.SnackBar(
                content=ft.Text(f"Error: {str(e)}"),
                bgcolor=ft.colors.RED
            )
            self.page.snack_bar.open = True
            self.page.update()
    
    def show_friend_chat_dialog(self):
        """Show friend chat dialog for searching users and sending friend requests"""
        try:
            api = get_api_client()
            api.set_token(self.token)  # Set authentication token
            dialog = FriendChatDialog(
                page=self.page,
                api_client=api,
                current_user=self.user,
                on_chat_created=lambda: self.load_conversations()
            )
            dialog.show()
        except Exception as e:
            print(f"Error showing friend chat dialog: {e}")
            self.page.snack_bar = ft.SnackBar(
                content=ft.Text(f"Error: {str(e)}"),
                bgcolor=ft.colors.RED
            )
            self.page.snack_bar.open = True
            self.page.update()
    
    def show_group_chat_dialog(self):
        """Show group chat creation dialog"""
        try:
            api = get_api_client()
            api.set_token(self.token)
            
            dialog = GroupCreationDialog(
                page=self.page,
                api_client=api,
                current_user=self.user,
                on_group_created=lambda: self.page.run_task(self.load_conversations)
            )
            dialog.show()
        except Exception as e:
            print(f"Error showing group chat dialog: {e}")
            self.page.snack_bar = ft.SnackBar(
                content=ft.Text(f"Error: {str(e)}"),
                bgcolor=ft.colors.RED
            )
            self.page.snack_bar.open = True
            self.page.update()
    
    def show_direct_chat_selection(self, users):
        """Show dialog to select user for direct chat"""
        async def handle_select(user: User):
            await self.create_direct_conversation(user)
        
        dialog = DirectChatDialog(
            users=users,
            on_select=handle_select
        )
        
        self.page.dialog = dialog
        dialog.open = True
        self.page.update()
    
    def show_group_chat_creation(self, users):
        """Show dialog to create group chat"""
        async def handle_create(group_name: str, member_ids: List[str]):
            await self.create_group_conversation(group_name, member_ids)
        
        dialog = GroupChatDialog(
            users=users,
            on_create=handle_create
        )
        
        self.page.dialog = dialog
        dialog.open = True
        self.page.update()
    
    async def create_direct_conversation(self, user: User):
        """Create direct conversation with user"""
        try:
            api = get_api_client()
            conversation = await api.create_conversation(
                type="direct",
                participant_ids=[user.id]
            )
            
            # Close dialog
            if self.page.dialog:
                self.page.dialog.open = False
            
            # Reload conversations
            await self.load_conversations()
            
            # Select new conversation
            await self.select_conversation(conversation)
        
        except Exception as e:
            error_msg = str(e)
            if "already exists" in error_msg:
                # Conversation exists, just close dialog
                if self.page.dialog:
                    self.page.dialog.open = False
                await self.load_conversations()
            else:
                print(f"Error creating conversation: {e}")
                raise
    
    async def create_group_conversation(self, group_name: str, member_ids: List[str]):
        """Create group conversation"""
        # Validate
        if not group_name or not group_name.strip():
            raise ValueError("Please enter a group name")
        
        if not member_ids or len(member_ids) == 0:
            raise ValueError("Please select at least one member")
        
        try:
            api = get_api_client()
            conversation = await api.create_conversation(
                type="group",
                title=group_name.strip(),
                participant_ids=member_ids
            )
            
            
            # Close dialog
            if self.page.dialog:
                self.page.dialog.open = False
            
            # Reload conversations
            await self.load_conversations()
            
            # Select new conversation
            await self.select_conversation(conversation)
            
            # Show success message
            self.page.snack_bar = ft.SnackBar(
                content=ft.Text(f"Group '{group_name}' created successfully!"),
                bgcolor=config.SUCCESS_COLOR
            )
            self.page.snack_bar.open = True
            self.page.update()
        
        except Exception as e:
            print(f"Error creating group: {e}")
            raise
    
    def close_dialog(self, dialog):
        """Close dialog"""
        dialog.open = False
        self.page.update()
    
    def show_group_info(self):
        """Show group information and management dialog"""
        if not self.current_conversation or self.current_conversation.type.value != "group":
            return
        
        # TODO: Implement add/remove members handlers
        async def handle_add_members(member_ids: List[str]):
            print(f"Adding members: {member_ids}")
            # Backend API call to add members
        
        async def handle_remove_member(user_id: str):
            print(f"Removing member: {user_id}")
            # Backend API call to remove member
        
        dialog = GroupInfoDialog(
            conversation=self.current_conversation,
            current_user=self.user,
            on_add_members=handle_add_members,
            on_remove_member=handle_remove_member
        )
        dialog.open(self.page)
    
    async def open_conversation_settings(self):
        """Open conversation settings dialog"""
        if not self.current_conversation:
            return
        
        dialog = ConversationSettingsDialog(
            page=self.page,
            conversation=self.current_conversation,
            current_user_id=self.user.id,
            on_action=self.handle_settings_action
        )
        dialog.open()
    
    async def handle_settings_action(self, action: str):
        """Handle settings action callback"""
        if action in ["unfriend", "delete", "leave"]:
            # Reload conversations (conversation will disappear from list)
            await self.load_conversations()
            
            # Clear current conversation if it was the one we just left/deleted
            if self.current_conversation:
                # Check if still in list
                still_exists = any(
                    c.id == self.current_conversation.id
                    for c in self.conversations
                )
                
                if not still_exists:
                    # Clear chat area
                    self.current_conversation = None
                    self.messages = []
                    self.chat_header.value = "Select a conversation"
                    self.messages_list_view.controls.clear()
                    self.chat_header_row.controls = [self.chat_header]
                    self.update()
        
        elif action == "add_member":
            # Open add member dialog
            existing_ids = [p.user_id for p in self.current_conversation.participants]
            
            add_dialog = AddMemberDialog(
                page=self.page,
                conversation_id=self.current_conversation.id,
                existing_participant_ids=existing_ids,
                on_add=self.on_member_added
            )
            add_dialog.open()
    
    async def on_member_added(self, user_id: str):
        """Callback when member is added"""
        # Reload conversation to get updated participants
        if self.current_conversation:
            api = get_api_client()
            updated_conv = await api.get_conversation(self.current_conversation.id)
            self.current_conversation = updated_conv
            await self.select_conversation(updated_conv)
        
        # Show notification
        self.page.snack_bar = ft.SnackBar(
            content=ft.Text("Đã thêm thành viên thành công"),
            bgcolor=config.SUCCESS_COLOR
        )
        self.page.snack_bar.open = True
        self.page.update()
    
    async def _fetch_and_add_conversation(self, conversation_id: str):
        """Fetch conversation from API and add to list if not exists"""
        try:
            print(f"Fetching conversation {conversation_id} from API...")
            api = get_api_client()
            api.set_token(self.token)
            conv = await api.get_conversation(conversation_id)
            
            # Check if already exists
            exists = any(str(c.id) == str(conv.id) for c in self.conversations)
            print(f"   - Conversation exists in list: {exists}")
            
            if not exists:
                print(f"Adding conversation {conversation_id} to list")
                self.conversations.insert(0, conv)
                print(f"   - Added to list, now have {len(self.conversations)} conversations")
                self.render_conversations()
                print(f"Conversation added and rendered!")
            else:
                print(f"Conversation already exists, skipping add")
        except Exception as e:
            print(f"Error fetching conversation {conversation_id}: {e}")
            import traceback
            traceback.print_exc()
            print(f"Falling back to reload all conversations...")
            await self.load_conversations()
    
    def download_file(self, file_url: str, file_name: str):
        """Download file - open in browser"""
        # Note: In Flet, we can open URL in browser
        # For actual download, we'd need to implement save dialog
        import webbrowser
        print(f"Opening file: {file_url}")
        webbrowser.open(file_url)
        
        # Show notification
        self.page.snack_bar = ft.SnackBar(
            content=ft.Text(f"Opening {file_name} in browser..."),
            bgcolor=config.SUCCESS_COLOR
        )
        self.page.snack_bar.open = True
        self.page.update()
    
    def handle_copy_message(self, message: Message):
        """Handle copy message to clipboard"""
        try:
            self.page.set_clipboard(message.content)
            self.page.snack_bar = ft.SnackBar(
                content=ft.Text("Message copied to clipboard"),
                bgcolor=config.SUCCESS_COLOR
            )
            self.page.snack_bar.open = True
            self.page.update()
        except Exception as e:
            self.page.snack_bar = ft.SnackBar(
                content=ft.Text("Failed to copy message"),
                bgcolor=config.ERROR_COLOR
            )
            self.page.snack_bar.open = True
            self.page.update()
    
    def handle_edit_message(self, message: Message):
        """Handle edit message"""
        async def save_edit(message_id: str, new_content: str):
            try:
                api = get_api_client()
                api.set_token(self.token)
                
                # Call API to update message
                response = await api.put(f"/messages/{message_id}", json={"content": new_content})
                
                print(f"Message edited: {message_id}")
                
                # Show success message
                self.page.snack_bar = ft.SnackBar(
                    content=ft.Text("Message updated successfully"),
                    bgcolor=config.SUCCESS_COLOR
                )
                self.page.snack_bar.open = True
                self.page.update()
                
                # Reload messages to show edit
                await self.load_messages()
                
            except Exception as e:
                print(f"Error editing message: {e}")
                self.page.snack_bar = ft.SnackBar(
                    content=ft.Text(f"Failed to edit message: {str(e)}"),
                    bgcolor=config.ERROR_COLOR
                )
                self.page.snack_bar.open = True
                self.page.update()
        
        # Show edit dialog
        dialog = EditMessageDialog(
            message=message,
            page=self.page,
            on_save=lambda msg_id, content: self.page.run_task(save_edit, msg_id, content)
        )
        dialog.show()
    
    def handle_delete_message(self, message: Message):
        """Handle delete message"""
        async def confirm_delete(message_id: str):
            try:
                api = get_api_client()
                api.set_token(self.token)
                
                # Call API to delete message
                await api.delete(f"/messages/{message_id}")
                
                print(f"Message deleted: {message_id}")
                
                # Show success message
                self.page.snack_bar = ft.SnackBar(
                    content=ft.Text("Message deleted"),
                    bgcolor=config.SUCCESS_COLOR
                )
                self.page.snack_bar.open = True
                self.page.update()
                
                # Reload messages to show deletion
                await self.load_messages()
                
            except Exception as e:
                print(f"Error deleting message: {e}")
                self.page.snack_bar = ft.SnackBar(
                    content=ft.Text(f"Failed to delete message: {str(e)}"),
                    bgcolor=config.ERROR_COLOR
                )
                self.page.snack_bar.open = True
                self.page.update()
        
        # Show delete confirmation dialog
        dialog = DeleteMessageDialog(
            message=message,
            page=self.page,
            on_confirm=lambda msg_id: self.page.run_task(confirm_delete, msg_id)
        )
        dialog.show()
    
    def handle_reaction_click(self, message: Message, emoji: str, is_my_reaction: bool):
        """Handle clicking on a reaction - toggle on/off"""
        async def toggle_reaction():
            try:
                api = get_api_client()
                api.set_token(self.token)
                
                if is_my_reaction:
                    # Remove reaction
                    await api.delete(f"/messages/{message.id}/reactions/{emoji}")
                    print(f"Removed reaction {emoji}")
                else:
                    # Add reaction
                    await api.post(f"/messages/{message.id}/reactions", json={"emoji": emoji})
                    print(f"Added reaction {emoji}")
                
                # Reload messages to show update
                await self.load_messages()
                
            except Exception as e:
                print(f"Error toggling reaction: {e}")
                self.page.snack_bar = ft.SnackBar(
                    content=ft.Text(f"Failed to react: {str(e)}"),
                    bgcolor=config.ERROR_COLOR
                )
                self.page.snack_bar.open = True
                self.page.update()
        
        self.page.run_task(toggle_reaction)
    
    def handle_add_reaction(self, message: Message):
        """Handle clicking add reaction button - show picker"""
        from ..components import ReactionPickerDialog
        
        def on_emoji_selected(emoji: str):
            # Add the selected emoji
            self.page.run_task(self._add_reaction_async, message.id, emoji)
        
        dialog = ReactionPickerDialog(
            page=self.page,
            on_reaction_selected=on_emoji_selected
        )
        dialog.show()
    
    async def _add_reaction_async(self, message_id: str, emoji: str):
        """Add reaction async"""
        try:
            api = get_api_client()
            api.set_token(self.token)
            
            await api.post(f"/messages/{message_id}/reactions", json={"emoji": emoji})
            print(f"Added reaction {emoji}")
            
            # Reload messages
            await self.load_messages()
            
        except Exception as e:
            print(f"Error adding reaction: {e}")
            self.page.snack_bar = ft.SnackBar(
                content=ft.Text(f"Failed to add reaction: {str(e)}"),
                bgcolor=config.ERROR_COLOR
            )
            self.page.snack_bar.open = True
            self.page.update()
    
    def show_profile(self):
        """Show user profile dialog"""
        dialog = ProfileDialog(
            user=self.user,
            page=self.page,
            on_edit=self.show_edit_profile
        )
        dialog.show()
    
    def show_edit_profile(self):
        """Show edit profile dialog"""
        async def handle_save(full_name: str, bio: str):
            try:
                api = get_api_client()
                
                # Update local user object (backend API support needed)
                self.user.display_name = full_name.strip()
                # self.user.bio = bio  # If bio field exists
                
                # Show success
                self.page.snack_bar = ft.SnackBar(
                    content=ft.Text("Profile updated successfully!"),
                    bgcolor=config.SUCCESS_COLOR
                )
                self.page.snack_bar.open = True
                self.page.update()
                
                
            except Exception as ex:
                print(f"Error updating profile: {ex}")
                raise
        
        dialog = EditProfileDialog(
            user=self.user,
            page=self.page,
            on_save=handle_save
        )
        dialog.show()
    
    def show_settings(self):
        """Show settings dialog"""
        dialog = SettingsDialog(page=self.page)
        dialog.show()
    
    async def load_pending_requests_count(self):
        """Load count of pending friend requests"""
        try:
            api = get_api_client()
            api.set_token(self.token)
            
            response = await api.get("/friendships/requests/received")
            
            if response.status_code == 200:
                data = response.json()
                # Count only pending requests (all received requests are for current user)
                self.pending_requests_count = sum(
                    1 for req in data 
                    if req.get("status") == "pending"
                )
                
                # Update badge
                if self.pending_requests_count > 0:
                    self.friend_requests_badge.content.value = str(self.pending_requests_count)
                    self.friend_requests_badge.visible = True
                else:
                    self.friend_requests_badge.visible = False
                
                self.update()
                print(f"Pending friend requests: {self.pending_requests_count}")
        
        except Exception as e:
            print(f"Error loading pending requests count: {e}")
    
    def show_friend_requests(self):
        """Show friend requests dialog"""
        try:
            api = get_api_client()
            api.set_token(self.token)
            
            dialog = FriendRequestsDialog(
                page=self.page,
                api_client=api,
                current_user=self.user,
                on_request_handled=self.handle_friend_request_handled
            )
            dialog.show()
        
        except Exception as e:
            print(f"Error showing friend requests: {e}")
            self.page.snack_bar = ft.SnackBar(
                content=ft.Text(f"Error: {str(e)}"),
                bgcolor=ft.colors.RED
            )
            self.page.snack_bar.open = True
            self.page.update()
    
    def handle_friend_request_handled(self):
        """Handle when a friend request is accepted or rejected"""
        # Reload conversations (in case new chat was created)
        self.page.run_task(self.load_conversations)
        # Reload friends list
        self.page.run_task(self.load_friends)
        # Reload pending requests count
        self.page.run_task(self.load_pending_requests_count)
    
    # ========== Video Call Methods ==========
    
    async def _start_video_call(self):
        """Start a video call with current conversation participant"""
        if not self.current_conversation:
            self.page.snack_bar = ft.SnackBar(
                content=ft.Text("Please select a conversation first"),
                bgcolor=config.ERROR_COLOR
            )
            self.page.snack_bar.open = True
            self.page.update()
            return
        
        if self.current_conversation.type.value != "direct":
            self.page.snack_bar = ft.SnackBar(
                content=ft.Text("Video calls are only available for direct chats"),
                bgcolor=config.ERROR_COLOR
            )
            self.page.snack_bar.open = True
            self.page.update()
            return
        
        # Check if already in a call
        if self.current_call_id:
            self.page.snack_bar = ft.SnackBar(
                content=ft.Text("You are already in a call"),
                bgcolor=config.ERROR_COLOR
            )
            self.page.snack_bar.open = True
            self.page.update()
            return
        
        try:
            # Get remote user from conversation
            remote_user = None
            for participant in self.current_conversation.participants:
                if str(participant.user_id) != str(self.user.id):
                    remote_user = participant
                    break
            
            if not remote_user:
                self.page.snack_bar = ft.SnackBar(
                    content=ft.Text("Could not find conversation participant"),
                    bgcolor=config.ERROR_COLOR
                )
                self.page.snack_bar.open = True
                self.page.update()
                return
            
            # Generate call ID
            call_id = str(uuid.uuid4())
            self.current_call_id = call_id
            
            # Send call invite
            await self.ws_client.send_call_invite(
                call_id=call_id,
                caller_id=str(self.user.id),
                callee_id=str(remote_user.user_id),
                conversation_id=str(self.current_conversation.id)
            )
            
            # Show calling overlay
            self._show_calling_overlay(remote_user.display_name or remote_user.username)
            
            # Setup timeout timer (30 seconds) using asyncio
            call_id_for_timeout = call_id  # Capture call_id for closure
            async def timeout_task():
                await asyncio.sleep(30)  # Wait 30 seconds
                if self.current_call_id == call_id_for_timeout:  # Still waiting for this call
                    await self._handle_call_timeout()
            
            self.call_timeout_timer_task = asyncio.create_task(timeout_task())
            
        except Exception as e:
            print(f"Error starting video call: {e}")
            import traceback
            traceback.print_exc()
            self.current_call_id = None
            self.page.snack_bar = ft.SnackBar(
                content=ft.Text(f"Failed to start call: {str(e)}"),
                bgcolor=config.ERROR_COLOR
            )
            self.page.snack_bar.open = True
            self.page.update()
    
    def _show_calling_overlay(self, remote_username: str):
        """Show calling overlay while waiting for answer"""
        # Create overlay dialog
        calling_dialog = ft.AlertDialog(
            title=ft.Text("Calling..."),
            content=ft.Column([
                ft.Text(f"Calling {remote_username}...", size=16),
                ft.ProgressRing()
            ], tight=True, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            actions=[
                ft.TextButton(
                    text="Cancel",
                    on_click=lambda e: self.page.run_task(self._cancel_call)
                )
            ],
            modal=True
        )
        self.page.dialog = calling_dialog
        calling_dialog.open = True
        self.page.update()
    
    async def _cancel_call(self):
        """Cancel outgoing call"""
        if self.current_call_id and self.ws_client:
            await self.ws_client.send_call_end(
                call_id=self.current_call_id,
                ended_by=str(self.user.id)
            )
        
        await self._close_calling_overlay()
        self.current_call_id = None
    
    async def _close_calling_overlay(self):
        """Close calling overlay"""
        if self.call_timeout_timer_task and not self.call_timeout_timer_task.done():
            self.call_timeout_timer_task.cancel()
            try:
                await self.call_timeout_timer_task
            except asyncio.CancelledError:
                pass
            self.call_timeout_timer_task = None
        
        if self.page.dialog:
            self.page.dialog.open = False
            self.page.dialog = None
            self.page.update()
    
    def handle_call_message(self, data: dict):
        """Handle incoming call-related WebSocket messages"""
        try:
            msg_type = data.get("type")
            msg_data = data.get("data", {})
            
            
            if msg_type == "call_invite_sent":
                call_id = msg_data.get("call_id")
            
            elif msg_type == "call_incoming":
                # Incoming call
                call_id = msg_data.get("call_id")
                caller_id = msg_data.get("caller_id")
                caller_username = msg_data.get("caller_username", "Unknown")
                caller_display_name = msg_data.get("caller_display_name", caller_username)
                
                # Check if already in a call
                if self.current_call_id:
                    # Reject automatically (busy)
                    self.page.run_task(
                        self._reject_incoming_call,
                        call_id,
                        caller_id,
                        "busy"
                    )
                    return
                
                self.current_call_id = call_id
                self._show_incoming_call_dialog(call_id, caller_id, caller_display_name)
            
            elif msg_type == "call_accepted":
                # Call was accepted by callee
                call_id = msg_data.get("call_id")
                callee_username = msg_data.get("callee_username", "Unknown")
                
                if call_id == self.current_call_id:
                    self.page.run_task(self._close_calling_overlay)
                    # Open video call page
                    self.page.run_task(self._open_video_call_page, call_id, True)
            
            elif msg_type == "call_reject":
                # Call was rejected
                call_id = msg_data.get("call_id")
                reason = msg_data.get("reason", "rejected")
                
                if call_id == self.current_call_id:
                    self.page.run_task(self._close_calling_overlay)
                    self.current_call_id = None
                    
                    reason_text = "User is busy" if reason == "busy" else "Call was rejected"
                    self.page.snack_bar = ft.SnackBar(
                        content=ft.Text(reason_text),
                        bgcolor=config.ERROR_COLOR
                    )
                    self.page.snack_bar.open = True
                    self.page.update()
            
            elif msg_type == "call_ended":
                # Call ended
                call_id = msg_data.get("call_id")
                
                if call_id == self.current_call_id:
                    self._close_video_call_page()
                    self.current_call_id = None
                    
                    self.page.snack_bar = ft.SnackBar(
                        content=ft.Text("Call ended"),
                        bgcolor=config.TEXT_SECONDARY
                    )
                    self.page.snack_bar.open = True
                    self.page.update()
            
            elif msg_type in ["sdp_offer", "sdp_answer", "ice_candidate"]:
                # Forward to video call page if open
                if self.current_call_page:
                    if msg_type == "sdp_offer":
                        self.page.run_task(
                            self.current_call_page.handle_sdp_offer,
                            msg_data.get("sdp")
                        )
                    elif msg_type == "sdp_answer":
                        self.page.run_task(
                            self.current_call_page.handle_sdp_answer,
                            msg_data.get("sdp")
                        )
                    elif msg_type == "ice_candidate":
                        self.page.run_task(
                            self.current_call_page.handle_ice_candidate,
                            msg_data.get("candidate"),
                            msg_data.get("sdp_mid"),
                            msg_data.get("sdp_mline_index")
                        )
        
        except Exception as e:
            print(f"Error handling call message: {e}")
            import traceback
            traceback.print_exc()
    
    def _show_incoming_call_dialog(self, call_id: str, caller_id: str, caller_name: str):
        """Show incoming call dialog with ringtone"""
        # Create ringtone (using ft.Audio)
        # Note: You may need to add a ringtone file to your assets
        try:
            # Try to play ringtone (if you have a sound file)
            # For now, we'll use a simple approach with ft.Audio
            # You can add a ringtone.wav file to your assets folder
            self.call_ringtone = ft.Audio(
                src="https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3",  # Placeholder - replace with actual ringtone
                autoplay=True,
                volume=1.0,
                balance=0.0
            )
            # Add to page overlay (if supported)
            # Note: Flet Audio may need to be added differently
        except Exception as e:
            print(f"Could not setup ringtone: {e}")
            # Continue without ringtone
        
        # Create dialog
        self.incoming_call_dialog = ft.AlertDialog(
            title=ft.Text("Incoming Video Call"),
            content=ft.Column([
                ft.Text(f"{caller_name} is calling...", size=18, weight=ft.FontWeight.BOLD),
                ft.ProgressRing()
            ], tight=True, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            actions=[
                ft.ElevatedButton(
                    text="Accept",
                    bgcolor=ft.colors.GREEN,
                    color=ft.colors.WHITE,
                    on_click=lambda e: self.page.run_task(
                        self._accept_incoming_call,
                        call_id,
                        caller_id
                    )
                ),
                ft.ElevatedButton(
                    text="Reject",
                    bgcolor=ft.colors.RED,
                    color=ft.colors.WHITE,
                    on_click=lambda e: self.page.run_task(
                        self._reject_incoming_call,
                        call_id,
                        caller_id,
                        "rejected"
                    )
                )
            ],
            modal=True
        )
        
        self.page.dialog = self.incoming_call_dialog
        self.incoming_call_dialog.open = True
        self.page.update()
        
        # Setup timeout (30 seconds) using asyncio for incoming call
        call_id_for_timeout = call_id  # Capture call_id for closure
        async def timeout_task():
            await asyncio.sleep(30)  # Wait 30 seconds
            if self.current_call_id == call_id_for_timeout:  # Still waiting for this call
                await self._handle_call_timeout()
        
        self.call_timeout_timer_task = asyncio.create_task(timeout_task())
    
    async def _accept_incoming_call(self, call_id: str, caller_id: str):
        """Accept incoming call"""
        try:
            # Stop ringtone
            if self.call_ringtone:
                # Stop audio if possible
                self.call_ringtone = None
            
            # Close dialog
            if self.incoming_call_dialog:
                self.incoming_call_dialog.open = False
                self.incoming_call_dialog = None
                self.page.dialog = None
                self.page.update()
            
            # Cancel timeout
            if self.call_timeout_timer:
                self.call_timeout_timer.cancel()
                self.call_timeout_timer = None
            
            # Send accept message
            await self.ws_client.send_call_accept(
                call_id=call_id,
                caller_id=caller_id,
                callee_id=str(self.user.id)
            )
            
            # Open video call page
            await self._open_video_call_page(call_id, False)
        
        except Exception as e:
            print(f"Error accepting call: {e}")
            import traceback
            traceback.print_exc()
    
    async def _reject_incoming_call(self, call_id: str, caller_id: str, reason: str):
        """Reject incoming call"""
        try:
            # Stop ringtone
            if self.call_ringtone:
                self.call_ringtone = None
            
            # Close dialog
            if self.incoming_call_dialog:
                self.incoming_call_dialog.open = False
                self.incoming_call_dialog = None
                self.page.dialog = None
                self.page.update()
            
            # Cancel timeout
            if self.call_timeout_timer:
                self.call_timeout_timer.cancel()
                self.call_timeout_timer = None
            
            # Send reject message
            await self.ws_client.send_call_reject(
                call_id=call_id,
                caller_id=caller_id,
                callee_id=str(self.user.id),
                reason=reason
            )
            
            self.current_call_id = None
        
        except Exception as e:
            print(f"Error rejecting call: {e}")
            import traceback
            traceback.print_exc()
    
    async def _handle_call_timeout(self):
        """Handle call timeout (30 seconds)"""
        if self.current_call_id:
            # End the call
            await self.ws_client.send_call_end(
                call_id=self.current_call_id,
                ended_by=str(self.user.id)
            )
        
        # Stop ringtone
        if self.call_ringtone:
            self.call_ringtone = None
        
        # Close dialog/overlay
        await self._close_calling_overlay()
        if self.incoming_call_dialog:
            self.incoming_call_dialog.open = False
            self.incoming_call_dialog = None
            self.page.dialog = None
            self.page.update()
        
        self.current_call_id = None
        
        self.page.snack_bar = ft.SnackBar(
            content=ft.Text("Call timeout - no answer"),
            bgcolor=config.ERROR_COLOR
        )
        self.page.snack_bar.open = True
        self.page.update()
    
    async def _open_video_call_page(self, call_id: str, is_caller: bool):
        """Open video call page"""
        try:
            # Get remote user info
            remote_user_id = None
            remote_username = "Unknown"
            
            if self.current_conversation:
                for participant in self.current_conversation.participants:
                    if str(participant.user_id) != str(self.user.id):
                        remote_user_id = str(participant.user_id)
                        remote_username = participant.display_name or participant.username
                        break
            
            if not remote_user_id:
                self.page.snack_bar = ft.SnackBar(
                    content=ft.Text("Could not find remote user"),
                    bgcolor=config.ERROR_COLOR
                )
                self.page.snack_bar.open = True
                self.page.update()
                return
            
            if not VIDEO_CALL_AVAILABLE or not VideoCallPage:
                self.page.snack_bar = ft.SnackBar(
                    content=ft.Text("Video call not available. Please install: pip install opencv-python aiortc"),
                    bgcolor=config.ERROR_COLOR
                )
                self.page.snack_bar.open = True
                self.page.update()
                return
            
            self.current_call_page = VideoCallPage(
                page=self.page,
                call_id=call_id,
                local_user_id=str(self.user.id),
                remote_user_id=remote_user_id,
                remote_username=remote_username,
                is_caller=is_caller,
                on_call_end=self._close_video_call_page,
                ws_client=self.ws_client
            )
            
            # Replace main screen with video call page
            self.page.controls.clear()
            self.page.add(self.current_call_page)
            self.page.update()
        
        except Exception as e:
            print(f"Error opening video call page: {e}")
            import traceback
            traceback.print_exc()
    
    def _close_video_call_page(self):
        """Close video call page and return to main screen"""
        try:
            # Cleanup call page
            if self.current_call_page:
                self.page.run_task(self.current_call_page._cleanup)
                self.current_call_page = None
            
            # Clear call state
            self.current_call_id = None
            
            # Restore main screen
            self.page.controls.clear()
            self.page.add(self)
            self.page.update()
        
        except Exception as e:
            print(f"Error closing video call page: {e}")
            import traceback
            traceback.print_exc()
    
    def handle_logout(self):
        """Handle logout"""
        print("Logging out...")
        # Disconnect WebSocket
        if self.ws_client:
            self.page.run_task(self.ws_client.disconnect)
        
        # Clear storage and logout
        from ..utils.storage import storage
        storage.logout()
        
        # Call logout callback
        self.on_logout()

