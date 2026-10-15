import secrets
import urllib.parse
import uuid

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, EmailStr, Field, model_validator
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import AuditLog, AuditOutcome, Organization, Patient, User, UserRole
from app.services.auth.service import (
    Token,
    UserCreate,
    UserLogin,
    UserResponse,
    UserSignupRequest,
    authenticate_user,
    check_credentials_available,
    create_access_token,
    create_refresh_token,
    create_user,
    get_current_active_user,
    get_password_hash,
    normalize_phone,
)

router = APIRouter(prefix="/auth", tags=["auth"])


class PatientRegisterRequest(BaseModel):
    full_name: str
    email: EmailStr
    phone: str
    password: str


class PatientLoginRequest(BaseModel):
    identifier: str  # Email or Mobile Phone
    password: str


class GoogleAuthRequest(BaseModel):
    email: EmailStr
    full_name: str | None = None
    avatar_url: str | None = None
    google_id: str | None = None
    credential: str | None = None


class GoogleOAuthCallbackRequest(BaseModel):
    code: str
    redirect_uri: str | None = None


class CheckAvailabilityRequest(BaseModel):
    email: EmailStr | None = None
    phone: str | None = None


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


class OrgRegisterRequest(BaseModel):
    # Step 1: Admin & Basic Facility Information
    admin_name: str
    email: EmailStr
    phone: str | None = None
    password: str
    organization_name: str
    organization_code: str | None = None
    organization_address: str | None = None

    # Step 2: Clinical Facility & Department Configuration
    facility_type: str = "Multi-Specialty Hospital"
    departments: list[str] = Field(default_factory=list)
    total_beds: int = Field(default=150, ge=1, le=10000, description="Total bed capacity (1 to 10,000)")
    icu_beds: int = Field(default=24, ge=0, le=2500, description="Dedicated ICU beds (0 to 2,500)")
    has_emergency: bool = True
    has_ambulance: bool = True

    # Step 3: Regulatory & Licensing Credentials
    license_number: str | None = None
    abdm_facility_id: str | None = None
    insurance_network_code: str | None = None

    # Step 4: Operational Settings & Safety Gate
    emergency_hotline: str | None = None
    operating_hours: str = "24/7 Emergency & Inpatient"
    clinical_review_policy: str = "Strict Doctor Sign-Off Required"

    @model_validator(mode="after")
    def validate_beds(self):
        if self.icu_beds > self.total_beds:
            raise ValueError(f"Dedicated ICU bed count ({self.icu_beds}) cannot exceed total inpatient bed capacity ({self.total_beds}).")
        return self


@router.post("/patient/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def patient_register(data: PatientRegisterRequest, db: AsyncSession = Depends(get_db)):
    """Register a new patient account with both email and mobile phone number."""
    clean_phone = normalize_phone(data.phone) or data.phone.strip()

    # Verify that neither email nor mobile phone is already linked to ANY account
    await check_credentials_available(db, email=data.email, phone=clean_phone)

    # Create User record
    user_create = UserCreate(
        email=data.email,
        password=data.password,
        full_name=data.full_name,
        role=UserRole.PATIENT.value,
        phone=clean_phone,
    )
    user = await create_user(db, user_create, role=UserRole.PATIENT.value)

    # Create associated Patient profile
    patient_profile = Patient(
        user_id=user.user_id,
        full_name=user.full_name,
        email=user.email,
        phone=clean_phone,
    )
    db.add(patient_profile)

    # Immutable Audit Log
    audit = AuditLog(
        user_id=user.user_id,
        action="PATIENT_REGISTRATION",
        resource_type="users",
        resource_id=user.user_id,
        outcome=AuditOutcome.SUCCESS,
        details={"role": UserRole.PATIENT.value, "email": user.email, "phone": clean_phone},
    )
    db.add(audit)
    await db.commit()
    await db.refresh(user)
    return user


@router.post("/patient/login", response_model=Token)
async def patient_login(form_data: PatientLoginRequest, db: AsyncSession = Depends(get_db)):
    """Patient login supporting either email or mobile phone number."""
    if not form_data.identifier or not form_data.identifier.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email address or mobile phone number is required.",
        )

    user = await authenticate_user(db, form_data.identifier.strip(), form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials. Please verify your email/phone and password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Enforce that patient login endpoint only serves patients
    if user.role != UserRole.PATIENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This portal is for patients only. Hospital staff must sign in at the clinical portal.",
        )

    user_role_str = user.role.value if hasattr(user.role, "value") else str(user.role)
    token_data = {
        "sub": str(user.user_id),
        "email": user.email,
        "role": user_role_str,
    }
    access_token = create_access_token(data=token_data)
    refresh_token = create_refresh_token(data=token_data)

    return Token(access_token=access_token, refresh_token=refresh_token)


@router.post("/check-availability")
async def check_availability(
    data: CheckAvailabilityRequest,
    db: AsyncSession = Depends(get_db),
):
    """Pre-flight check to verify that an email or phone number is available before registration.
    
    If either already exists, raises HTTP 400 instructing the user to log in with their credentials.
    """
    clean_phone = normalize_phone(data.phone) if data.phone else None
    await check_credentials_available(db, email=data.email, phone=clean_phone)
    return {"available": True, "message": "Credentials are available for new registration."}


async def _authenticate_or_register_google_user(
    db: AsyncSession,
    email: str,
    full_name: str | None = None,
    google_id: str | None = None,
    avatar_url: str | None = None,
) -> Token:
    """Helper to authenticate an existing patient or auto-provision a new patient user from verified Google OAuth details."""
    clean_email = email.strip().lower()
    if not clean_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Valid Google account email address is required.",
        )

    # 1. Check if user already exists
    result = await db.execute(
        select(User).where(func.lower(User.email) == clean_email)
    )
    user = result.scalar_one_or_none()

    if user:
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This account has been deactivated. Please contact hospital support.",
            )
        # Verify role: patient login portal accommodates patients
        if user.role != UserRole.PATIENT:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This account is registered with a clinical/administrative role. Please sign in via the clinical portal.",
            )

        audit = AuditLog(
            user_id=user.user_id,
            action="GOOGLE_SSO_LOGIN",
            resource_type="users",
            resource_id=user.user_id,
            outcome=AuditOutcome.SUCCESS,
            details={"email": user.email, "role": user.role.value if hasattr(user.role, "value") else str(user.role)},
        )
        db.add(audit)
        await db.commit()
    else:
        # 2. Automatically register new patient with Google account details
        user_name = (full_name or "").strip()
        if not user_name:
            user_name = clean_email.split("@")[0].replace(".", " ").title()

        random_secret = f"GAuth_{secrets.token_urlsafe(28)}!9a"
        hashed = get_password_hash(random_secret)

        new_user = User(
            user_id=uuid.uuid4(),
            email=clean_email,
            full_name=user_name,
            hashed_password=hashed,
            role=UserRole.PATIENT,
            is_active=True,
        )
        db.add(new_user)
        await db.flush()

        # Create associated Patient profile
        patient_profile = Patient(
            user_id=new_user.user_id,
            full_name=new_user.full_name,
            email=clean_email,
        )
        db.add(patient_profile)

        audit = AuditLog(
            user_id=new_user.user_id,
            action="GOOGLE_SSO_AUTO_REGISTER_AND_LOGIN",
            resource_type="users",
            resource_id=new_user.user_id,
            outcome=AuditOutcome.SUCCESS,
            details={
                "email": clean_email,
                "full_name": user_name,
                "role": UserRole.PATIENT.value,
                "google_id": google_id,
            },
        )
        db.add(audit)
        await db.commit()
        await db.refresh(new_user)
        user = new_user

    user_role_str = user.role.value if hasattr(user.role, "value") else str(user.role)
    token_data = {
        "sub": str(user.user_id),
        "email": user.email,
        "role": user_role_str,
    }
    if user.organization_id:
        token_data["organization_id"] = str(user.organization_id)

    access_token = create_access_token(data=token_data)
    refresh_token = create_refresh_token(data=token_data)

    return Token(access_token=access_token, refresh_token=refresh_token)


@router.get("/google/url")
async def get_google_auth_url(redirect_uri: str | None = None):
    """Generate official Google Accounts OAuth 2.0 authorization URL for accounts.google.com."""
    from app.core.config import settings

    client_id = settings.GOOGLE_CLIENT_ID
    if not client_id or not client_id.strip():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google OAuth Client ID is not configured. Please add GOOGLE_CLIENT_ID in your .env file.",
        )

    cb_uri = redirect_uri or settings.GOOGLE_REDIRECT_URI or f"{settings.FRONTEND_URL}/auth/callback/google"
    params = {
        "client_id": client_id.strip(),
        "redirect_uri": cb_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "prompt": "select_account",
    }
    auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urllib.parse.urlencode(params)}"
    return {
        "auth_url": auth_url,
        "client_id": client_id,
        "redirect_uri": cb_uri,
    }


@router.get("/google/login")
async def google_login_redirect(redirect_uri: str | None = None):
    """Direct browser redirect to official accounts.google.com OAuth screen."""
    from app.core.config import settings

    client_id = settings.GOOGLE_CLIENT_ID
    frontend_base = (getattr(settings, "FRONTEND_URL", None) or "http://localhost:3000").rstrip("/")
    if not client_id or not client_id.strip():
        msg = urllib.parse.quote("Google OAuth is not configured. Please set GOOGLE_CLIENT_ID in .env.")
        return RedirectResponse(url=f"{frontend_base}/patient/login?error={msg}")

    cb_uri = redirect_uri or settings.GOOGLE_REDIRECT_URI or f"{frontend_base}/auth/callback/google"
    params = {
        "client_id": client_id.strip(),
        "redirect_uri": cb_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "prompt": "select_account",
    }
    auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urllib.parse.urlencode(params)}"
    return RedirectResponse(url=auth_url)


@router.post("/google/callback", response_model=Token)
async def google_oauth_callback(data: GoogleOAuthCallbackRequest, db: AsyncSession = Depends(get_db)):
    """Exchange authorization code from accounts.google.com for Google tokens, fetch profile, and authenticate."""
    from app.core.config import settings

    client_id = settings.GOOGLE_CLIENT_ID
    client_secret = settings.GOOGLE_CLIENT_SECRET
    if not client_id or not client_secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google OAuth credentials (GOOGLE_CLIENT_ID & GOOGLE_CLIENT_SECRET) are not configured in backend .env.",
        )

    cb_uri = data.redirect_uri or settings.GOOGLE_REDIRECT_URI or f"{settings.FRONTEND_URL}/auth/callback/google"

    # 1. Exchange authorization code for Google access token
    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            token_res = await client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "code": data.code.strip(),
                    "client_id": client_id.strip(),
                    "client_secret": client_secret.strip(),
                    "redirect_uri": cb_uri,
                    "grant_type": "authorization_code",
                },
                headers={"Accept": "application/json"},
            )
            token_json = token_res.json()
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Failed to connect to Google OAuth token endpoint: {exc}",
            )

        if token_res.status_code != 200:
            error_desc = token_json.get("error_description") or token_json.get("error") or "Failed to exchange code"
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Google OAuth token exchange failed: {error_desc}",
            )

        google_access_token = token_json.get("access_token")
        if not google_access_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Google OAuth response did not contain access_token.",
            )

        # 2. Fetch user profile from Google UserInfo endpoint
        try:
            userinfo_res = await client.get(
                "https://www.googleapis.com/oauth2/v3/userinfo",
                headers={"Authorization": f"Bearer {google_access_token}"},
            )
            google_profile = userinfo_res.json()
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Failed to fetch user info from Google: {exc}",
            )

        if userinfo_res.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Could not verify user info from Google Accounts.",
            )

    google_email = google_profile.get("email")
    if not google_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google account did not return a verified email address.",
        )

    return await _authenticate_or_register_google_user(
        db=db,
        email=google_email,
        full_name=google_profile.get("name"),
        google_id=google_profile.get("sub"),
        avatar_url=google_profile.get("picture"),
    )


@router.get("/google/callback")
async def google_oauth_callback_redirect(
    code: str | None = None,
    error: str | None = None,
    error_description: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Direct browser callback handler from accounts.google.com."""
    from app.core.config import settings

    frontend_base = (getattr(settings, "FRONTEND_URL", None) or "http://localhost:3000").rstrip("/")
    if error or not code:
        err_msg = error_description or error or "Google authentication cancelled or failed."
        return RedirectResponse(url=f"{frontend_base}/patient/login?error={urllib.parse.quote(err_msg)}")

    try:
        tokens = await google_oauth_callback(
            data=GoogleOAuthCallbackRequest(code=code),
            db=db,
        )
        return RedirectResponse(
            url=f"{frontend_base}/auth/callback/google?access_token={tokens.access_token}&refresh_token={tokens.refresh_token}"
        )
    except HTTPException as exc:
        return RedirectResponse(url=f"{frontend_base}/patient/login?error={urllib.parse.quote(exc.detail)}")
    except Exception as exc:
        return RedirectResponse(url=f"{frontend_base}/patient/login?error={urllib.parse.quote(str(exc))}")


@router.post("/google", response_model=Token)
async def google_auth(data: GoogleAuthRequest, db: AsyncSession = Depends(get_db)):
    """Authenticate or register a patient via Google account payload."""
    return await _authenticate_or_register_google_user(
        db=db,
        email=data.email,
        full_name=data.full_name,
        google_id=data.google_id,
        avatar_url=data.avatar_url,
    )


@router.post("/register-org", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_organization(data: OrgRegisterRequest, db: AsyncSession = Depends(get_db)):
    """Self-serve registration: creates a new Healthcare Organization and sets the registrant as its Administrator."""
    clean_phone = normalize_phone(data.phone) if data.phone else None

    # Verify that neither admin email nor mobile phone is already linked to ANY account
    await check_credentials_available(db, email=data.email, phone=clean_phone)

    # Generate or format code
    org_code = data.organization_code.strip().upper() if data.organization_code else None
    if not org_code:
        # Generate code from organization name initials + random digits
        import random
        initials = "".join([w[0] for w in data.organization_name.split()[:3]]).upper()
        if not initials or len(initials) < 2:
            initials = "ORG"
        org_code = f"{initials}-{random.randint(100, 999)}"

    # Check if org name or code exists
    existing_org = await db.execute(
        select(Organization).where(
            (Organization.name == data.organization_name) | (Organization.code == org_code)
        )
    )
    if existing_org.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An organization with this name or code already exists.",
        )

    # Create Organization with full medical configuration
    new_org = Organization(
        name=data.organization_name.strip(),
        code=org_code,
        address=data.organization_address,
        contact_email=data.email,
        contact_phone=data.phone,
        facility_type=data.facility_type,
        departments=data.departments or [],
        total_beds=data.total_beds or 0,
        icu_beds=data.icu_beds or 0,
        has_emergency=data.has_emergency,
        has_ambulance=data.has_ambulance,
        license_number=data.license_number,
        abdm_facility_id=data.abdm_facility_id,
        insurance_network_code=data.insurance_network_code,
        emergency_hotline=data.emergency_hotline,
        operating_hours=data.operating_hours,
        clinical_review_policy=data.clinical_review_policy,
        is_active=True,
    )
    db.add(new_org)
    await db.flush()

    # Create Administrator User for this Organization
    clean_phone = data.phone.strip() if data.phone else None
    user_create = UserCreate(
        email=data.email,
        password=data.password,
        full_name=data.admin_name.strip(),
        role=UserRole.ADMIN.value,
        phone=clean_phone,
        organization_id=new_org.organization_id,
    )
    user = await create_user(db, user_create, role=UserRole.ADMIN.value)

    # Audit log
    audit = AuditLog(
        user_id=user.user_id,
        action="REGISTER_ORGANIZATION_AND_ADMIN",
        resource_type="organizations",
        resource_id=new_org.organization_id,
        outcome=AuditOutcome.SUCCESS,
        details={
            "organization_name": new_org.name,
            "organization_code": new_org.code,
            "admin_email": user.email,
        },
    )
    db.add(audit)
    await db.commit()
    await db.refresh(user)
    return user


@router.post("/signup", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def signup(user_data: UserSignupRequest, db: AsyncSession = Depends(get_db)):
    clean_phone = normalize_phone(getattr(user_data, "phone", None))

    # Verify that neither email nor mobile phone is already linked to ANY account
    await check_credentials_available(db, email=user_data.email, phone=clean_phone)
    user_create = UserCreate(
        email=user_data.email,
        password=user_data.password,
        full_name=user_data.full_name,
        role=UserRole.PATIENT.value,
        phone=clean_phone,
    )
    user = await create_user(db, user_create, role=UserRole.PATIENT.value)

    # Automatically create associated Patient profile
    patient_profile = Patient(
        user_id=user.user_id,
        full_name=user.full_name,
        email=user.email,
        phone=clean_phone,
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
    """Login and get access + refresh tokens. Supports email or mobile phone number."""
    identifier = form_data.identifier or form_data.email or form_data.phone
    if not identifier or not identifier.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email address or mobile phone number is required",
        )

    user = await authenticate_user(db, identifier.strip(), form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email, phone number, or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_role_str = user.role.value if hasattr(user.role, "value") else str(user.role)
    token_data = {
        "sub": str(user.user_id),
        "email": user.email,
        "role": user_role_str,
    }
    if user.organization_id:
        token_data["organization_id"] = str(user.organization_id)

    access_token = create_access_token(data=token_data)
    refresh_token = create_refresh_token(data=token_data)
    
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


@router.post("/forgot-password", status_code=status.HTTP_200_OK)
async def forgot_password(
    data: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    """Initiate password reset flow for a registered user email.
    
    Verifies the email exists in database. If found, generates a 30-minute signed reset token,
    dispatches an HTML email containing the reset link, and writes an audit log.
    """
    from datetime import datetime, timedelta, timezone
    from app.core.config import settings
    from app.services.auth.service import jwt
    from app.services.notifications.email_service import send_password_reset_email

    clean_email = data.email.strip().lower()
    stmt = select(User).where(func.lower(User.email) == clean_email)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No account is registered under '{data.email}'. Please verify the email address or register a new account.",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This account has been deactivated. Please contact hospital support.",
        )

    # Generate secure password reset JWT token (30-minute validity)
    token_jti = str(uuid.uuid4())
    now_utc = datetime.now(timezone.utc)
    exp_utc = now_utc + timedelta(minutes=30)

    token_payload = {
        "sub": str(user.user_id),
        "email": user.email,
        "type": "password_reset",
        "jti": token_jti,
        "iat": int(now_utc.timestamp()),
        "exp": int(exp_utc.timestamp()),
    }
    reset_token = jwt.encode(token_payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

    frontend_base = (getattr(settings, "FRONTEND_URL", None) or "http://localhost:3000").rstrip("/")
    reset_url = f"{frontend_base}/patient/reset-password?token={reset_token}"

    user_name = user.full_name or "Valued Patient"
    email_sent = await send_password_reset_email(
        to_email=user.email,
        user_name=user_name,
        reset_url=reset_url,
        expires_in_minutes=30,
    )

    audit = AuditLog(
        user_id=user.user_id,
        action="PASSWORD_RESET_REQUESTED",
        resource_type="users",
        resource_id=user.user_id,
        outcome=AuditOutcome.SUCCESS,
        details={"email": user.email, "email_dispatched": email_sent},
    )
    db.add(audit)
    await db.commit()

    return {
        "message": f"Password reset instructions have been sent to {user.email}.",
        "email": user.email,
        "reset_url": reset_url,
    }


@router.post("/reset-password", status_code=status.HTTP_200_OK)
async def reset_password(
    data: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    """Validate reset token and set a new password for the user."""
    from datetime import datetime, timezone
    from uuid import UUID
    from app.core.config import settings
    from app.core.security import validate_password_strength
    from app.services.auth.service import (
        get_password_hash,
        get_user_by_id,
        is_token_jti_revoked,
        jwt,
        revoke_all_user_tokens,
        revoke_token_jti,
    )

    if not data.token or not data.token.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reset token is required.",
        )

    # Decode and validate the reset token
    try:
        payload = jwt.decode(
            data.token.strip(),
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The password reset link has expired. Please request a new password reset email.",
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or malformed password reset link.",
        )

    if payload.get("type") != "password_reset":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid token type for password reset.",
        )

    jti = payload.get("jti")
    if not jti or is_token_jti_revoked(jti):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This password reset link has already been used. Please request a new one if needed.",
        )

    user_id_str = payload.get("sub")
    if not user_id_str:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid reset token payload: missing user identification.",
        )

    # Enforce password strength
    is_valid, err_msg = validate_password_strength(data.new_password)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=err_msg or "Password must be at least 8 characters with uppercase, lowercase, numbers, and special characters.",
        )

    user = await get_user_by_id(db, UUID(user_id_str))
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User account not found or has been deactivated.",
        )

    # Update password and timestamps
    user.hashed_password = get_password_hash(data.new_password)
    user.updated_at = datetime.now(timezone.utc)

    # Invalidate this reset token JTI immediately (single-use)
    revoke_token_jti(jti)
    # Revoke all outstanding user login sessions so they must log in with their new credentials
    revoke_all_user_tokens(str(user.user_id))

    audit = AuditLog(
        user_id=user.user_id,
        action="PASSWORD_RESET_COMPLETED",
        resource_type="users",
        resource_id=user.user_id,
        outcome=AuditOutcome.SUCCESS,
        details={"email": user.email},
    )
    db.add(audit)
    await db.commit()

    return {
        "message": "Your password has been successfully reset! You can now log in with your new credentials.",
        "email": user.email,
    }