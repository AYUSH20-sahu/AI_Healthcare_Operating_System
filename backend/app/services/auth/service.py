"""Auth service - signup, login, JWT handling."""

from datetime import datetime, timedelta
from uuid import UUID

import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from pydantic import BaseModel, EmailStr
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
import importlib
from app.database import get_db
from app.models import Doctor, Patient, User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    user_id: UUID | None = None
    email: str | None = None
    role: str | None = None
    organization_id: str | None = None


class UserSignupRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    phone: str | None = None

    class Config:
        extra = "allow"


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    role: str = "patient"
    phone: str | None = None
    organization_id: UUID | None = None


class UserResponse(BaseModel):
    user_id: UUID
    email: str
    phone: str | None = None
    full_name: str
    role: str
    organization_id: UUID | None = None
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class UserLogin(BaseModel):
    email: str | None = None
    phone: str | None = None
    identifier: str | None = None
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
        redis_lib = importlib.import_module("redis")
        client = redis_lib.from_url(settings.REDIS_URL, decode_responses=True, socket_timeout=0.5)
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


def normalize_phone(phone: str | None) -> str | None:
    """Normalize phone number by stripping whitespace, dashes, and parentheses."""
    if not phone:
        return None
    import re
    cleaned = re.sub(r"[\s\-\(\)]", "", phone.strip())
    return cleaned or phone.strip()


async def check_credentials_available(
    db: AsyncSession,
    email: str | None = None,
    phone: str | None = None,
    exclude_user_id: UUID | None = None,
) -> None:
    """Verify that email and phone number are not already linked to ANY account.

    Checks across all roles (Admin, Doctor, Patient, Nurse, Receptionist, Physician).
    Raises HTTPException(400) if a conflict is detected.
    """
    clean_email = email.strip().lower() if email else None
    norm_phone = normalize_phone(phone)
    raw_phone = phone.strip() if phone else None
    phone_candidates = list({p for p in [norm_phone, raw_phone] if p})

    # 1. Verify Email
    if clean_email:
        # Check users table
        user_stmt = select(User).where(func.lower(User.email) == clean_email)
        if exclude_user_id:
            user_stmt = user_stmt.where(User.user_id != exclude_user_id)
        user_res = await db.execute(user_stmt)
        if user_res.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="An account with this email address already exists. Please log in using your credentials.",
            )

        # Check patients table
        pat_res = await db.execute(
            select(Patient).where(func.lower(Patient.email) == clean_email)
        )
        pat = pat_res.scalar_one_or_none()
        if pat and (not exclude_user_id or pat.user_id != exclude_user_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="An account with this email address already exists. Please log in using your credentials.",
            )

        # Check doctors table
        doc_res = await db.execute(
            select(Doctor).where(func.lower(Doctor.email) == clean_email)
        )
        doc = doc_res.scalar_one_or_none()
        if doc and (not exclude_user_id or doc.user_id != exclude_user_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="An account with this email address already exists. Please log in using your credentials.",
            )

    # 2. Verify Mobile Phone Number
    if phone_candidates:
        # Check users table
        user_phone_stmt = select(User).where(
            or_(*[User.phone == cand for cand in phone_candidates])
        )
        if exclude_user_id:
            user_phone_stmt = user_phone_stmt.where(User.user_id != exclude_user_id)
        user_phone_res = await db.execute(user_phone_stmt)
        if user_phone_res.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="An account with this mobile phone number already exists. Please log in using your credentials.",
            )

        # Check patients table
        pat_phone_res = await db.execute(
            select(Patient).where(
                or_(*[Patient.phone == cand for cand in phone_candidates])
            )
        )
        pat = pat_phone_res.scalar_one_or_none()
        if pat and (not exclude_user_id or pat.user_id != exclude_user_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="An account with this mobile phone number already exists. Please log in using your credentials.",
            )

        # Check doctors table
        doc_phone_res = await db.execute(
            select(Doctor).where(
                or_(*[Doctor.phone == cand for cand in phone_candidates])
            )
        )
        doc = doc_phone_res.scalar_one_or_none()
        if doc and (not exclude_user_id or doc.user_id != exclude_user_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="An account with this mobile phone number already exists. Please log in using your credentials.",
            )


async def get_user_by_id(db: AsyncSession, user_id: UUID) -> User | None:
    """Get user by ID."""
    result = await db.execute(select(User).where(User.user_id == user_id))
    return result.scalar_one_or_none()


async def get_user_by_phone(db: AsyncSession, phone: str) -> User | None:
    """Get user by phone number (checking raw and normalized variants)."""
    if not phone:
        return None
    norm = normalize_phone(phone)
    candidates = list({p for p in [norm, phone.strip()] if p})
    result = await db.execute(select(User).where(or_(*[User.phone == c for c in candidates])))
    return result.scalar_one_or_none()


async def get_user_by_identifier(db: AsyncSession, identifier: str) -> User | None:
    """Get user by email or phone number (checking User, Patient, and Doctor records)."""
    if not identifier:
        return None
    cleaned = identifier.strip()
    norm = normalize_phone(cleaned)
    candidates = list({p for p in [cleaned, norm] if p})

    # Try matching User table (email or phone)
    result = await db.execute(
        select(User).where(
            or_(
                func.lower(User.email) == cleaned.lower(),
                *[User.phone == c for c in candidates],
            )
        )
    )
    user = result.scalar_one_or_none()
    if user:
        return user

    # Check Patient profile
    pat_res = await db.execute(
        select(Patient).where(
            or_(
                func.lower(Patient.email) == cleaned.lower(),
                *[Patient.phone == c for c in candidates],
            )
        )
    )
    patient = pat_res.scalar_one_or_none()
    if patient and patient.user_id:
        user = await get_user_by_id(db, patient.user_id)
        if user:
            return user

    # Check Doctor profile
    doc_res = await db.execute(
        select(Doctor).where(
            or_(
                func.lower(Doctor.email) == cleaned.lower(),
                *[Doctor.phone == c for c in candidates],
            )
        )
    )
    doctor = doc_res.scalar_one_or_none()
    if doctor and doctor.user_id:
        user = await get_user_by_id(db, doctor.user_id)
        if user:
            return user

    return None


async def authenticate_user(db: AsyncSession, identifier: str, password: str) -> User | None:
    """Authenticate a user with email or phone number and password."""
    user = await get_user_by_identifier(db, identifier)
    if not user:
        return None
    if not user.is_active:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


async def create_user(db: AsyncSession, user_data: UserCreate, role: str = "patient") -> User:
    """Create a new user with password strength validation."""
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
        phone=user_data.phone,
        organization_id=user_data.organization_id,
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
        try:
            target_uuid = UUID(user_id)
            user = await get_user_by_id(db, target_uuid)
        except ValueError:
            user = await get_user_by_identifier(db, user_id)
    except (JWTError, ValueError):
        raise credentials_exception
    
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