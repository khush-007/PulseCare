from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import declarative_base, sessionmaker
from backend.app.core.config import settings

# SQLite compatibility arguments
connect_args = {}
if "sqlite" in settings.DATABASE_URL:
    connect_args["check_same_thread"] = False

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    connect_args=connect_args,
    future=True,
)

AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)
async_sessionmaker = AsyncSessionLocal  # Alias for compatibility with existing tests

Base = declarative_base()


initialized = False

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields an active database session.
    Ensures the database schema is initialized (including legacy columns) before first use.
    """
    global initialized
    if not initialized:
        # Initialize tables and add missing columns (e.g., enable_memory) if needed.
        # This is safe to call multiple times; it will create tables if absent and ignore existing schema.
        await init_db()
        initialized = True
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """Create database tables if they do not exist and ensure schema is up-to-date.
    This function is safe to call multiple times; it creates missing tables and
    adds new columns (e.g., `user_id` on `knowledge_document_chunks`) via ALTER
    statements when necessary.
    """
    # Import all model modules so that Base.metadata knows about the tables
    from backend.app.models import (
        user,
        user_memory,
        doctor,
        appointment,
        service,
        chatbot,
        medicine,
    )
    # 1️⃣ Create all tables defined by the models
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # 2️⃣ SQLite‑specific legacy migration: add ``user_id`` column if missing
    if "sqlite" in settings.DATABASE_URL:
        async with engine.begin() as conn:
            from sqlalchemy import text
            pragma_result = await conn.execute(
                text("PRAGMA table_info(knowledge_document_chunks);")
            )
            columns = [row[1] for row in pragma_result.fetchall()]
            if "user_id" not in columns:
                await conn.execute(
                    text(
                        "ALTER TABLE knowledge_document_chunks ADD COLUMN user_id INTEGER"
                    )
                )
            # else: column already present – nothing to do
    # Note: For production migrations, use Alembic instead of this function.


