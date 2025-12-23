import json
from typing import Optional, Any
from pathlib import Path


class Storage:
    def __init__(self, storage_file: str = ".chat_app_storage.json"):
        self.storage_file = Path.home() / storage_file
        self._data = self._load()
    
    def _load(self) -> dict:
        if self.storage_file.exists():
            try:
                with open(self.storage_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading storage: {e}")
                return {}
        return {}
    
    def _save(self):
        try:
            with open(self.storage_file, 'w', encoding='utf-8') as f:
                json.dump(self._data, f, indent=2)
        except Exception as e:
            print(f"Error saving storage: {e}")
    
    def set(self, key: str, value: Any):
        self._data[key] = value
        self._save()
    
    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)
    
    def remove(self, key: str):
        if key in self._data:
            del self._data[key]
            self._save()
    
    def clear(self):
        self._data = {}
        self._save()
    
    def set_token(self, token: str):
        self.set("auth_token", token)
    
    def get_token(self) -> Optional[str]:
        return self.get("auth_token")
    
    def clear_token(self):
        self.remove("auth_token")
    
    def set_user(self, user: dict):
        self.set("current_user", user)
    
    def get_user(self) -> Optional[dict]:
        return self.get("current_user")
    
    def clear_user(self):
        self.remove("current_user")
    
    def logout(self):
        self.clear_token()
        self.clear_user()


storage = Storage()

