"""
Local storage for persisting data
"""
import json
from typing import Optional, Any
from pathlib import Path


class Storage:
    """Simple file-based storage for token and user data"""
    
    def __init__(self, storage_file: str = ".chat_app_storage.json"):
        """Initialize storage"""
        self.storage_file = Path.home() / storage_file
        self._data = self._load()
    
    def _load(self) -> dict:
        """Load data from file"""
        if self.storage_file.exists():
            try:
                with open(self.storage_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading storage: {e}")
                return {}
        return {}
    
    def _save(self):
        """Save data to file"""
        try:
            with open(self.storage_file, 'w', encoding='utf-8') as f:
                json.dump(self._data, f, indent=2)
        except Exception as e:
            print(f"Error saving storage: {e}")
    
    def set(self, key: str, value: Any):
        """Store a value"""
        self._data[key] = value
        self._save()
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a value"""
        return self._data.get(key, default)
    
    def remove(self, key: str):
        """Remove a value"""
        if key in self._data:
            del self._data[key]
            self._save()
    
    def clear(self):
        """Clear all data"""
        self._data = {}
        self._save()
    
    # Convenience methods for common keys
    def set_token(self, token: str):
        """Store authentication token"""
        self.set("auth_token", token)
    
    def get_token(self) -> Optional[str]:
        """Get authentication token"""
        return self.get("auth_token")
    
    def clear_token(self):
        """Remove authentication token"""
        self.remove("auth_token")
    
    def set_user(self, user: dict):
        """Store current user data"""
        self.set("current_user", user)
    
    def get_user(self) -> Optional[dict]:
        """Get current user data"""
        return self.get("current_user")
    
    def clear_user(self):
        """Remove current user data"""
        self.remove("current_user")
    
    def logout(self):
        """Clear all auth data"""
        self.clear_token()
        self.clear_user()


# Global storage instance
storage = Storage()

