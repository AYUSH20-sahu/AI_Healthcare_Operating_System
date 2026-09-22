"""Auth API routes."""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field, model_validator
from sqlalchemy import select
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