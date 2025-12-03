"""
Message Status Component
Displays message delivery/read status icons (✓ ✓✓ ✓✓✓)
"""
import flet as ft
from datetime import datetime, timedelta
from typing import Optional


class MessageStatus(ft.UserControl):
    """
    Display message status icons
    
    States:
    - ✓ Sent (grey) - Message sent successfully
    - ✓✓ Delivered (grey) - Message delivered to recipient
    - ✓✓ Read (blue) - Message read by recipient
    """
    
    def __init__(self, 
                 created_at,  # str or datetime
                 delivered_at: Optional[datetime] = None,
                 read_at: Optional[datetime] = None):
        """
        Initialize Message Status
        
        Args:
            created_at: When message was created/sent (str or datetime)
            delivered_at: When message was delivered (optional)
            read_at: When message was read (optional)
        """
        super().__init__()
        # Parse created_at if string
        if isinstance(created_at, str):
            try:
                self.created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            except:
                self.created_at = datetime.now()
        else:
            self.created_at = created_at
        self.delivered_at = delivered_at
        self.read_at = read_at
    
    def build(self):
        """Build status indicator"""
        if self.read_at:
            # Read - Blue double check marks
            return ft.Icon(
                ft.icons.DONE_ALL,
                size=14,
                color=ft.colors.BLUE_600,
                tooltip=f"Read at {self._format_timestamp(self.read_at)}"
            )
        elif self.delivered_at:
            # Delivered - Grey double check marks
            return ft.Icon(
                ft.icons.DONE_ALL,
                size=14,
                color=ft.colors.GREY_500,
                tooltip=f"Delivered at {self._format_timestamp(self.delivered_at)}"
            )
        else:
            # Sent - Grey single check mark
            return ft.Icon(
                ft.icons.DONE,
                size=14,
                color=ft.colors.GREY_500,
                tooltip=f"Sent at {self._format_timestamp(self.created_at)}"
            )
    
    def update_status(self, delivered_at: Optional[datetime] = None, read_at: Optional[datetime] = None):
        """
        Update message status
        
        Args:
            delivered_at: New delivered timestamp
            read_at: New read timestamp
        """
        if delivered_at:
            self.delivered_at = delivered_at
        if read_at:
            self.read_at = read_at
        self.update()
    
    @staticmethod
    def _format_timestamp(dt) -> str:
        """
        Format timestamp for display
        
        Args:
            dt: Datetime object or string
            
        Returns:
            Formatted string like "14:30"
        """
        # Handle string timestamps
        if isinstance(dt, str):
            try:
                dt = datetime.fromisoformat(dt.replace('Z', '+00:00'))
            except:
                return dt  # Return as-is if can't parse
        
        return dt.strftime("%H:%M")


class MessageStatusWithTime(ft.UserControl):
    """
    Message status with timestamp display
    Shows both the time and status icon
    """
    
    def __init__(self,
                 created_at,  # str or datetime
                 delivered_at: Optional[datetime] = None,
                 read_at: Optional[datetime] = None):
        super().__init__()
        # Parse created_at if string
        if isinstance(created_at, str):
            try:
                self.created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            except:
                self.created_at = datetime.now()
        else:
            self.created_at = created_at
        self.delivered_at = delivered_at
        self.read_at = read_at
        self.status_icon = None
    
    def build(self):
        """Build status with time"""
        # Status icon
        self.status_icon = MessageStatus(
            created_at=self.created_at,
            delivered_at=self.delivered_at,
            read_at=self.read_at
        )
        
        # Time display
        time_text = ft.Text(
            self._format_time(self.created_at),
            size=10,
            color=ft.colors.GREY_600
        )
        
        return ft.Row(
            controls=[
                time_text,
                self.status_icon
            ],
            spacing=4,
            alignment=ft.MainAxisAlignment.END
        )
    
    def update_status(self, delivered_at: Optional[datetime] = None, read_at: Optional[datetime] = None):
        """Update status"""
        if delivered_at:
            self.delivered_at = delivered_at
        if read_at:
            self.read_at = read_at
        
        if self.status_icon:
            self.status_icon.update_status(delivered_at, read_at)
    
    @staticmethod
    def _format_time(dt) -> str:
        """Format time for display"""
        # Handle string timestamps
        if isinstance(dt, str):
            try:
                dt = datetime.fromisoformat(dt.replace('Z', '+00:00'))
            except:
                return dt  # Return as-is if can't parse
        
        now = datetime.now()
        
        if dt.date() == now.date():
            # Today - show time only
            return dt.strftime("%H:%M")
        elif dt.date() == (now.date() - timedelta(days=1)):
            # Yesterday
            return "Yesterday"
        else:
            # Older - show date
            return dt.strftime("%d/%m/%y")

