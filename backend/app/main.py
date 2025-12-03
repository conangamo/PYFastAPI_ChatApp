"""
FastAPI Backend - Chat App
Entry point for the application
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from .core.config import settings
from .database import init_db, close_db
from .api.router import api_router
from .core.file_utils import init_upload_directories


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan events for FastAPI app
    Handles startup and shutdown
    """
    # Startup
    print("🚀 Backend server starting...")
    print(f"📚 API Documentation: http://localhost:8000/docs")
    print(f"🔧 Environment: {'DEBUG' if settings.DEBUG else 'PRODUCTION'}")
    
    # Initialize upload directories
    init_upload_directories()
    
    # Initialize database (create tables if not exist)
    # Note: In production, use Alembic migrations instead
    await init_db()  # Auto-create tables from models
    
    yield
    
    # Shutdown
    print("👋 Backend server shutting down...")
    await close_db()


# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    description="Real-time chat application backend with WebSocket support",
    version=settings.APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API router
app.include_router(api_router, prefix="/api")


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "ok",
        "message": "Backend is running",
        "version": settings.APP_VERSION
    }


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Welcome to Chat App API",
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "health": "/health",
        "api": "/api"
    }

