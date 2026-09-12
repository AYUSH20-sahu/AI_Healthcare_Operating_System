"""Auth API routes."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import AuditLog, AuditOutcome, Patient, User, UserRole
from app.services.auth.service import (
    Token,
    UserCreate,
    UserLogin,
    UserResponse,
    UserSignupRequest,
    authenticate_user,
    create_access_token,
    create_refresh_token,
    create_user,
    get_current_active_user,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/signup", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def signup(user_data: UserSignupRequest, db: AsyncSession = Depends(get_db)):
    """Register a new patient user. Strictly enforces PATIENT role."""
    # Check if user already exists
    existing_user = await db.execute(
        select(User).where(User.email == user_data.email)
    )
    if existing_user.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )
    
    # Public registration strictly creates PATIENT accounts only
    user_create = UserCreate(
        email=user_data.email,
        password=user_data.password,
        full_name=user_data.full_name,
        role=UserRole.PATIENT.value,
    )
    user = await create_user(db, user_create, role=UserRole.PATIENT.value)

    # Automatically create associated Patient profile
    patient_profile = Patient(
        user_id=user.user_id,
        full_name=user.full_name,
        email=user.email,
    )
    db.add(patient_profile)

    # Immutable Audit Log
    audit = AuditLog(
        user_id=user.user_id,
        action="PUBLIC_USER_REGISTRATION",
        resource_type="users",
        resource_id=user.user_id,
        outcome=AuditOutcome.SUCCESS,
        details={"role": UserRole.PATIENT.value, "email": user.email},
    )
    db.add(audit)
    await db.commit()
    await db.refresh(user)
    return user


@router.post("/login", response_model=Token)
async def login(form_data: UserLogin, db: AsyncSession = Depends(get_db)):
    """Login and get access + refresh tokens."""
    user = await authenticate_user(db, form_data.email, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = create_access_token(data={"sub": str(user.user_id), "email": user.email, "role": user.role})
    refresh_token = create_refresh_token(data={"sub": str(user.user_id), "email": user.email, "role": user.role})
    
    return Token(access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh", response_model=Token)
async def refresh_token(refresh_token: str, db: AsyncSession = Depends(get_db)):
    """Refresh access token using refresh token."""
    from uuid import UUID

    from app.services.auth.service import TokenData, get_user_by_id, jwt, settings
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(
            refresh_token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
        if payload.get("type") != "refresh":
            raise credentials_exception
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
        token_data = TokenData(user_id=UUID(user_id))
    except Exception:
        raise credentials_exception
    
    user = await get_user_by_id(db, token_data.user_id)
    if user is None:
        raise credentials_exception
    
    access_token = create_access_token(data={"sub": str(user.user_id), "email": user.email, "role": user.role})
    new_refresh_token = create_refresh_token(data={"sub": str(user.user_id), "email": user.email, "role": user.role})
    
    return Token(access_token=access_token, refresh_token=new_refresh_token)


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_active_user)):
    """Get current user information."""
    return current_user