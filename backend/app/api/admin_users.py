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
from app.services.auth.service import (
    check_credentials_available,
    get_password_hash,
    normalize_phone,
)

router = APIRouter(prefix="/admin/users", tags=["admin-users"])


class UserProvisionRequest(BaseModel):
    """Schema for provisioning a clinician or lead account by an administrator (4-Step Process)."""
    # Step 1: Personal & Demographics
    email: EmailStr
    password: str = Field(min_length=8)
    full_name: str
    role: str = Field(..., description="Role: doctor, head_physician, head_nurse, admin")
    phone: Optional[str] = None
    emergency_contact_phone: Optional[str] = None

    # Step 2: Professional Licensure & Credentials
    license_number: Optional[str] = None
    qualifications: Optional[str] = None
    experience_years: Optional[int] = 0
    specialty: Optional[str] = None

    # Step 3: Departmental Assignment & Clinical Setup
    department: Optional[str] = None
    designation: Optional[str] = None
    room_number: Optional[str] = None
    shift: Optional[str] = None
    hospital_affiliation: Optional[str] = None

    # Step 4: Governance & Review
    abdm_hpr_id: Optional[str] = None
    clinical_privileges: Optional[list[str]] = None
    background_verified: Optional[bool] = True


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
    department: Optional[str] = None
    designation: Optional[str] = None
    qualifications: Optional[str] = None
    experience_years: Optional[int] = None
    room_number: Optional[str] = None
    shift: Optional[str] = None
    is_head_physician: Optional[bool] = False

    class Config:
        from_attributes = True


class AdminUserResponse(BaseModel):
    user_id: uuid.UUID
    email: str
    full_name: str
    role: str
    phone: Optional[str] = None
    is_active: bool
    created_at: datetime
    department: Optional[str] = None
    designation: Optional[str] = None
    qualifications: Optional[str] = None
    experience_years: Optional[int] = None
    room_number: Optional[str] = None
    shift: Optional[str] = None
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
    department: Optional[str] = Query(None, description="Filter by department"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(require_admin),
):
    """List all registered and provisioned users with administrative filtering scoped to organization."""
    query = select(User)

    # Multi-tenant: If not Super Admin, scope users strictly to Admin's organization
    if current_admin.role != UserRole.SUPER_ADMIN and current_admin.organization_id:
        query = query.where(User.organization_id == current_admin.organization_id)

    if role:
        try:
            role_enum = UserRole(role.lower())
            query = query.where(User.role == role_enum)
        except ValueError:
            pass

    if is_active is not None:
        query = query.where(User.is_active == is_active)

    if department:
        query = query.where(User.department.ilike(f"%{department.strip()}%"))

    if search:
        search_pattern = f"%{search}%"
        query = query.where(
            or_(
                User.email.ilike(search_pattern),
                User.full_name.ilike(search_pattern),
                User.phone.ilike(search_pattern),
            )
        )

    # Count total matching
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    # Fetch paginated
    query = query.order_by(User.created_at.desc()).offset(offset).limit(limit)
    result = await db.execute(query)
    users = result.scalars().all()

    # Pre-fetch doctor profiles
    response_items = []
    for u in users:
        doc_summary = None
        if u.role in (UserRole.DOCTOR, UserRole.HEAD_PHYSICIAN):
            doc_res = await db.execute(select(Doctor).where(Doctor.user_id == u.user_id))
            doc = doc_res.scalar_one_or_none()
            if doc:
                doc_summary = DoctorProfileSummary(
                    doctor_id=doc.doctor_id,
                    specialty=doc.specialty,
                    license_number=doc.license_number,
                    hospital_affiliation=doc.hospital_affiliation,
                    phone=doc.phone,
                    department=doc.department,
                    designation=doc.designation,
                    qualifications=doc.qualifications,
                    experience_years=doc.experience_years,
                    room_number=doc.room_number,
                    shift=doc.shift,
                    is_head_physician=doc.is_head_physician,
                )

        response_items.append(
            AdminUserResponse(
                user_id=u.user_id,
                email=u.email,
                full_name=u.full_name,
                role=u.role.value if hasattr(u.role, "value") else str(u.role),
                phone=u.phone,
                is_active=u.is_active,
                created_at=u.created_at,
                department=u.department,
                designation=u.designation,
                qualifications=u.qualifications,
                experience_years=u.experience_years,
                room_number=u.room_number,
                shift=u.shift,
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
    """Provision a new clinician or departmental leadership account (4-Step Process).
    
    Hospital Admins can create all Doctor profiles, only one Head Nurse, and only one Head Physician.
    Junior staff are subsequently provisioned by their respective departmental heads.
    """
    # 1. Validate role
    try:
        assigned_role = UserRole(provision_data.role.lower())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid role: '{provision_data.role}'. Allowed for hospital provisioning: doctor, head_physician, head_nurse, nurse, receptionist",
        )

    # 1a. Enforce Super Admin Boundary for Admin provisioning (SEC-06)
    if assigned_role in (UserRole.ADMIN, UserRole.SUPER_ADMIN):
        from app.core.config import settings
        if current_admin.email.lower() != settings.SUPER_ADMIN_EMAIL.lower():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the institutional Super Administrator can provision new Administrator accounts.",
            )

    # 1b. Role constraints for Hospital Admin
    if current_admin.role != UserRole.SUPER_ADMIN:
        allowed_admin_roles = (
            UserRole.DOCTOR,
            UserRole.HEAD_PHYSICIAN,
            UserRole.HEAD_NURSE,
            UserRole.NURSE,
            UserRole.RECEPTIONIST,
            UserRole.ADMIN,
        )
        if assigned_role not in allowed_admin_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Hospital Admin can only provision clinical and authorized staff accounts. Selected: {assigned_role.value}",
            )

    # 1c. Enforce Only ONE Head Physician per organization
    if assigned_role == UserRole.HEAD_PHYSICIAN:
        existing_head_physician = await db.execute(
            select(User).where(
                User.organization_id == current_admin.organization_id,
                User.role == UserRole.HEAD_PHYSICIAN,
                User.is_active,
            )
        )
        if existing_head_physician.scalars().first():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A Head Physician (Chief Medical Officer) has already been provisioned for this hospital. Only one Head Physician is permitted.",
            )

    # 1d. Enforce Only ONE Head Nurse per organization
    if assigned_role == UserRole.HEAD_NURSE:
        existing_head_nurse = await db.execute(
            select(User).where(
                User.organization_id == current_admin.organization_id,
                User.role == UserRole.HEAD_NURSE,
                User.is_active,
            )
        )
        if existing_head_nurse.scalars().first():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A Head Nurse (Nursing Superintendent) has already been provisioned for this hospital. Only one Head Nurse is permitted.",
            )

    # 2. Check credentials uniqueness across all account types (Universal Guard)
    clean_phone = normalize_phone(provision_data.phone) if provision_data.phone else None
    await check_credentials_available(db, email=provision_data.email, phone=clean_phone)

    # 3. If DOCTOR or HEAD_PHYSICIAN, validate medical license number and required clinical fields
    if assigned_role in (UserRole.DOCTOR, UserRole.HEAD_PHYSICIAN):
        if not provision_data.license_number:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Medical Council Registration / License number is required for doctor provisioning.",
            )

        existing_license = await db.execute(
            select(Doctor).where(Doctor.license_number == provision_data.license_number)
        )
        if existing_license.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Medical license {provision_data.license_number} is already in use by another practitioner.",
            )

    # 4. If HEAD_NURSE, require nursing registration number
    if assigned_role == UserRole.HEAD_NURSE:
        if not provision_data.license_number:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Nursing Council Registration number is required for Head Nurse provisioning.",
            )

    # 5. Create User
    hashed_pwd = get_password_hash(provision_data.password)
    new_user = User(
        email=provision_data.email,
        phone=clean_phone,
        hashed_password=hashed_pwd,
        full_name=provision_data.full_name,
        role=assigned_role,
        organization_id=current_admin.organization_id,
        department=provision_data.department,
        designation=provision_data.designation or ("Chief Medical Officer" if assigned_role == UserRole.HEAD_PHYSICIAN else "Nursing Superintendent" if assigned_role == UserRole.HEAD_NURSE else "Consultant Doctor"),
        qualifications=provision_data.qualifications,
        experience_years=provision_data.experience_years,
        room_number=provision_data.room_number,
        shift=provision_data.shift or "Morning (08:00 - 16:00)",
        is_active=True,
    )
    db.add(new_user)
    await db.flush()

    # 6. Create Doctor profile if DOCTOR or HEAD_PHYSICIAN
    doc_summary = None
    if assigned_role in (UserRole.DOCTOR, UserRole.HEAD_PHYSICIAN):
        new_doctor = Doctor(
            user_id=new_user.user_id,
            email=new_user.email,
            full_name=new_user.full_name,
            specialty=provision_data.specialty or provision_data.department or "General Medicine",
            license_number=provision_data.license_number,
            hospital_affiliation=provision_data.hospital_affiliation or "AI-HOS Medical Center",
            phone=clean_phone,
            department=provision_data.department,
            designation=new_user.designation,
            qualifications=provision_data.qualifications,
            experience_years=provision_data.experience_years,
            room_number=provision_data.room_number,
            shift=new_user.shift,
            is_head_physician=(assigned_role == UserRole.HEAD_PHYSICIAN),
        )
        db.add(new_doctor)
        await db.flush()
        doc_summary = DoctorProfileSummary(
            doctor_id=new_doctor.doctor_id,
            specialty=new_doctor.specialty,
            license_number=new_doctor.license_number,
            hospital_affiliation=new_doctor.hospital_affiliation,
            phone=new_doctor.phone,
            department=new_doctor.department,
            designation=new_doctor.designation,
            qualifications=new_doctor.qualifications,
            experience_years=new_doctor.experience_years,
            room_number=new_doctor.room_number,
            shift=new_doctor.shift,
            is_head_physician=new_doctor.is_head_physician,
        )

    # 7. Immutable Audit Log
    audit_entry = AuditLog(
        user_id=current_admin.user_id,
        action="ADMIN_PROVISION_USER",
        resource_type="users",
        resource_id=new_user.user_id,
        outcome=AuditOutcome.SUCCESS,
        details={
            "provisioned_email": new_user.email,
            "assigned_role": assigned_role.value,
            "department": provision_data.department,
            "designation": new_user.designation,
            "provisioned_by_admin": str(current_admin.user_id),
            "license_number": provision_data.license_number,
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
        phone=new_user.phone,
        is_active=new_user.is_active,
        created_at=new_user.created_at,
        department=new_user.department,
        designation=new_user.designation,
        qualifications=new_user.qualifications,
        experience_years=new_user.experience_years,
        room_number=new_user.room_number,
        shift=new_user.shift,
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
    if str(user_id) == str(current_admin.user_id) and not status_data.is_active:
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

    # Revoke sessions if account deactivated (SEC-04)
    if not status_data.is_active:
        from app.services.auth.service import revoke_all_user_tokens
        revoke_all_user_tokens(str(user.user_id))

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

    # Invalidate all existing sessions upon password reset (SEC-04)
    from app.services.auth.service import revoke_all_user_tokens
    revoke_all_user_tokens(str(user.user_id))

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


class UserRoleChangeRequest(BaseModel):
    """Schema for updating a user's organizational role."""
    new_role: str = Field(..., description="Target role: doctor, nurse, receptionist, admin, patient")
    specialty: Optional[str] = Field(None, description="Required if promoted to doctor and no profile exists")
    license_number: Optional[str] = Field(None, description="Required if promoted to doctor and no profile exists")


@router.patch("/{user_id}/role", response_model=AdminUserResponse)
async def update_user_role(
    user_id: uuid.UUID,
    role_data: UserRoleChangeRequest,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(require_admin),
):
    """Assign or change a user's role with full audit trail.
    
    Admins cannot demote their own account to prevent lockout.
    Promoting a user to DOCTOR initializes a doctor profile if needed.
    """
    try:
        assigned_role = UserRole(role_data.new_role.lower())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid role: '{role_data.new_role}'. Allowed: doctor, nurse, receptionist, admin, patient",
        )

    # Enforce Super Admin Boundary (SEC-06)
    if assigned_role == UserRole.ADMIN:
        from app.core.config import settings
        if current_admin.email.lower() != settings.SUPER_ADMIN_EMAIL.lower():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the institutional Super Administrator can promote accounts to the Administrator role.",
            )

    if str(user_id) == str(current_admin.user_id) and assigned_role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Administrators cannot demote their own account",
        )

    result = await db.execute(select(User).where(User.user_id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    old_role = user.role.value if hasattr(user.role, "value") else str(user.role)
    user.role = assigned_role

    doc_summary = None
    if assigned_role == UserRole.DOCTOR:
        doc_res = await db.execute(select(Doctor).where(Doctor.user_id == user.user_id))
        doc = doc_res.scalar_one_or_none()
        if not doc:
            if not role_data.license_number or not str(role_data.license_number).strip():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="A verified medical license number is strictly required when promoting a user to Doctor. Synthetic identifiers are prohibited.",
                )
            if not role_data.specialty or not str(role_data.specialty).strip():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Clinical specialty is strictly required when promoting a user to Doctor.",
                )

            clean_lic = str(role_data.license_number).strip()
            existing_lic = await db.execute(
                select(Doctor).where(Doctor.license_number == clean_lic)
            )
            if existing_lic.scalar_one_or_none():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Medical license {clean_lic} is already registered to another clinician.",
                )

            # Create verified doctor profile
            doc = Doctor(
                user_id=user.user_id,
                email=user.email,
                full_name=user.full_name,
                specialty=str(role_data.specialty).strip(),
                license_number=clean_lic,
                hospital_affiliation="AI-HOS Central Health",
            )
            db.add(doc)
            await db.flush()
        doc_summary = DoctorProfileSummary(
            doctor_id=doc.doctor_id,
            specialty=doc.specialty,
            license_number=doc.license_number,
            hospital_affiliation=doc.hospital_affiliation,
            phone=doc.phone,
        )

    audit_entry = AuditLog(
        user_id=current_admin.user_id,
        action="ADMIN_CHANGE_USER_ROLE",
        resource_type="users",
        resource_id=user.user_id,
        outcome=AuditOutcome.SUCCESS,
        details={
            "target_email": user.email,
            "old_role": old_role,
            "new_role": assigned_role.value,
            "changed_by_admin": str(current_admin.user_id),
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
        doctor_profile=doc_summary,
    )


@router.delete("/{user_id}")
async def deactivate_or_delete_user(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(require_admin),
):
    """Deactivate or remove a user account.
    
    Prevents self-deletion by administrators.
    """
    if str(user_id) == str(current_admin.user_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Administrators cannot delete their own account",
        )

    result = await db.execute(select(User).where(User.user_id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Soft deactivate to maintain referential integrity in audits & medical records
    user.is_active = False

    audit_entry = AuditLog(
        user_id=current_admin.user_id,
        action="ADMIN_DEACTIVATE_USER",
        resource_type="users",
        resource_id=user.user_id,
        outcome=AuditOutcome.SUCCESS,
        details={
            "target_email": user.email,
            "deactivated_by_admin": str(current_admin.user_id),
        },
    )
    db.add(audit_entry)
    await db.commit()

    return {"detail": "User account deactivated successfully", "user_id": str(user_id)}

