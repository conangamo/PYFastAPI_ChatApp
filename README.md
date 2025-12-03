# 💬 Real-Time Chat Application

A modern, full-featured real-time chat application built with FastAPI, PostgreSQL, and Flet. Supports direct messaging, group chats, file sharing, voice messages, and real-time notifications via WebSocket.

![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.104.1-green.svg)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-blue.svg)
![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

---

## ✨ Features

### 🔐 Authentication & User Management
- ✅ User registration and login
- ✅ JWT-based authentication
- ✅ User profiles with display names
- ✅ Password encryption with bcrypt

### 💬 Messaging
- ✅ **Direct messaging (1-1)** - Private conversations between two users
- ✅ **Group chats** - Support for multiple participants (up to 100 members)
- ✅ **Real-time messaging** - Instant message delivery via WebSocket
- ✅ **Message reactions** - Add emoji reactions to messages
- ✅ **Read receipts** - See when messages are delivered and read
- ✅ **Message editing** - Edit sent messages
- ✅ **Message deletion** - Delete your own messages
- ✅ **Typing indicators** - See when others are typing

### 📎 File Sharing
- ✅ **Image upload** - Send and preview images inline
- ✅ **File attachments** - Support for PDF, DOCX, TXT, and more
- ✅ **Voice messages** - Record and send audio messages
- ✅ **File size validation** - Maximum 10MB per file
- ✅ **Automatic thumbnails** - Image thumbnails for better UX

### 👥 Social Features
- ✅ **Friend system** - Send, accept, and manage friend requests
- ✅ **Online/Offline status** - Real-time presence indicators
- ✅ **Conversation settings** - Unfriend, leave group, add members
- ✅ **System messages** - Automatic notifications for group events

### 🎨 User Interface
- ✅ **Modern desktop UI** - Built with Flet (Flutter-based)
- ✅ **Responsive design** - Adaptive message bubbles
- ✅ **Real-time updates** - No page refresh needed
- ✅ **Message status indicators** - Sent, delivered, read status
- ✅ **Conversation list** - Sorted by last activity

---

## 🛠 Tech Stack

### Backend
- **FastAPI** (0.104.1) - Modern, fast web framework for building APIs
- **Uvicorn** - ASGI server with WebSocket support
- **SQLAlchemy** (2.0.23) - Python ORM with async support
- **PostgreSQL** (15) - Relational database
- **Alembic** - Database migration tool
- **WebSocket** - Real-time bidirectional communication
- **JWT** - JSON Web Tokens for authentication
- **Bcrypt** - Password hashing
- **Pydantic** - Data validation and settings management

### Frontend
- **Flet** (0.23.2) - Desktop UI framework (Flutter-based)
- **Python** (3.11+) - Programming language
- **WebSockets** - Real-time client connection
- **Pillow** - Image processing
- **SoundDevice/SoundFile** - Voice message recording

### DevOps
- **Docker** & **Docker Compose** - Containerization
- **PostgreSQL** - Database container
- **FastAPI** - Backend container with hot-reload

---

## 📋 Prerequisites

- **Docker Desktop** (Windows/Mac) or **Docker Engine** (Linux) - Version 20.10+
- **Docker Compose** - Version 3.8+
- **Python** 3.11+ (for running frontend locally)
- **Git** - For cloning the repository

---

## 🚀 Quick Start

### 1. Clone the Repository

```bash
git clone <repository-url>
cd chat_V4
```

### 2. Start Backend and Database

```bash
# Start all services (PostgreSQL + Backend)
docker-compose up -d --build
```

**Wait 30-60 seconds** for services to fully start.

**Verify services are running:**
```bash
# Check containers
docker ps
# Should see: chat_backend (healthy) and chat_postgres (healthy)

# Test backend
curl http://localhost:8000/health
# Response: {"status":"ok","message":"Backend is running"}
```

### 3. Start Frontend

**Note:** Frontend runs locally (not in Docker) for best desktop app experience.

```bash
# Navigate to frontend directory
cd frontend

# Create virtual environment (if not exists)
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the application
python -m app.main
```

The desktop application window will open automatically.

---

## 📖 Detailed Setup Guide

### Environment Configuration

Create a `.env` file in the project root (optional - defaults are provided):

```env
# Database
POSTGRES_DB=chatapp
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres123

# Backend
SECRET_KEY=your-secret-key-change-this-in-production
ACCESS_TOKEN_EXPIRE_MINUTES=30
MAX_FILE_SIZE=10485760

# CORS (comma-separated)
BACKEND_CORS_ORIGINS=http://localhost:8550,http://localhost:8000
```

**⚠️ Important:** Change `SECRET_KEY` and `POSTGRES_PASSWORD` in production!

### Database Setup

The database is automatically initialized when the PostgreSQL container starts. Tables are created from SQLAlchemy models.

**Manual database access:**
```bash
# Connect to PostgreSQL
docker exec -it chat_postgres psql -U postgres -d chatapp

# View tables
\dt

# Exit
\q
```

### Running Migrations

If you modify database models, create and run migrations:

```bash
# Enter backend container
docker exec -it chat_backend bash

# Create migration
alembic revision --autogenerate -m "description"

# Apply migration
alembic upgrade head
```

---

## 🎯 Usage

### First Time Setup

1. **Start backend and database:**
   ```bash
   docker-compose up -d
   ```

2. **Start frontend:**
   ```bash
   cd frontend
   venv\Scripts\activate  # Windows
   python -m app.main
   ```

3. **Register a new account:**
   - Click "Register" in the login screen
   - Fill in: Email, Username, Display Name, Password
   - Click "Register"

4. **Login:**
   - Enter username/email and password
   - Click "Login"

### Creating Conversations

**Direct Chat (1-1):**
1. Click "New Chat" button
2. Select "Direct Chat"
3. Choose a friend from the list
4. Start chatting!

**Group Chat:**
1. Click "New Chat" button
2. Select "Group Chat"
3. Enter group name
4. Select friends to add (must be accepted friends)
5. Click "Create Group"

### Sending Messages

- **Text messages:** Type in the input box and press Enter or click Send
- **Files:** Click the attachment icon (📎) and select a file
- **Images:** Images are displayed inline in the chat
- **Voice messages:** Click the microphone icon (🎤) to record

### Managing Conversations

**Settings (⚙️ icon in chat header):**
- **Direct chat:** Unfriend, Delete conversation
- **Group chat:** Leave group, Add members (creator only)

---

## 📁 Project Structure

```
chat_V4/
├── backend/                 # FastAPI backend
│   ├── app/
│   │   ├── main.py         # FastAPI app entry point
│   │   ├── database.py     # Database connection
│   │   ├── models/         # SQLAlchemy models
│   │   │   ├── user.py
│   │   │   ├── conversation.py
│   │   │   ├── message.py
│   │   │   ├── friendship.py
│   │   │   └── reaction.py
│   │   ├── schemas/        # Pydantic schemas
│   │   ├── api/
│   │   │   └── endpoints/  # REST API endpoints
│   │   │       ├── auth.py
│   │   │       ├── users.py
│   │   │       ├── conversations.py
│   │   │       ├── messages.py
│   │   │       ├── files.py
│   │   │       ├── reactions.py
│   │   │       └── websocket.py
│   │   ├── websocket/      # WebSocket handlers
│   │   │   └── manager.py  # Connection manager
│   │   └── core/           # Core utilities
│   ├── requirements.txt
│   ├── Dockerfile
│   └── alembic/           # Database migrations
│
├── frontend/               # Flet desktop app
│   ├── app/
│   │   ├── main.py        # App entry point
│   │   ├── config.py      # Configuration
│   │   ├── api/
│   │   │   └── client.py  # HTTP API client
│   │   ├── websocket/
│   │   │   └── client.py  # WebSocket client
│   │   ├── models/        # Data models
│   │   ├── screens/       # UI screens
│   │   │   ├── login.py
│   │   │   ├── register.py
│   │   │   └── main_screen.py
│   │   ├── components/     # UI components
│   │   │   ├── message_bubble.py
│   │   │   ├── message_input.py
│   │   │   └── ...
│   │   └── utils/         # Utilities
│   ├── requirements.txt
│   └── Dockerfile
│
├── database/              # Database initialization
│   └── init.sql
│
├── documents/             # Documentation and guides
│
├── docker-compose.yml     # Docker services configuration
├── .env                   # Environment variables (create from .env.example)
├── .gitignore
└── README.md             # This file
```

---

## 🔌 API Documentation

Once the backend is running, access interactive API documentation:

- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

### Key Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/auth/register` | POST | Register new user |
| `/api/auth/login` | POST | Login and get JWT token |
| `/api/users/me` | GET | Get current user profile |
| `/api/conversations` | GET | List user's conversations |
| `/api/conversations` | POST | Create new conversation |
| `/api/messages` | GET | Get messages from conversation |
| `/api/messages` | POST | Send a message |
| `/api/files/upload` | POST | Upload a file |
| `/api/ws` | WebSocket | Real-time messaging connection |

**Authentication:** Most endpoints require JWT token in `Authorization: Bearer <token>` header.

---

## 🧪 Testing

### Manual Testing

1. **Test Authentication:**
   ```bash
   # Register
   curl -X POST http://localhost:8000/api/auth/register \
     -H "Content-Type: application/json" \
     -d '{"email":"test@example.com","username":"testuser","display_name":"Test User","password":"test123"}'
   
   # Login
   curl -X POST http://localhost:8000/api/auth/login \
     -H "Content-Type: application/x-www-form-urlencoded" \
     -d "username=testuser&password=test123"
   ```

2. **Test WebSocket:**
   - Use the Swagger UI WebSocket tester at `/docs`
   - Or use the frontend application

### Automated Tests

```bash
# Run backend tests
docker exec -it chat_backend pytest

# Or run locally
cd backend
pytest
```

---

## 🐛 Troubleshooting

### Backend won't start

```bash
# Check logs
docker-compose logs backend

# Restart services
docker-compose restart backend

# Rebuild containers
docker-compose down
docker-compose up -d --build
```

### Database connection error

```bash
# Check PostgreSQL is ready
docker exec -it chat_postgres pg_isready

# View database logs
docker-compose logs postgres

# Reset database (⚠️ deletes all data)
docker-compose down -v
docker-compose up -d
```

### Frontend can't connect to backend

1. **Verify backend is running:**
   ```bash
   curl http://localhost:8000/health
   ```

2. **Check frontend config:**
   - Open `frontend/app/config.py`
   - Ensure `BACKEND_URL = "http://localhost:8000"`

3. **Check firewall/antivirus** - May block localhost connections

### Port already in use

**Change ports in `docker-compose.yml`:**
```yaml
services:
  backend:
    ports:
      - "8001:8000"  # Change 8000 to 8001
  postgres:
    ports:
      - "5434:5432"  # Change 5433 to 5434
```

Then update frontend config accordingly.

---

## 🔒 Security Notes

⚠️ **This project is for educational purposes. Not production-ready!**

**For production, add:**
- ✅ HTTPS/TLS encryption
- ✅ Rate limiting
- ✅ Enhanced input validation
- ✅ SQL injection prevention (already using parameterized queries)
- ✅ XSS protection
- ✅ CORS configuration for specific domains
- ✅ Environment variable secrets management
- ✅ Database backup strategy
- ✅ Logging and monitoring
- ✅ CI/CD pipeline
- ✅ Security headers

---

## 🚧 Known Limitations

- Frontend runs locally (not containerized) for best desktop experience
- No video/voice calls (only voice messages)
- No mobile app (desktop only)
- No end-to-end encryption
- No message search functionality
- Limited to 10MB file size
- Group chat limited to 100 members

---

## 🗺 Roadmap

### Planned Features
- [ ] Message search
- [ ] Dark mode
- [ ] Custom themes
- [ ] Message forwarding
- [ ] Message pinning
- [ ] Voice/video calls (WebRTC)
- [ ] Mobile app (iOS/Android)
- [ ] End-to-end encryption
- [ ] Message scheduling
- [ ] Chat export

---

## 📚 Documentation

Additional documentation is available in the `documents/` folder:

- **Architecture Overview** - System design and architecture
- **API Testing Guide** - How to test the API
- **WebSocket Guide** - WebSocket implementation details
- **Database Schema** - Database structure documentation
- **Deployment Guide** - Production deployment instructions

---

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

**Guidelines:**
- Follow PEP 8 style guide for Python code
- Write clear commit messages
- Add tests for new features
- Update documentation as needed

---

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

**Free to use for educational purposes.**

---

## 👥 Authors

- **Your Name** - *Initial work* - [YourGitHub](https://github.com/yourusername)

---

## 🙏 Acknowledgments

- FastAPI team for the amazing framework
- Flet team for the desktop UI framework
- PostgreSQL community
- All open-source contributors

---

## 📞 Support

If you encounter any issues or have questions:

1. Check the [Troubleshooting](#-troubleshooting) section
2. Review the documentation in `documents/`
3. Open an issue on GitHub
4. Check API documentation at http://localhost:8000/docs

---

**Made with ❤️ using Python, FastAPI, and Flet**

**Happy Chatting! 💬✨**
