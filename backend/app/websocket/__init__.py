"""
WebSocket module for real-time messaging
"""
from .manager import ConnectionManager

# Singleton instance
manager = ConnectionManager()

__all__ = ["manager", "ConnectionManager"]

