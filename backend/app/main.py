from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from .core.config import settings
from .database import init_db, close_db
from .api.router import api_router
from .core.file_utils import init_upload_directories


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Backend server starting...")
    print(f"PI Documentation: http://localhost:8000/docs")
    print(f"Environment: {'DEBUG' if settings.DEBUG else 'PRODUCTION'}")
    
    init_upload_directories()
    await init_db()
    
    yield
    
    print("Backend server shutting down...")
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


@app.get("/health")
async def health_check():
    return {
        "status": "ok",
        "message": "Backend is running",
        "version": settings.APP_VERSION
    }


@app.get("/")
async def root():
    return {
        "message": "Welcome to Chat App API",
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "health": "/health",
        "api": "/api"
    }

