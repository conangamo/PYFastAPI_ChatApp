# 🎨 Flet Chat App Frontend

Desktop application for real-time chat.

---

## 🚀 Quick Start

### **Option 1: Run Locally (Desktop App)**

```bash
# Install dependencies
cd frontend
pip install -r requirements.txt

# Run app
python -m app.main
```

**Backend must be running**: `http://localhost:8000`

---

### **Option 2: Run with Docker**

```bash
# From project root
docker-compose up frontend
```

Access at: `http://localhost:8550`

---

## 📁 Project Structure

```
frontend/app/
├── main.py                 # App entry point
├── config.py               # Configuration
│
├── api/                    # Backend API client
│   └── client.py           # HTTP requests
│
├── websocket/              # Real-time messaging
│   └── client.py           # WebSocket client
│
├── models/                 # Data models
│   ├── user.py
│   ├── conversation.py
│   └── message.py
│
├── screens/                # UI screens
│   ├── login.py            # Login screen
│   ├── register.py         # Register screen
│   └── main_screen.py      # Main chat screen
│
├── components/             # Reusable UI components
│
└── utils/                  # Utilities
    ├── storage.py          # Local storage
    └── formatters.py       # Date/time formatters
```

---

## ✨ Features

### **Implemented** ✅
- ✅ User registration
- ✅ User login/logout
- ✅ View conversations
- ✅ Send/receive messages
- ✅ Real-time updates (WebSocket)
- ✅ Create new conversations
- ✅ Direct chat (1-1)

### **Future** 🔄
- 🔄 Group chat UI
- 🔄 File upload/download
- 🔄 Typing indicators
- 🔄 Read receipts
- 🔄 User profiles
- 🔄 Search messages
- 🔄 Notifications
- 🔄 Dark mode

---

## 🎨 UI Overview

### **Login Screen**
- Username & password fields
- Link to register
- Error handling

### **Register Screen**
- Username, email, display name, password
- Validation
- Success redirect to login

### **Main Chat Screen**
```
┌────────────────────────────────────────┐
│ Sidebar       │  Chat Area             │
│               │                         │
│ • User Info   │  [Chat Header]          │
│ • New Chat    │                         │
│               │  [Messages...]          │
│ Conversations │                         │
│ • Alice       │                         │
│ • Bob         │                         │
│               │  [Message Input] [Send] │
└────────────────────────────────────────┘
```

**Sidebar**:
- User profile
- Logout button
- "New Chat" button
- Conversations list
- Connection status

**Chat Area**:
- Conversation header
- Messages list (auto-scroll)
- Message input box
- Send button

---

## 🔧 Configuration

Edit `app/config.py`:

```python
BACKEND_URL = "http://localhost:8000"
BACKEND_WS_URL = "ws://localhost:8000"

WINDOW_WIDTH = 1200
WINDOW_HEIGHT = 800

# Colors
PRIMARY_COLOR = "#1976D2"
# ... more settings
```

---

## 📡 API Integration

### **HTTP Endpoints Used**:
- `POST /api/auth/login` - Login
- `POST /api/auth/register` - Register
- `GET /api/users/me` - Get profile
- `GET /api/users` - List users
- `GET /api/conversations` - List conversations
- `POST /api/conversations` - Create conversation
- `GET /api/messages` - Get messages
- `POST /api/messages` - Send message

### **WebSocket**:
- `ws://localhost:8000/api/ws?token={JWT}`
- Receives: `new_message`, `user_online`, `user_offline`
- Sends: `typing` (future)

---

## 💾 Local Storage

Data stored in: `~/.chat_app_storage.json`

**Stores**:
- Authentication token
- User data (cached)

**Auto-cleared on logout**

---

## 🧪 Testing

### **Manual Testing**:

1. **Register new user**:
   - Open app
   - Click "Register"
   - Fill form
   - Submit
   - Should redirect to login

2. **Login**:
   - Enter credentials
   - Should see main screen

3. **Create conversation**:
   - Click "+ New Chat"
   - Select user
   - Should open chat

4. **Send message**:
   - Type message
   - Press Enter or click Send
   - Should appear in chat

5. **Real-time test**:
   - Open 2 instances (2 users)
   - Send message from one
   - Should appear in other instantly

---

## 🐛 Troubleshooting

### **Can't connect to backend**:
```
Error: Connection refused
```
→ Make sure backend is running: `docker-compose up backend`

### **WebSocket not connecting**:
```
Status: 🔴 Offline
```
→ Check backend WebSocket endpoint: `ws://localhost:8000/api/ws`
→ Verify JWT token is valid

### **Login fails**:
```
401 Unauthorized
```
→ Check username/password
→ Register first if new user

### **Messages not appearing**:
→ Check browser console for errors
→ Verify WebSocket is connected (🟢 Connected)
→ Try refreshing conversation list

---

## 🚀 Deployment

### **Desktop App (Standalone)**:

```bash
# Install PyInstaller
pip install pyinstaller

# Build executable
pyinstaller --name ChatApp \
            --windowed \
            --icon=icon.ico \
            --add-data "app:app" \
            app/main.py

# Executable in: dist/ChatApp/
```

### **Web App (Docker)**:
Already configured in `docker-compose.yml`

---

## 📚 Dependencies

- `flet==0.23.2` - UI framework
- `httpx==0.25.1` - HTTP client
- `websockets==12.0` - WebSocket client
- `pydantic==2.5.0` - Data validation
- `python-dateutil==2.8.2` - Date formatting

---

## 🎯 Next Steps

After running the app:
1. ✅ Test login/register
2. ✅ Create conversations
3. ✅ Send messages
4. ✅ Test real-time updates
5. 🔄 Add more features (see Future list above)

---

**Enjoy chatting!** 💬✨

*Frontend built with Flet - Python UI framework*

