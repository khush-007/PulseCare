from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import Field, validator
import os


class Settings(BaseSettings):
    PROJECT_NAME: str = "PulseCare - Smart Healthcare Appointment & Triage System"
    API_V1_STR: str = "/api"
    ENVIRONMENT: str = "development"

    # Database
    # Defaults to SQLite async for local zero-dependency testing, or Postgres in production
    DATABASE_URL: str = Field(
        default="sqlite+aiosqlite:///./pulsecare.db",
        description="Async DB connection string (PostgreSQL with asyncpg or SQLite with aiosqlite)"
    )
    SYNC_DATABASE_URL: str = Field(
        default="sqlite:///./pulsecare.db",
        description="Sync DB connection string for migrations/scripts"
    )

    # Security
    SECRET_KEY: str = Field("dev-secret-key", env="SECRET_KEY", description="Secret key for JWT; must be set via env in production (dev placeholder provided)")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 1 day

    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ]

    # Chatbot & LLM Settings
    LLM_PROVIDER: str = Field(
        default="mock",
        description="mock | gemini | openai | anthropic"
    )
    LLM_MODEL: str = Field(default="gemini-2.5-flash", description="LLM model name")
    LLM_API_KEY: Optional[str] = Field(default=None, env="GEMINI_API_KEY")
    LLM_BASE_URL: Optional[str] = None
    LLM_TEMPERATURE: float = 0.1

    # Embeddings & Reranker
    EMBEDDING_PROVIDER: str = Field(
        default="mock",
        description="mock | openai | gemini | huggingface"
    )
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    EMBEDDING_DIMENSION: int = 384

    RERANKER_PROVIDER: str = Field(
        default="simple",
        description="simple | cross-encoder | cohere"
    )
    RERANKER_MODEL: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"

    # RAG Settings
    RAG_TOP_K_RETRIEVAL: int = 20
    RAG_TOP_K_RERANK: int = 5
    RAG_RELEVANCE_THRESHOLD: float = 0.4
    RAG_ENABLE_HYDE: bool = False

    # Feature Flags
    FEATURE_PROPOSE_BOOKING: bool = True
    FEATURE_EXTERNAL_MEDICINE_API: bool = True

    # Rate Limiting & Safety
    CHAT_RATE_LIMIT_PER_MINUTE: int = 30
    CHAT_MAX_INPUT_LENGTH: int = 1500
    CHAT_MAX_HISTORY_TURNS: int = 10

    # Document storage root for user uploads
    DOCUMENTS_ROOT: str = "./uploaded_documents"

    class Config:
        env_file = ".env"
        extra = "ignore"

    @validator('SECRET_KEY')
    def _ensure_secret_key(cls, v, values):
        # In non‑development environments we must have a real secret set via env var.
        if values.get('ENVIRONMENT') != 'development' and v.startswith('pulsecare-production-secret-key'):
            raise ValueError('SECRET_KEY must be provided through environment variable in production')
        return v



settings = Settings()
