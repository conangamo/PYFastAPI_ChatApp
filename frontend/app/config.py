"""
Configuration for Flet Chat App
"""
import os
from dataclasses import dataclass


@dataclass
class Config:
    """App configuration"""
    
    # Backend URLs
    BACKEND_URL: str = os.getenv("BACKEND_URL", "http://localhost:8000")
    BACKEND_WS_URL: str = os.getenv("BACKEND_WS_URL", "ws://localhost:8000")
    
    # API endpoints
    API_BASE: str = f"{BACKEND_URL}/api"
    WS_ENDPOINT: str = f"{BACKEND_WS_URL}/api/ws"
    
    # App settings
    APP_NAME: str = "Chat App"
    APP_VERSION: str = "1.0.0"
    
    # Window settings
    WINDOW_WIDTH: int = 1200
    WINDOW_HEIGHT: int = 800
    WINDOW_MIN_WIDTH: int = 900
    WINDOW_MIN_HEIGHT: int = 600
    
    # UI Colors (Material Design)
    PRIMARY_COLOR: str = "#1976D2"
    SECONDARY_COLOR: str = "#DC004E"
    SUCCESS_COLOR: str = "#4CAF50"
    ERROR_COLOR: str = "#F44336"
    WARNING_COLOR: str = "#FF9800"
    INFO_COLOR: str = "#2196F3"
    
    BACKGROUND_COLOR: str = "#F5F5F5"
    SURFACE_COLOR: str = "#FFFFFF"
    TEXT_PRIMARY: str = "#212121"
    TEXT_SECONDARY: str = "#757575"
    DIVIDER_COLOR: str = "#E0E0E0"
    BORDER_COLOR: str = "#E0E0E0"  # Border color for cards and containers
    
    # Message colors
    MESSAGE_SENT_BG: str = "#E3F2FD"      # Light blue
    MESSAGE_RECEIVED_BG: str = "#F5F5F5"   # Light gray
    
    # Storage keys
    STORAGE_TOKEN_KEY: str = "auth_token"
    STORAGE_USER_KEY: str = "current_user"
    
    # Message settings
    MAX_MESSAGE_LENGTH: int = 5000
    MESSAGES_PER_PAGE: int = 50
    
    # File upload
    MAX_FILE_SIZE_MB: int = 100
    ALLOWED_EXTENSIONS: list = None
    
    def __post_init__(self):
        if self.ALLOWED_EXTENSIONS is None:
            self.ALLOWED_EXTENSIONS = [
                # Images
                ".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp",
                # Documents
                ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".txt", ".csv",
                # Audio
                ".mp3", ".wav", ".ogg", ".webm",
                # Video
                ".mp4", ".mpeg", ".mov", ".avi",
                # Archives
                ".zip", ".rar", ".7z"
            ]


# Global config instance
config = Config()

