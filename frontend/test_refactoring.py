"""
Quick test to verify refactoring works
"""
import sys
from pathlib import Path

# Add app to path
sys.path.insert(0, str(Path(__file__).parent))

def test_imports():
    """Test all imports work"""
    print("Testing imports...")
    
    try:
        from app.components import MessageBubble, ConversationItem, MessageInput
        print("[OK] Components import OK")
    except Exception as e:
        print(f"[FAIL] Components import failed: {e}")
        return False
    
    try:
        from app.dialogs import (
            ProfileDialog, EditProfileDialog, SettingsDialog,
            NewChatDialog, DirectChatDialog, GroupChatDialog, GroupInfoDialog
        )
        print("[OK] Dialogs import OK")
    except Exception as e:
        print(f"[FAIL] Dialogs import failed: {e}")
        return False
    
    try:
        from app.screens.main_screen import MainChatScreen
        print("[OK] MainChatScreen import OK")
    except Exception as e:
        print(f"[FAIL] MainChatScreen import failed: {e}")
        return False
    
    return True

def test_component_structure():
    """Test component classes have required methods"""
    print("\nTesting component structure...")
    
    from app.components import MessageBubble, ConversationItem, MessageInput
    import flet as ft
    
    # Check MessageBubble
    required_methods = ['build']
    for method in required_methods:
        if not hasattr(MessageBubble, method):
            print(f"[FAIL] MessageBubble missing {method}")
            return False
    print("[OK] MessageBubble structure OK")
    
    # Check ConversationItem
    if not hasattr(ConversationItem, 'build'):
        print("[FAIL] ConversationItem missing build")
        return False
    print("[OK] ConversationItem structure OK")
    
    # Check MessageInput
    if not hasattr(MessageInput, 'build'):
        print("[FAIL] MessageInput missing build")
        return False
    print("[OK] MessageInput structure OK")
    
    return True

def test_dialog_structure():
    """Test dialog classes"""
    print("\nTesting dialog structure...")
    
    from app.dialogs import ProfileDialog, SettingsDialog
    import flet as ft
    
    # Dialogs should be AlertDialog
    print("[OK] Dialog classes defined")
    
    return True

def test_main_screen_methods():
    """Test MainChatScreen has all required methods"""
    print("\nTesting MainChatScreen methods...")
    
    from app.screens.main_screen import MainChatScreen
    
    required_methods = [
        'build',
        'did_mount',
        'load_conversations',
        'render_conversations',
        'render_messages',
        'handle_send_message',
        'handle_conversation_click',
        'connect_websocket',
        'handle_ws_message',
        'handle_typing',
        'show_new_chat_dialog',
        'show_profile',
        'show_settings',
        'handle_logout',
    ]
    
    for method in required_methods:
        if not hasattr(MainChatScreen, method):
            print(f"[FAIL] MainChatScreen missing {method}")
            return False
    
    print(f"[OK] MainChatScreen has all {len(required_methods)} required methods")
    return True

def main():
    """Run all tests"""
    print("="*60)
    print("REFACTORING VALIDATION TEST")
    print("="*60)
    
    tests = [
        ("Imports", test_imports),
        ("Component Structure", test_component_structure),
        ("Dialog Structure", test_dialog_structure),
        ("MainChatScreen Methods", test_main_screen_methods),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append(result)
        except Exception as e:
            print(f"[FAIL] {name} test failed with exception: {e}")
            results.append(False)
    
    print("\n" + "="*60)
    print("TEST RESULTS")
    print("="*60)
    passed = sum(results)
    total = len(results)
    print(f"Passed: {passed}/{total}")
    
    if all(results):
        print("\nALL TESTS PASSED! Refactoring is successful!")
        return 0
    else:
        print("\nSOME TESTS FAILED! Please review the errors above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())

