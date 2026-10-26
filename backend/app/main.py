from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.app.core.config import settings
from backend.app.core.database import init_db
from backend.app.routers.auth import router as auth_router
from backend.app.routers.doctors import router as doctors_router
from backend.app.routers.appointments import router as appointments_router
from backend.app.routers.services import router as services_router
from backend.app.routers.triage import router as triage_router
from backend.app.chatbot.router import router as chatbot_router
from backend.app.chatbot.memory.personalization import router as memory_router
from backend.app.routers.documents import router as documents_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize DB schema on startup
    await init_db()
    # Ensure document upload root exists
    import os
    os.makedirs(settings.DOCUMENTS_ROOT, exist_ok=True)
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="PulseCare Smart Healthcare Appointment & Triage System Backend with Agentic Chatbot",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Core PulseCare Routers
app.include_router(auth_router, prefix=settings.API_V1_STR)
app.include_router(doctors_router, prefix=settings.API_V1_STR)
app.include_router(appointments_router, prefix=settings.API_V1_STR)
app.include_router(services_router, prefix=settings.API_V1_STR)
app.include_router(triage_router, prefix=settings.API_V1_STR)

# Dedicated Isolated Chatbot Router
app.include_router(memory_router, prefix=settings.API_V1_STR)
app.include_router(chatbot_router, prefix=settings.API_V1_STR)
app.include_router(documents_router, prefix=settings.API_V1_STR)


@app.get("/health", tags=["Health"])
async def health_check():
    return {
        "status": "healthy",
        "system": settings.PROJECT_NAME,
        "environment": settings.ENVIRONMENT,
    }


@app.get("/", tags=["Root"])
async def root():
    return {
        "message": "Welcome to PulseCare Smart Healthcare API",
        "docs": "/docs",
        "version": "1.0.0",
    }
