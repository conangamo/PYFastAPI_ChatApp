"""
Formatting utilities
"""
from datetime import datetime
from typing import Optional


def format_timestamp(timestamp: str, include_date: bool = False) -> str:
    """
    Format ISO timestamp to readable format
    
    Args:
        timestamp: ISO format timestamp
        include_date: Whether to include date
        
    Returns:
        Formatted string like "10:30 AM" or "Oct 19, 10:30 AM"
    """
    try:
        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        
        # Convert to local time
        local_dt = dt.astimezone()
        
        # Check if today
        now = datetime.now()
        is_today = (local_dt.date() == now.date())
        
        if is_today and not include_date:
            return local_dt.strftime("%I:%M %p")
        elif is_today:
            return local_dt.strftime("Today, %I:%M %p")
        else:
            # Check if this year
            is_this_year = (local_dt.year == now.year)
            if is_this_year:
                return local_dt.strftime("%b %d, %I:%M %p")
            else:
                return local_dt.strftime("%b %d %Y, %I:%M %p")
    except Exception as e:
        print(f"Error formatting timestamp: {e}")
        return timestamp


def format_file_size(size_bytes: int) -> str:
    """
    Format file size in bytes to readable format
    
    Args:
        size_bytes: File size in bytes
        
    Returns:
        Formatted string like "1.5 MB" or "350 KB"
    """
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        kb = size_bytes / 1024
        return f"{kb:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        mb = size_bytes / (1024 * 1024)
        return f"{mb:.1f} MB"
    else:
        gb = size_bytes / (1024 * 1024 * 1024)
        return f"{gb:.2f} GB"


def truncate_text(text: str, max_length: int = 50) -> str:
    """
    Truncate text to max length
    
    Args:
        text: Text to truncate
        max_length: Maximum length
        
    Returns:
        Truncated text with "..." if needed
    """
    if len(text) <= max_length:
        return text
    return text[:max_length - 3] + "..."


def get_file_icon(file_type: Optional[str]) -> str:
    """
    Get emoji icon for file type
    
    Args:
        file_type: MIME type or file extension
        
    Returns:
        Emoji icon
    """
    if not file_type:
        return "📄"
    
    file_type = file_type.lower()
    
    if "image" in file_type or any(ext in file_type for ext in [".jpg", ".png", ".gif"]):
        return "🖼️"
    elif "video" in file_type or ".mp4" in file_type:
        return "🎥"
    elif "audio" in file_type or ".mp3" in file_type:
        return "🎵"
    elif "pdf" in file_type:
        return "📕"
    elif any(word in file_type for word in ["document", "word", ".doc"]):
        return "📘"
    elif any(word in file_type for word in ["spreadsheet", "excel", ".xls"]):
        return "📊"
    elif "zip" in file_type or "rar" in file_type:
        return "📦"
    else:
        return "📄"

