"""
App Data Directory Management
Provides directories for storing temporary recordings in project folder
"""
from pathlib import Path
import time
import os


class AppDirectories:
    """
    Manage app-specific directories in project folder
    
    Uses: {project_root}/ChatApp/recordings/
    This avoids using C: drive and keeps files with project
    """
    
    APP_NAME = "ChatApp"
    
    def __init__(self):
        """Initialize app directories"""
        self._init_directories()
    
    def _init_directories(self):
        """Create all necessary app directories in project folder"""
        # Get project root (chat_V4/)
        # Current file: frontend/app/utils/app_dirs.py
        # Project root: ../../../../
        current_file = Path(__file__)
        project_root = current_file.parent.parent.parent.parent  # Go up to chat_V4/
        
        # Create ChatApp directory in project root
        app_dir = project_root / self.APP_NAME
        
        # Main directories (all in project)
        self.data_dir = app_dir / "data"
        self.cache_dir = app_dir / "cache"
        self.log_dir = app_dir / "logs"
        
        # Subdirectories for voice messages
        self.recordings_dir = app_dir / "recordings"
        self.pending_uploads_dir = self.cache_dir / "pending_uploads"
        
        # Create all directories
        for directory in [
            self.data_dir,
            self.cache_dir,
            self.log_dir,
            self.recordings_dir,
            self.pending_uploads_dir
        ]:
            directory.mkdir(parents=True, exist_ok=True)
        
        print(f"📁 App directories initialized (in project folder):")
        print(f"   Project root: {project_root}")
        print(f"   App directory: {app_dir}")
        print(f"   Recordings: {self.recordings_dir}")
        print(f"   Cache: {self.cache_dir}")
    
    def get_recordings_dir(self) -> Path:
        """
        Get recordings directory for voice messages
        
        Returns:
            Path: Recordings directory path
        """
        return self.recordings_dir
    
    def get_pending_uploads_dir(self) -> Path:
        """
        Get pending uploads directory (for retry logic)
        
        Returns:
            Path: Pending uploads directory path
        """
        return self.pending_uploads_dir
    
    def cleanup_old_recordings(self, max_age_hours: int = 24):
        """
        Clean up recordings older than specified age
        
        Args:
            max_age_hours: Maximum age in hours (default 24 hours)
            
        Returns:
            int: Number of files deleted
        """
        deleted_count = 0
        current_time = time.time()
        cutoff_time = current_time - (max_age_hours * 3600)
        
        print(f"🧹 Cleaning up recordings older than {max_age_hours} hours...")
        
        for file in self.recordings_dir.glob("voice_msg_*.wav"):
            try:
                # Check file modification time
                file_mtime = file.stat().st_mtime
                
                if file_mtime < cutoff_time:
                    file_age_hours = (current_time - file_mtime) / 3600
                    file.unlink()
                    deleted_count += 1
                    print(f"   🗑️ Deleted: {file.name} (age: {file_age_hours:.1f}h)")
            
            except Exception as e:
                print(f"   ⚠️ Failed to delete {file.name}: {e}")
        
        print(f"✅ Cleanup complete: {deleted_count} file(s) deleted")
        return deleted_count
    
    def get_recordings_stats(self) -> dict:
        """
        Get statistics about recordings directory
        
        Returns:
            dict: Statistics (count, total_size_mb, oldest_file, newest_file)
        """
        files = list(self.recordings_dir.glob("voice_msg_*.wav"))
        
        if not files:
            return {
                "count": 0,
                "total_size_mb": 0,
                "oldest_file": None,
                "newest_file": None
            }
        
        total_size = sum(f.stat().st_size for f in files)
        oldest = min(files, key=lambda f: f.stat().st_mtime)
        newest = max(files, key=lambda f: f.stat().st_mtime)
        
        return {
            "count": len(files),
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "oldest_file": oldest.name,
            "oldest_age_hours": round((time.time() - oldest.stat().st_mtime) / 3600, 1),
            "newest_file": newest.name,
            "newest_age_hours": round((time.time() - newest.stat().st_mtime) / 3600, 1)
        }
    
    def clear_all_recordings(self):
        """
        Clear all recordings (use with caution!)
        
        Returns:
            int: Number of files deleted
        """
        deleted_count = 0
        
        print("🗑️ Clearing all recordings...")
        
        for file in self.recordings_dir.glob("voice_msg_*.wav"):
            try:
                file.unlink()
                deleted_count += 1
            except Exception as e:
                print(f"   ⚠️ Failed to delete {file.name}: {e}")
        
        print(f"✅ Cleared {deleted_count} recording(s)")
        return deleted_count
    
    def get_storage_info(self) -> dict:
        """
        Get overall storage information
        
        Returns:
            dict: Storage info for all app directories
        """
        def get_dir_size(directory: Path) -> float:
            """Get total size of directory in MB"""
            total = 0
            try:
                for file in directory.rglob("*"):
                    if file.is_file():
                        total += file.stat().st_size
            except:
                pass
            return round(total / (1024 * 1024), 2)
        
        return {
            "data_dir": {
                "path": str(self.data_dir),
                "size_mb": get_dir_size(self.data_dir)
            },
            "cache_dir": {
                "path": str(self.cache_dir),
                "size_mb": get_dir_size(self.cache_dir)
            },
            "recordings": {
                "path": str(self.recordings_dir),
                "size_mb": get_dir_size(self.recordings_dir),
                **self.get_recordings_stats()
            }
        }
    
    def __repr__(self):
        """String representation"""
        return f"AppDirectories(data={self.data_dir}, recordings={self.recordings_dir})"


# Singleton instance
_app_dirs = None

def get_app_directories() -> AppDirectories:
    """
    Get singleton instance of AppDirectories
    
    Returns:
        AppDirectories: App directories manager
    """
    global _app_dirs
    if _app_dirs is None:
        _app_dirs = AppDirectories()
    return _app_dirs


# Convenience functions
def get_recordings_dir() -> Path:
    """Get recordings directory path"""
    return get_app_directories().get_recordings_dir()


def cleanup_old_recordings(max_age_hours: int = 24) -> int:
    """Clean up old recordings"""
    return get_app_directories().cleanup_old_recordings(max_age_hours)


def get_recordings_stats() -> dict:
    """Get recordings statistics"""
    return get_app_directories().get_recordings_stats()


# Example usage
if __name__ == "__main__":
    # Test the module
    app_dirs = get_app_directories()
    
    print("\n📊 App Directories:")
    print(app_dirs)
    
    print("\n📊 Storage Info:")
    import json
    print(json.dumps(app_dirs.get_storage_info(), indent=2))
    
    print("\n📊 Recordings Stats:")
    print(json.dumps(app_dirs.get_recordings_stats(), indent=2))
    
    print("\n🧹 Cleanup old recordings (>24h):")
    deleted = app_dirs.cleanup_old_recordings(max_age_hours=24)
    print(f"Deleted: {deleted} files")

