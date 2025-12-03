"""
Flet Frontend - Chat App
Desktop application entry point
"""
import flet as ft

from .config import config
from .api.client import APIClient, get_api_client
from .utils.storage import storage
from .utils.app_dirs import cleanup_old_recordings, get_recordings_stats
from .screens import LoginScreen, RegisterScreen, MainChatScreen


class ChatApp:
    """Main chat application"""
    
    def __init__(self, page: ft.Page):
        """Initialize app"""
        self.page = page
        self.current_screen = None
        
        # Configure page
        self.page.title = config.APP_NAME
        self.page.window.width = config.WINDOW_WIDTH
        self.page.window.height = config.WINDOW_HEIGHT
        self.page.window.min_width = config.WINDOW_MIN_WIDTH
        self.page.window.min_height = config.WINDOW_MIN_HEIGHT
        self.page.theme_mode = ft.ThemeMode.LIGHT
        self.page.padding = 0
        self.page.spacing = 0
        self.page.scroll = None  # No page-level scrolling
        
        # Initialize API client
        self.api_client = get_api_client()
        
        # Check if already logged in and try to restore
        self.initialize_app()
    
    def initialize_app(self):
        """Initialize the app - check for existing session"""
        print("🚀 Initializing app...")
        
        # Cleanup old voice recordings (older than 24 hours)
        try:
            stats = get_recordings_stats()
            if stats['count'] > 0:
                print(f"📊 Found {stats['count']} voice recordings ({stats['total_size_mb']} MB)")
                deleted = cleanup_old_recordings(max_age_hours=24)
                if deleted > 0:
                    print(f"🧹 Cleaned up {deleted} old recording(s)")
        except Exception as e:
            print(f"⚠️ Cleanup failed: {e}")
        
        token = storage.get_token()
        print(f"📝 Token found: {bool(token)}")
        
        if token:
            # Try to restore session
            print("🔄 Trying to restore session...")
            self.api_client.set_token(token)
            # Use page.run_task for async operations in Flet
            self.page.run_task(self.try_restore_session)
        else:
            # Show login screen
            print("📱 Showing login screen...")
            self.show_login_screen()
    
    async def try_restore_session(self):
        """Try to restore previous session"""
        # Show loading indicator
        self.show_loading("Restoring session...")
        
        try:
            print("🔍 Verifying token with backend...")
            # Verify token is still valid
            user = await self.api_client.get_current_user()
            
            print(f"✅ Token valid! User: {user.username}")
            # Token valid, go to main screen
            self.show_main_screen(storage.get_token(), user)
        
        except Exception as e:
            print(f"❌ Session restore failed: {e}")
            # Token invalid, clear and show login
            storage.logout()
            self.api_client.token = None
            self.show_login_screen()
    
    def show_loading(self, message: str):
        """Show loading screen"""
        print(f"⏳ Loading: {message}")
        self.page.controls.clear()
        self.page.add(
            ft.Container(
                content=ft.Column([
                    ft.ProgressRing(),
                    ft.Text(message, size=16)
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                alignment=ft.MainAxisAlignment.CENTER,
                ),
                alignment=ft.alignment.center,
                expand=True
            )
        )
        self.page.update()
    
    def show_login_screen(self):
        """Show login screen"""
        print("🔓 Creating login screen...")
        self.page.controls.clear()
        
        try:
            login_screen = LoginScreen(
                page=self.page,
                on_login_success=self.handle_login_success,
                on_go_to_register=self.show_register_screen
            )
            print("✅ Login screen created")
            
            self.current_screen = login_screen
            self.page.add(login_screen)
            print("✅ Login screen added to page")
            self.page.update()
            print("✅ Page updated")
        except Exception as e:
            print(f"❌ Error creating login screen: {e}")
            import traceback
            traceback.print_exc()
    
    def show_register_screen(self):
        """Show register screen"""
        self.page.controls.clear()
        
        register_screen = RegisterScreen(
            page=self.page,
            on_register_success=self.handle_register_success,
            on_go_to_login=self.show_login_screen
        )
        
        self.current_screen = register_screen
        self.page.add(register_screen)
        self.page.update()
    
    def handle_login_success(self, token: str, user):
        """Handle successful login"""
        print(f"Login successful: {user.username}")
        self.show_main_screen(token, user)
    
    def handle_register_success(self):
        """Handle successful registration"""
        print("Registration successful, showing login")
        self.show_login_screen()
    
    def show_main_screen(self, token: str, user):
        """Show main chat screen"""
        print(f"📺 Showing main screen for user: {user.username}")
        self.page.controls.clear()
        
        try:
            main_screen = MainChatScreen(
                page=self.page,
                user=user,
                token=token,
                on_logout=self.handle_logout
            )
            print("✅ Main screen created")
            
            # Add with expand to fill the page
            self.current_screen = main_screen
            self.page.add(main_screen)
            print(f"✅ Main screen added (expand={getattr(main_screen, 'expand', None)})")
            self.page.update()
            print("✅ Page updated with main screen")
        except Exception as e:
            print(f"❌ Error showing main screen: {e}")
            import traceback
            traceback.print_exc()
    
    def handle_logout(self):
        """Handle logout"""
        print("Logging out...")
        storage.logout()
        self.api_client.token = None
        self.show_login_screen()


def main(page: ft.Page):
    """Main Flet app entry point"""
    print("=" * 50)
    print("🎯 Starting Chat App...")
    print("=" * 50)
    try:
        app = ChatApp(page)
        print("✅ App initialized successfully")
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()


# Run app
if __name__ == "__main__":
    # For desktop mode (recommended)
    ft.app(target=main)
    
    # For web mode (Docker) - uncomment line below and comment line above
    # ft.app(target=main, port=8550, view=ft.AppView.WEB_BROWSER)
