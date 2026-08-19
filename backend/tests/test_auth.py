"""Tests for auth service."""

import pytest
import pytest_asyncio
from uuid import uuid4
from datetime import datetime

from app.services.auth.service import (
    UserCreate,
    UserLogin,
    verify_password,
    get_password_hash,
    create_access_token,
    create_refresh_token,
    authenticate_user,
    create_user,
    get_user_by_email,
    get_user_by_id,
)
from app.models import User, UserRole


@pytest_asyncio.fixture
async def test_user(db_session):
    """Create a test user."""
    user = User(
        email="test@example.com",
        hashed_password=get_password_hash("testpassword123"),
        full_name="Test User",
        role=UserRole.PATIENT,
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


class TestPasswordHashing:
    """Test password hashing and verification."""

    def test_get_password_hash(self):
        """Test password hashing produces a hash."""
        password = "testpassword123"
        hashed = get_password_hash(password)
        assert hashed != password
        assert len(hashed) > 0

    def test_verify_password_correct(self):
        """Test verifying correct password."""
        password = "testpassword123"
        hashed = get_password_hash(password)
        assert verify_password(password, hashed) is True

    def test_verify_password_incorrect(self):
        """Test verifying incorrect password."""
        password = "testpassword123"
        hashed = get_password_hash(password)
        assert verify_password("wrongpassword", hashed) is False


class TestTokenCreation:
    """Test JWT token creation."""

    def test_create_access_token(self):
        """Test creating access token."""
        data = {"sub": str(uuid4()), "email": "test@example.com", "role": "patient"}
        token = create_access_token(data)
        assert isinstance(token, str)
        assert len(token) > 0

    def test_create_refresh_token(self):
        """Test creating refresh token."""
        data = {"sub": str(uuid4()), "email": "test@example.com", "role": "patient"}
        token = create_refresh_token(data)
        assert isinstance(token, str)
        assert len(token) > 0


class TestUserOperations:
    """Test user database operations."""

    @pytest.mark.asyncio
    async def test_create_user(self, db_session):
        """Test creating a new user."""
        user_data = UserCreate(
            email="newuser@example.com",
            password="newpassword123",
            full_name="New User",
            role="patient",
        )
        user = await create_user(db_session, user_data)
        
        assert user.email == "newuser@example.com"
        assert user.full_name == "New User"
        assert user.role == UserRole.PATIENT
        assert user.is_active is True
        assert user.hashed_password != "newpassword123"

    @pytest.mark.asyncio
    async def test_get_user_by_email(self, db_session, test_user):
        """Test getting user by email."""
        user = await get_user_by_email(db_session, "test@example.com")
        assert user is not None
        assert user.email == "test@example.com"

    @pytest.mark.asyncio
    async def test_get_user_by_email_not_found(self, db_session):
        """Test getting non-existent user by email."""
        user = await get_user_by_email(db_session, "nonexistent@example.com")
        assert user is None

    @pytest.mark.asyncio
    async def test_get_user_by_id(self, db_session, test_user):
        """Test getting user by ID."""
        user = await get_user_by_id(db_session, test_user.user_id)
        assert user is not None
        assert user.user_id == test_user.user_id

    @pytest.mark.asyncio
    async def test_get_user_by_id_not_found(self, db_session):
        """Test getting non-existent user by ID."""
        user = await get_user_by_id(db_session, uuid4())
        assert user is None


class TestAuthentication:
    """Test user authentication."""

    @pytest.mark.asyncio
    async def test_authenticate_user_success(self, db_session, test_user):
        """Test successful authentication."""
        user = await authenticate_user(db_session, "test@example.com", "testpassword123")
        assert user is not None
        assert user.user_id == test_user.user_id

    @pytest.mark.asyncio
    async def test_authenticate_user_wrong_password(self, db_session, test_user):
        """Test authentication with wrong password."""
        user = await authenticate_user(db_session, "test@example.com", "wrongpassword")
        assert user is None

    @pytest.mark.asyncio
    async def test_authenticate_user_not_found(self, db_session):
        """Test authentication with non-existent user."""
        user = await authenticate_user(db_session, "nonexistent@example.com", "password")
        assert user is None