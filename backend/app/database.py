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
    engine = create_async_engine(
        settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://"),
        connect_args={"ssl": True, "command_timeout": 10},
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