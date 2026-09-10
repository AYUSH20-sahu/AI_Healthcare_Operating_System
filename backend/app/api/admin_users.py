"""Admin user management and account provisioning API routes.

Enforces Global Authentication & Account Provisioning Rule (lines 480-686 of Master Prompt v6).
Only authorized Administrators can access these endpoints.
Every action is recorded in the immutable audit log.
"""

import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import AuditLog, AuditOutcome, Doctor, User, UserRole
from app.services.auth.rbac import require_admin
from app.services.auth.service import get_password_hash

router = APIRouter(prefix="/admin/users", tags=["admin-users"])


class UserProvisionRequest(BaseModel):
    """Schema for provisioning a user account by an administrator."""
    email: EmailStr
    password: str = Field(min_length=8)
    full_name: str
    role: str = Field(..., description="Role: doctor, nurse, receptionist, admin")
    specialty: Optional[str] = None
    license_number: Optional[str] = None
    hospital_affiliation: Optional[str] = None
    phone: Optional[str] = None


class UserStatusUpdate(BaseModel):
    is_active: bool


class PasswordResetRequest(BaseModel):
    new_password: str = Field(min_length=8)


class DoctorProfileSummary(BaseModel):
    doctor_id: uuid.UUID
    specialty: str
    license_number: str
    hospital_affiliation: Optional[str] = None
    phone: Optional[str] = None

    class Config:
        from_attributes = True


class AdminUserResponse(BaseModel):
    user_id: uuid.UUID
    email: str
    full_name: str
    role: str
    is_active: bool
    created_at: datetime
    doctor_profile: Optional[DoctorProfileSummary] = None

    class Config:
        from_attributes = True


class AdminUserListResponse(BaseModel):
    users: list[AdminUserResponse]
    total: int
    limit: int
    offset: int


@router.get("/", response_model=AdminUserListResponse)
async def list_users(
    role: Optional[str] = Query(None, description="Filter by role"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    search: Optional[str] = Query(None, description="Search email or full name"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(require_admin),
):
    """List all registered and provisioned users with administrative filtering."""
    query = select(User)

    if role:
        try:
            role_enum = UserRole(role.lower())
            query = query.where(User.role == role_enum)
        except ValueError:
            pass

    if is_active is not None:
        query = query.where(User.is_active == is_active)

    if search:
        search_pattern = f"%{search}%"
        query = query.where(
            or_(
                User.email.ilike(search_pattern),
                User.full_name.ilike(search_pattern),
            )
        )

    # Count total matching
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    # Fetch paginated with doctor profiles
    query = query.order_by(User.created_at.desc()).offset(offset).limit(limit)
    result = await db.execute(query)
    users = result.scalars().all()

    # Pre-fetch doctor profiles for doctors
    response_items = []
    for u in users:
        doc_summary = None
        if u.role == UserRole.DOCTOR:
            doc_res = await db.execute(select(Doctor).where(Doctor.user_id == u.user_id))
            doc = doc_res.scalar_one_or_none()
            if doc:
                doc_summary = DoctorProfileSummary(
                    doctor_id=doc.doctor_id,
                    specialty=doc.specialty,
                    license_number=doc.license_number,
                    hospital_affiliation=doc.hospital_affiliation,
                    phone=doc.phone,
                )

        response_items.append(
            AdminUserResponse(
                user_id=u.user_id,
                email=u.email,
                full_name=u.full_name,
                role=u.role.value if hasattr(u.role, "value") else str(u.role),
                is_active=u.is_active,
                created_at=u.created_at,
                doctor_profile=doc_summary,
            )
        )

    return AdminUserListResponse(
        users=response_items,
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post("/", response_model=AdminUserResponse, status_code=status.HTTP_201_CREATED)
async def provision_user(
    provision_data: UserProvisionRequest,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(require_admin),
):
    """Provision a new clinician or staff account.
    
    Doctors and staff roles cannot register publicly; they must be provisioned
    here by an authorized administrator with full audit logging.
    """
    # 1. Validate role
    try:
        assigned_role = UserRole(provision_data.role.lower())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid role: '{provision_data.role}'. Allowed: doctor, nurse, receptionist, admin, patient",
        )

    # 2. Check email uniqueness
    existing_user = await db.execute(
        select(User).where(User.email == provision_data.email)
    )
    if existing_user.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email address is already registered",
        )

    # 3. If DOCTOR, validate license number and required clinical fields
    if assigned_role == UserRole.DOCTOR:
        if not provision_data.license_number:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="License number is required for doctor provisioning",
            )
        if not provision_data.specialty:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Specialty is required for doctor provisioning",
            )

        existing_license = await db.execute(
            select(Doctor).where(Doctor.license_number == provision_data.license_number)
        )
        if existing_license.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Medical license {provision_data.license_number} is already in use",
            )

    # 4. Create User
    hashed_pwd = get_password_hash(provision_data.password)
    new_user = User(
        email=provision_data.email,
        hashed_password=hashed_pwd,
        full_name=provision_data.full_name,
        role=assigned_role,
        is_active=True,
    )
    db.add(new_user)
    await db.flush()

    # 5. Create Doctor profile if applicable
    doc_summary = None
    if assigned_role == UserRole.DOCTOR:
        new_doctor = Doctor(
            user_id=new_user.user_id,
            email=new_user.email,
            full_name=new_user.full_name,
            specialty=provision_data.specialty,
            license_number=provision_data.license_number,
            hospital_affiliation=provision_data.hospital_affiliation or "AI-HOS Central Health",
            phone=provision_data.phone,
        )
        db.add(new_doctor)
        await db.flush()
        doc_summary = DoctorProfileSummary(
            doctor_id=new_doctor.doctor_id,
            specialty=new_doctor.specialty,
            license_number=new_doctor.license_number,
            hospital_affiliation=new_doctor.hospital_affiliation,
            phone=new_doctor.phone,
        )

    # 6. Immutable Audit Log
    audit_entry = AuditLog(
        user_id=current_admin.user_id,
        action="ADMIN_PROVISION_USER",
        resource_type="users",
        resource_id=new_user.user_id,
        outcome=AuditOutcome.SUCCESS,
        details={
            "provisioned_email": new_user.email,
            "assigned_role": assigned_role.value,
            "provisioned_by_admin": str(current_admin.user_id),
            "license_number": provision_data.license_number if assigned_role == UserRole.DOCTOR else None,
        },
    )
    db.add(audit_entry)
    await db.commit()
    await db.refresh(new_user)

    return AdminUserResponse(
        user_id=new_user.user_id,
        email=new_user.email,
        full_name=new_user.full_name,
        role=new_user.role.value if hasattr(new_user.role, "value") else str(new_user.role),
        is_active=new_user.is_active,
        created_at=new_user.created_at,
        doctor_profile=doc_summary,
    )


@router.patch("/{user_id}/status", response_model=AdminUserResponse)
async def toggle_user_status(
    user_id: uuid.UUID,
    status_data: UserStatusUpdate,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(require_admin),
):
    """Activate or deactivate a user account.
    
    Deactivated users cannot authenticate or access any system APIs.
    """
    if user_id == current_admin.user_id and not status_data.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Administrators cannot deactivate their own active account",
        )

    result = await db.execute(select(User).where(User.user_id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    old_status = user.is_active
    user.is_active = status_data.is_active

    # Audit Log
    audit_entry = AuditLog(
        user_id=current_admin.user_id,
        action="ADMIN_TOGGLE_USER_STATUS",
        resource_type="users",
        resource_id=user.user_id,
        outcome=AuditOutcome.SUCCESS,
        details={
            "target_email": user.email,
            "old_status": old_status,
            "new_status": status_data.is_active,
            "modified_by_admin": str(current_admin.user_id),
        },
    )
    db.add(audit_entry)
    await db.commit()
    await db.refresh(user)

    return AdminUserResponse(
        user_id=user.user_id,
        email=user.email,
        full_name=user.full_name,
        role=user.role.value if hasattr(user.role, "value") else str(user.role),
        is_active=user.is_active,
        created_at=user.created_at,
    )


@router.post("/{user_id}/reset-password")
async def reset_user_password(
    user_id: uuid.UUID,
    reset_data: PasswordResetRequest,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(require_admin),
):
    """Reset a user's password directly by an administrator."""
    result = await db.execute(select(User).where(User.user_id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    user.hashed_password = get_password_hash(reset_data.new_password)

    # Audit Log
    audit_entry = AuditLog(
        user_id=current_admin.user_id,
        action="ADMIN_RESET_PASSWORD",
        resource_type="users",
        resource_id=user.user_id,
        outcome=AuditOutcome.SUCCESS,
        details={
            "target_email": user.email,
            "reset_by_admin": str(current_admin.user_id),
        },
    )
    db.add(audit_entry)
    await db.commit()

    return {"message": f"Password reset successfully for {user.email}"}
