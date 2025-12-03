"""
Clear stored token and user data
Run this if you want to logout/start fresh
"""
from pathlib import Path
import json

storage_file = Path.home() / ".chat_app_storage.json"

if storage_file.exists():
    print(f"📂 Found storage file: {storage_file}")
    
    # Read current data
    with open(storage_file, 'r') as f:
        data = json.load(f)
    
    print(f"📝 Current data: {list(data.keys())}")
    
    # Clear
    storage_file.unlink()
    print("✅ Storage cleared!")
else:
    print("ℹ️  No storage file found")

print("\n✨ Now run the app again with: python -m app.main")

