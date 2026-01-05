import flet as ft

from .config import config
from .api.client import APIClient, get_api_client
from .utils.storage import storage
from .utils.app_dirs import cleanup_old_recordings, get_recordings_stats
from .screens import LoginScreen, RegisterScreen, MainChatScreen


class ChatApp:
    def __init__(self, page: ft.Page):
        self.page = page
        self.current_screen = None
        
        self.page.title = config.APP_NAME
        self.page.window.width = config.WINDOW_WIDTH
        self.page.window.height = config.WINDOW_HEIGHT
        self.page.window.min_width = config.WINDOW_MIN_WIDTH
        self.page.window.min_height = config.WINDOW_MIN_HEIGHT
        self.page.theme_mode = ft.ThemeMode.LIGHT
        self.page.padding = 0
        self.page.spacing = 0
        self.page.scroll = None
        
        self.api_client = get_api_client()
        self.initialize_app()
    
    def initialize_app(self):
        print("Initializing app...")
        
        try:
            stats = get_recordings_stats()
            if stats['count'] > 0:
                print(f"Found {stats['count']} voice recordings ({stats['total_size_mb']} MB)")
                deleted = cleanup_old_recordings(max_age_hours=24)
                if deleted > 0:
                    print(f"Cleaned up {deleted} old recording(s)")
        except Exception as e:
            print(f"Cleanup failed: {e}")
        
        token = storage.get_token()
        print(f"Token found: {bool(token)}")
        
        if token:
            print("Trying to restore session...")
            self.api_client.set_token(token)
            self.page.run_task(self.try_restore_session)
        else:
            print("Showing login screen...")
            self.show_login_screen()
    
    async def try_restore_session(self):
        self.show_loading("Restoring session...")
 
        try:
            print("Verifying token with backend...")
            user = await self.api_client.get_current_user()
            
            print(f"Token valid! User: {user.username}")
            self.show_main_screen(storage.get_token(), user)
        
        except Exception as e:
            print(f"Session restore failed: {e}")
            storage.logout()    
            self.api_client.token = None
            self.show_login_screen()
    
    def show_loading(self, message: str):
        print(f"Loading: {message}")
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
        print("Creating login screen...")
        self.page.controls.clear()
        
        try:
            login_screen = LoginScreen(
                page=self.page,
                on_login_success=self.handle_login_success,
                on_go_to_register=self.show_register_screen
            )
            print("Login screen created")
            
            self.current_screen = login_screen
            self.page.add(login_screen)
            print("Login screen added to page")
            self.page.update()
            print("Page updated")
        except Exception as e:
            print(f"Error creating login screen: {e}")
            import traceback
            traceback.print_exc()
    
    def show_register_screen(self):
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
        print(f"Login successful: {user.username}")
        self.show_main_screen(token, user)
    
    def handle_register_success(self):
        print("Registration successful, showing login")
        self.show_login_screen()
    
    def show_main_screen(self, token: str, user):
        print(f"Showing main screen for user: {user.username}")
        self.page.controls.clear()
        
        try:
            main_screen = MainChatScreen(
                page=self.page,
                user=user,
                token=token,
                on_logout=self.handle_logout
            )
            print("Main screen created")
            
            self.current_screen = main_screen
            self.page.add(main_screen)
            print(f"Main screen added (expand={getattr(main_screen, 'expand', None)})")
            self.page.update()
            print("Page updated with main screen")
        except Exception as e:
            print(f"Error showing main screen: {e}")
            import traceback
            traceback.print_exc()
    
    def handle_logout(self):
        print("Logging out...")
        storage.logout()
        self.api_client.token = None
        self.show_login_screen()


def main(page: ft.Page):
    print("=" * 50)
    print("Starting Chat App...")
    print("=" * 50)
    try:
        app = ChatApp(page)
        print("App initialized successfully")
    except Exception as e:
        print(f"Fatal error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    ft.app(target=main)
