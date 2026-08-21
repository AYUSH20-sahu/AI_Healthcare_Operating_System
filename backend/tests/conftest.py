"""Pytest configuration and fixtures."""

from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from app.database import override_db_engine
from app.main import app
from app.models import Base, User, UserRole
from app.services.auth.service import create_access_token, get_password_hash


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    import asyncio
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def db_session():
    """Create a test database session using SQLite file-based for complete isolation."""
    # Use SQLite file-based for tests - complete isolation from Nhost PostgreSQL
    # File-based SQLite allows multiple connections to share the same database
    import os
    import tempfile
    
    # Create a temporary file for the database
    temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
    temp_db.close()
    temp_db_path = temp_db.name
    test_db_url = f"sqlite+aiosqlite:///{temp_db_path}"
    
    engine = create_async_engine(
        test_db_url,
        connect_args={"check_same_thread": False},
        poolclass=NullPool,
    )
    
    # Override the app's database engine for this test
    override_db_engine(engine)
    
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    AsyncSessionLocal = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with AsyncSessionLocal() as session:
        yield session
    
    # Drop tables after test
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()
    
    # Clean up temp file
    if os.path.exists(temp_db_path):
        os.unlink(temp_db_path)


@pytest_asyncio.fixture
async def client(db_session):
    """Create an async test client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def admin_user(db_session):
    """Create an admin user."""
    user = User(
        user_id=uuid4(),
        email="admin@test.com",
        hashed_password=get_password_hash("adminpassword123"),
        full_name="Admin User",
        role=UserRole.ADMIN,
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def admin_token(admin_user):
    """Create an admin access token."""
    return create_access_token(data={"sub": str(admin_user.user_id), "email": admin_user.email, "role": admin_user.role.value})


@pytest_asyncio.fixture
async def doctor_user(db_session):
    """Create a doctor user."""
    user = User(
        user_id=uuid4(),
        email="doctor@test.com",
        hashed_password=get_password_hash("doctorpassword123"),
        full_name="Dr. Test",
        role=UserRole.DOCTOR,
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def doctor_token(doctor_user):
    """Create a doctor access token."""
    return create_access_token(data={"sub": str(doctor_user.user_id), "email": doctor_user.email, "role": doctor_user.role.value})


@pytest_asyncio.fixture
async def patient_user(db_session):
    """Create a patient user."""
    user = User(
        user_id=uuid4(),
        email="patient@test.com",
        hashed_password=get_password_hash("patientpassword123"),
        full_name="Test Patient",
        role=UserRole.PATIENT,
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def patient_token(patient_user):
    """Create a patient access token."""
    return create_access_token(data={"sub": str(patient_user.user_id), "email": patient_user.email, "role": patient_user.role.value})