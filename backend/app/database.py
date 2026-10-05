"""Database dependency for FastAPI."""

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine  # type: ignore
from sqlalchemy.orm import sessionmaker  # type: ignore

from app.core.config import settings

# Global engine and session factory - can be overridden for testing
engine: Any = None
AsyncSessionLocal: Any = None


def init_db():
    """Initialize the database engine and session factory."""
    global engine, AsyncSessionLocal
    connect_args = {}
    is_sqlite = "sqlite" in settings.DATABASE_URL

    if not is_sqlite:
        connect_args["command_timeout"] = 15
        if "localhost" not in settings.DATABASE_URL and "127.0.0.1" not in settings.DATABASE_URL:
            connect_args["ssl"] = True

    url = settings.DATABASE_URL
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+asyncpg://", 1)
    elif url.startswith("postgresql://") and not url.startswith("postgresql+asyncpg://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)

    engine_kwargs = {
        "echo": False,
        "connect_args": connect_args,
    }
    if not is_sqlite:
        engine_kwargs["pool_pre_ping"] = True
        engine_kwargs["pool_recycle"] = 300

    engine = create_async_engine(url, **engine_kwargs)
    AsyncSessionLocal = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )


def override_db_engine(test_engine):
    """Override the database engine for testing."""
    global engine, AsyncSessionLocal
    engine = test_engine
    AsyncSessionLocal = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )


async def get_db() -> AsyncSession:
    """Get database session."""
    if AsyncSessionLocal is None:
        init_db()
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()