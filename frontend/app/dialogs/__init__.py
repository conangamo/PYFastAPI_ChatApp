"""
Dialog components
"""
from .profile_dialog import ProfileDialog, EditProfileDialog
from .settings_dialog import SettingsDialog
from .chat_dialogs import NewChatDialog, DirectChatDialog, GroupChatDialog, GroupInfoDialog
from .friend_chat_dialog import FriendChatDialog
from .friend_requests_dialog import FriendRequestsDialog
from .group_creation_dialog import GroupCreationDialog
from .message_dialogs import EditMessageDialog, DeleteMessageDialog
from .conversation_settings_dialog import ConversationSettingsDialog
from .add_member_dialog import AddMemberDialog

__all__ = [
    "ProfileDialog",
    "EditProfileDialog",
    "SettingsDialog",
    "NewChatDialog",
    "DirectChatDialog",
    "GroupChatDialog",
    "GroupInfoDialog",
    "FriendChatDialog",
    "FriendRequestsDialog",
    "GroupCreationDialog",
    "EditMessageDialog",
    "DeleteMessageDialog",
    "ConversationSettingsDialog",
    "AddMemberDialog",
]

