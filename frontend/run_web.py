"""
Web Mode for Multi-User Testing
Chạy file này khi cần test 2 users trên cùng 1 máy
"""
import flet as ft
from app.main import main

if __name__ == "__main__":
    print("=" * 60)
    print("🌐 WEB MODE - Multi-User Testing")
    print("=" * 60)
    print("")
    print("📝 Hướng dẫn:")
    print("  1. Mở browser tab 1: http://localhost:8550")
    print("     → Login User A (vd: alice/alice123)")
    print("")
    print("  2. Mở browser tab 2 (Incognito): http://localhost:8550")
    print("     → Login User B (vd: bob/bob123)")
    print("")
    print("  3. Test chat giữa 2 users!")
    print("")
    print("💡 Tip: Dùng Incognito cho tab 2 (Ctrl+Shift+N)")
    print("=" * 60)
    print("🚀 Server đang chạy tại: http://localhost:8550")
    print("   Nhấn Ctrl+C để thoát")
    print("=" * 60)
    print("")
    
    # Chạy web mode
    ft.app(target=main, port=8550, view=ft.AppView.WEB_BROWSER)

