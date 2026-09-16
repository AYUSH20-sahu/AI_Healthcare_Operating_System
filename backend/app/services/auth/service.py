"""Auth service - signup, login, JWT handling."""

from datetime import datetime, timedelta
from uuid import UUID

import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.database import get_db
from app.models import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    user_id: UUID | None = None
    email: str | None = None
    role: str | None = None


class UserSignupRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str

    class Config:
        extra = "forbid"


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    role: str = "patient"


class UserResponse(BaseModel):
    user_id: UUID
    email: str
    full_name: str
    role: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class UserLogin(BaseModel):
    email: EmailStr
    password: str


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against its hash."""
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))


def get_password_hash(password: str) -> str:
    """Hash a password."""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


# Revocation tracking (SEC-04: Refresh Token Rotation & Revocation with Redis + In-Memory Fallback)
revoked_jtis: set[str] = set()
user_tokens_revoked_before: dict[str, float] = {}  # user_id -> timestamp


def _get_redis_client():
    try:
        import redis
        client = redis.from_url(settings.REDIS_URL, decode_responses=True, socket_timeout=0.5)
        client.ping()
        return client
    except Exception:
        return None


def revoke_token_jti(jti: str) -> None:
    """Revoke a specific refresh token identifier in Redis and in-memory set."""
    if not jti:
        return
    str_jti = str(jti)
    revoked_jtis.add(str_jti)
    r = _get_redis_client()
    if r:
        try:
            ttl_seconds = settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS * 86400
            r.set(f"revoked_jti:{str_jti}", "1", ex=ttl_seconds)
        except Exception:
            pass


def is_token_jti_revoked(jti: str) -> bool:
    """Check if token identifier is in revocation list (Redis or in-memory)."""
    if not jti:
        return False
    str_jti = str(jti)
    if str_jti in revoked_jtis:
        return True
    r = _get_redis_client()
    if r:
        try:
            if r.exists(f"revoked_jti:{str_jti}"):
                return True
        except Exception:
            pass
    return False


def revoke_all_user_tokens(user_id: str) -> None:
    """Revoke all tokens issued for a user before this timestamp."""
    ts = datetime.utcnow().timestamp()
    str_uid = str(user_id)
    user_tokens_revoked_before[str_uid] = ts
    r = _get_redis_client()
    if r:
        try:
            ttl_seconds = settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS * 86400
            r.set(f"user_revoked_before:{str_uid}", str(ts), ex=ttl_seconds)
        except Exception:
            pass


def is_user_token_invalidated(user_id: str, issued_at: float | None) -> bool:
    """Check if a token was invalidated by a subsequent user-wide revocation."""
    str_uid = str(user_id)
    if not issued_at:
        return False
    if str_uid in user_tokens_revoked_before and issued_at < user_tokens_revoked_before[str_uid]:
        return True
    r = _get_redis_client()
    if r:
        try:
            val = r.get(f"user_revoked_before:{str_uid}")
            if val and issued_at < float(val):
                return True
        except Exception:
            pass
    return False


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    now = datetime.utcnow()
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "type": "access", "iat": now.timestamp()})
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt


def create_refresh_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """Create a JWT refresh token with unique jti identifier."""
    import uuid as _uuid
    to_encode = data.copy()
    now = datetime.utcnow()
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)
    jti = to_encode.get("jti") or str(_uuid.uuid4())
    to_encode.update({"exp": expire, "type": "refresh", "jti": jti, "iat": now.timestamp()})
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt


async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    """Get user by email."""
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def get_user_by_id(db: AsyncSession, user_id: UUID) -> User | None:
    """Get user by ID."""
    result = await db.execute(select(User).where(User.user_id == user_id))
    return result.scalar_one_or_none()


async def authenticate_user(db: AsyncSession, email: str, password: str) -> User | None:
    """Authenticate a user with email and password."""
    user = await get_user_by_email(db, email)
    if not user:
        return None
    if not user.is_active:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


async def create_user(db: AsyncSession, user_data: UserCreate, role: str = "patient") -> User:
    """Create a new user with password strength validation. Public registration defaults to patient role."""
    from app.core.security import validate_password_strength
    from app.models import UserRole

    # Enforce password strength
    is_valid, msg = validate_password_strength(user_data.password)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=msg or "Password does not meet security requirements.",
        )

    # Enforce safe role conversion, default to patient
    try:
        user_role = UserRole(role)
    except (ValueError, KeyError):
        user_role = UserRole.PATIENT

    hashed_password = get_password_hash(user_data.password)
    user = User(
        email=user_data.email,
        hashed_password=hashed_password,
        full_name=user_data.full_name,
        role=user_role,
        is_active=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Get current user from JWT token, strictly verifying token type is 'access'."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
        # Prevent refresh tokens from accessing authorized API routes
        token_type = payload.get("type")
        if token_type and token_type != "access":
            raise credentials_exception

        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
        if is_user_token_invalidated(user_id, payload.get("iat")):
            raise credentials_exception
        token_data = TokenData(user_id=UUID(user_id))
    except (JWTError, ValueError):
        raise credentials_exception
    
    user = await get_user_by_id(db, token_data.user_id)
    if user is None:
        raise credentials_exception
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Get current active user."""
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user