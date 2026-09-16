"""Auth API routes."""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
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
@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
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
    
    user_role_str = user.role.value if hasattr(user.role, "value") else str(user.role)
    access_token = create_access_token(data={"sub": str(user.user_id), "email": user.email, "role": user_role_str})
    refresh_token = create_refresh_token(data={"sub": str(user.user_id), "email": user.email, "role": user_role_str})
    
    return Token(access_token=access_token, refresh_token=refresh_token)


class RefreshTokenPayload(BaseModel):
    refresh_token: str


class LogoutPayload(BaseModel):
    refresh_token: str | None = None


@router.post("/refresh", response_model=Token)
async def refresh_token(
    payload_data: RefreshTokenPayload | None = None,
    refresh_token: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Refresh access token with refresh token rotation and reuse detection (SEC-04)."""
    from uuid import UUID
    from app.services.auth.service import (
        TokenData,
        get_user_by_id,
        is_token_jti_revoked,
        is_user_token_invalidated,
        jwt,
        revoke_all_user_tokens,
        revoke_token_jti,
        settings,
    )

    raw_token = (payload_data.refresh_token if payload_data else None) or refresh_token
    if not raw_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Refresh token is required",
        )

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(
            raw_token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
        if payload.get("type") != "refresh":
            raise credentials_exception

        user_id_str: str = payload.get("sub")
        if not user_id_str:
            raise credentials_exception

        jti = payload.get("jti")
        # Token reuse detection: if this jti was already rotated/revoked, revoke all tokens for this user!
        if jti and is_token_jti_revoked(jti):
            revoke_all_user_tokens(user_id_str)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Revoked refresh token presented. Potential token theft detected; all sessions revoked.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Check if user's tokens were invalidated before this token was issued
        if is_user_token_invalidated(user_id_str, payload.get("iat")):
            raise credentials_exception

        token_data = TokenData(user_id=UUID(user_id_str))
    except Exception:
        raise credentials_exception

    user = await get_user_by_id(db, token_data.user_id)
    if user is None or not user.is_active:
        raise credentials_exception

    # Invalidate the consumed refresh token (rotation)
    if jti:
        revoke_token_jti(jti)

    # Issue fresh token pair
    user_role_str = user.role.value if hasattr(user.role, "value") else str(user.role)
    new_access_token = create_access_token(
        data={"sub": str(user.user_id), "email": user.email, "role": user_role_str}
    )
    new_refresh_token = create_refresh_token(
        data={"sub": str(user.user_id), "email": user.email, "role": user_role_str}
    )

    return Token(access_token=new_access_token, refresh_token=new_refresh_token)


@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout(
    logout_data: LogoutPayload | None = None,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Log out user and invalidate refresh token (SEC-04)."""
    from app.services.auth.service import jwt, revoke_token_jti, settings

    if logout_data and logout_data.refresh_token:
        try:
            payload = jwt.decode(
                logout_data.refresh_token,
                settings.JWT_SECRET_KEY,
                algorithms=[settings.JWT_ALGORITHM],
            )
            jti = payload.get("jti")
            if jti:
                revoke_token_jti(jti)
        except Exception:
            pass

    audit = AuditLog(
        user_id=current_user.user_id,
        action="USER_LOGOUT",
        resource_type="users",
        resource_id=current_user.user_id,
        outcome=AuditOutcome.SUCCESS,
        details={"email": current_user.email},
    )
    db.add(audit)
    await db.commit()
    return {"message": "Successfully logged out and session revoked."}


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_active_user)):
    """Get current user information."""
    return current_user