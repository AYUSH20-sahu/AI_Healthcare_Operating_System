"""Database dependency for FastAPI."""

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings

# Global engine and session factory - can be overridden for testing
engine = None
AsyncSessionLocal = None


def init_db():
    """Initialize the database engine and session factory."""
    global engine, AsyncSessionLocal
    connect_args = {"command_timeout": 10}
    if "localhost" not in settings.DATABASE_URL and "127.0.0.1" not in settings.DATABASE_URL:
        connect_args["ssl"] = True

    url = settings.DATABASE_URL
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+asyncpg://", 1)
    elif url.startswith("postgresql://") and not url.startswith("postgresql+asyncpg://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)

    engine = create_async_engine(
        url,
        connect_args=connect_args,
        echo=False,
    )
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