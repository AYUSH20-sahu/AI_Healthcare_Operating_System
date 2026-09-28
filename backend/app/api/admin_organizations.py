"""Multi-Tenant Organization Management API routes.

Enables Super Administrators to manage healthcare organizations and their designated admins.
Allows Organization Admins to view and update their own organization profile.
"""

import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import AuditLog, AuditOutcome, Organization, User, UserRole
from app.services.auth.rbac import require_admin, require_super_admin
from app.services.auth.service import (
    UserCreate,
    check_credentials_available,
    create_user,
    get_current_active_user,
    get_user_by_email,
    normalize_phone,
)

router = APIRouter(prefix="/admin/organizations", tags=["admin-organizations"])


# =============================================================================
# Schemas
# =============================================================================

class AdminSummary(BaseModel):
    user_id: uuid.UUID
    full_name: str
    email: str
    phone: Optional[str] = None

    class Config:
        from_attributes = True


class OrgStats(BaseModel):
    total_users: int = 0
    total_doctors: int = 0
    total_patients: int = 0


class OrganizationResponse(BaseModel):
    organization_id: uuid.UUID
    name: str
    code: str
    description: Optional[str] = None
    address: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    is_active: bool
    facility_type: Optional[str] = None
    departments: Optional[list[str]] = None
    total_beds: Optional[int] = None
    icu_beds: Optional[int] = None
    has_emergency: Optional[bool] = None
    has_ambulance: Optional[bool] = None
    license_number: Optional[str] = None
    abdm_facility_id: Optional[str] = None
    insurance_network_code: Optional[str] = None
    emergency_hotline: Optional[str] = None
    operating_hours: Optional[str] = None
    clinical_review_policy: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    admin: Optional[AdminSummary] = None
    stats: Optional[OrgStats] = None

    class Config:
        from_attributes = True


class OrganizationCreateRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    code: str = Field(..., min_length=2, max_length=50)
    description: Optional[str] = None
    address: Optional[str] = None
    contact_email: Optional[EmailStr] = None
    contact_phone: Optional[str] = None
    facility_type: Optional[str] = "Multi-Specialty Hospital"
    departments: Optional[list[str]] = Field(default_factory=list)
    total_beds: Optional[int] = 0
    icu_beds: Optional[int] = 0
    has_emergency: Optional[bool] = True
    has_ambulance: Optional[bool] = True
    license_number: Optional[str] = None
    abdm_facility_id: Optional[str] = None
    insurance_network_code: Optional[str] = None
    emergency_hotline: Optional[str] = None
    operating_hours: Optional[str] = "24/7 Emergency & Inpatient"
    clinical_review_policy: Optional[str] = "Strict Doctor Sign-Off Required"
    # Admin provision details
    admin_name: str = Field(..., min_length=2)
    admin_email: EmailStr
    admin_password: str = Field(..., min_length=8)
    admin_phone: Optional[str] = None


class OrganizationUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=255)
    code: Optional[str] = Field(None, min_length=2, max_length=50)
    description: Optional[str] = None
    address: Optional[str] = None
    contact_email: Optional[EmailStr] = None
    contact_phone: Optional[str] = None
    is_active: Optional[bool] = None


# =============================================================================
# Endpoints
# =============================================================================

@router.get("/", response_model=list[OrganizationResponse])
async def list_organizations(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """List organizations. Super Admin sees all; Org Admin sees only their assigned organization."""
    if current_user.role == UserRole.SUPER_ADMIN:
        result = await db.execute(select(Organization).order_by(Organization.created_at.desc()))
        orgs = result.scalars().all()
    else:
        if not current_user.organization_id:
            return []
        result = await db.execute(
            select(Organization).where(Organization.organization_id == current_user.organization_id)
        )
        orgs = result.scalars().all()

    response = []
    for org in orgs:
        # Find admin for this organization
        admin_res = await db.execute(
            select(User).where(
                User.organization_id == org.organization_id,
                User.role == UserRole.ADMIN,
            )
        )
        admin_user = admin_res.scalar_one_or_none()
        admin_summary = None
        if admin_user:
            admin_summary = AdminSummary(
                user_id=admin_user.user_id,
                full_name=admin_user.full_name,
                email=admin_user.email,
                phone=admin_user.phone,
            )

        # Count users in this org
        stats_query = select(
            func.count(User.user_id).label("total"),
            func.count(User.user_id).filter(User.role == UserRole.DOCTOR).label("doctors"),
            func.count(User.user_id).filter(User.role == UserRole.PATIENT).label("patients"),
        ).where(User.organization_id == org.organization_id)
        stats_res = await db.execute(stats_query)
        stats_row = stats_res.fetchone()

        stats = OrgStats(
            total_users=stats_row[0] if stats_row else 0,
            total_doctors=stats_row[1] if stats_row else 0,
            total_patients=stats_row[2] if stats_row else 0,
        )

        response.append(
            OrganizationResponse(
                organization_id=org.organization_id,
                name=org.name,
                code=org.code,
                description=org.description,
                address=org.address,
                contact_email=org.contact_email,
                contact_phone=org.contact_phone,
                is_active=org.is_active,
                facility_type=org.facility_type,
                departments=org.departments or [],
                total_beds=org.total_beds,
                icu_beds=org.icu_beds,
                has_emergency=org.has_emergency,
                has_ambulance=org.has_ambulance,
                license_number=org.license_number,
                abdm_facility_id=org.abdm_facility_id,
                insurance_network_code=org.insurance_network_code,
                emergency_hotline=org.emergency_hotline,
                operating_hours=org.operating_hours,
                clinical_review_policy=org.clinical_review_policy,
                created_at=org.created_at,
                updated_at=org.updated_at,
                admin=admin_summary,
                stats=stats,
            )
        )
    return response


@router.get("/my-org", response_model=OrganizationResponse)
async def get_my_organization(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get the organization assigned to the current active user."""
    if not current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Current user is not associated with an organization.",
        )

    result = await db.execute(
        select(Organization).where(Organization.organization_id == current_user.organization_id)
    )
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found.",
        )

    # Fetch admin
    admin_res = await db.execute(
        select(User).where(
            User.organization_id == org.organization_id,
            User.role == UserRole.ADMIN,
        )
    )
    admin_user = admin_res.scalar_one_or_none()
    admin_summary = None
    if admin_user:
        admin_summary = AdminSummary(
            user_id=admin_user.user_id,
            full_name=admin_user.full_name,
            email=admin_user.email,
            phone=admin_user.phone,
        )

    return OrganizationResponse(
        organization_id=org.organization_id,
        name=org.name,
        code=org.code,
        description=org.description,
        address=org.address,
        contact_email=org.contact_email,
        contact_phone=org.contact_phone,
        is_active=org.is_active,
        facility_type=org.facility_type,
        departments=org.departments or [],
        total_beds=org.total_beds,
        icu_beds=org.icu_beds,
        has_emergency=org.has_emergency,
        has_ambulance=org.has_ambulance,
        license_number=org.license_number,
        abdm_facility_id=org.abdm_facility_id,
        insurance_network_code=org.insurance_network_code,
        emergency_hotline=org.emergency_hotline,
        operating_hours=org.operating_hours,
        clinical_review_policy=org.clinical_review_policy,
        created_at=org.created_at,
        updated_at=org.updated_at,
        admin=admin_summary,
    )


@router.post("/", response_model=OrganizationResponse, status_code=status.HTTP_201_CREATED)
async def create_organization(
    data: OrganizationCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_super_admin),
):
    """Super Admin creates an organization and provisions its initial Administrator."""
    # Check if org name or code exists
    existing_org = await db.execute(
        select(Organization).where(
            (Organization.name == data.name) | (Organization.code == data.code)
        )
    )
    if existing_org.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An organization with this name or code already exists.",
        )

    # Check if admin email or mobile phone is already linked to ANY account
    clean_admin_phone = normalize_phone(data.admin_phone) if data.admin_phone else None
    await check_credentials_available(db, email=data.admin_email, phone=clean_admin_phone)

    # Create Organization
    new_org = Organization(
        name=data.name,
        code=data.code.upper(),
        description=data.description,
        address=data.address,
        contact_email=data.contact_email,
        contact_phone=data.contact_phone,
        is_active=True,
    )
    db.add(new_org)
    await db.flush()  # populate new_org.organization_id

    # Create Org Admin User
    admin_user = await create_user(
        db,
        UserCreate(
            email=data.admin_email,
            password=data.admin_password,
            full_name=data.admin_name,
            role=UserRole.ADMIN.value,
            phone=data.admin_phone,
            organization_id=new_org.organization_id,
        ),
        role=UserRole.ADMIN.value,
    )

    # Audit log
    audit = AuditLog(
        user_id=current_user.user_id,
        action="CREATE_ORGANIZATION",
        resource_type="organizations",
        resource_id=new_org.organization_id,
        outcome=AuditOutcome.SUCCESS,
        details={
            "organization_name": new_org.name,
            "organization_code": new_org.code,
            "admin_email": admin_user.email,
        },
    )
    db.add(audit)
    await db.commit()
    await db.refresh(new_org)

    admin_summary = AdminSummary(
        user_id=admin_user.user_id,
        full_name=admin_user.full_name,
        email=admin_user.email,
        phone=admin_user.phone,
    )

    return OrganizationResponse(
        organization_id=new_org.organization_id,
        name=new_org.name,
        code=new_org.code,
        description=new_org.description,
        address=new_org.address,
        contact_email=new_org.contact_email,
        contact_phone=new_org.contact_phone,
        is_active=new_org.is_active,
        created_at=new_org.created_at,
        updated_at=new_org.updated_at,
        admin=admin_summary,
        stats=OrgStats(total_users=1),
    )


@router.get("/{org_id}", response_model=OrganizationResponse)
async def get_organization(
    org_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Get details of an organization. Restricted to Super Admin or that Org's Admin."""
    if current_user.role != UserRole.SUPER_ADMIN and current_user.organization_id != org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to view this organization.",
        )

    result = await db.execute(
        select(Organization).where(Organization.organization_id == org_id)
    )
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found.",
        )

    # Fetch admin
    admin_res = await db.execute(
        select(User).where(
            User.organization_id == org.organization_id,
            User.role == UserRole.ADMIN,
        )
    )
    admin_user = admin_res.scalar_one_or_none()
    admin_summary = None
    if admin_user:
        admin_summary = AdminSummary(
            user_id=admin_user.user_id,
            full_name=admin_user.full_name,
            email=admin_user.email,
            phone=admin_user.phone,
        )

    return OrganizationResponse(
        organization_id=org.organization_id,
        name=org.name,
        code=org.code,
        description=org.description,
        address=org.address,
        contact_email=org.contact_email,
        contact_phone=org.contact_phone,
        is_active=org.is_active,
        created_at=org.created_at,
        updated_at=org.updated_at,
        admin=admin_summary,
    )


@router.put("/{org_id}", response_model=OrganizationResponse)
async def update_organization(
    org_id: uuid.UUID,
    data: OrganizationUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Update organization details. Restricted to Super Admin or that Org's Admin."""
    if current_user.role != UserRole.SUPER_ADMIN and current_user.organization_id != org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to modify this organization.",
        )

    result = await db.execute(
        select(Organization).where(Organization.organization_id == org_id)
    )
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found.",
        )

    if data.name is not None:
        org.name = data.name
    if data.code is not None:
        org.code = data.code.upper()
    if data.description is not None:
        org.description = data.description
    if data.address is not None:
        org.address = data.address
    if data.contact_email is not None:
        org.contact_email = data.contact_email
    if data.contact_phone is not None:
        org.contact_phone = data.contact_phone
    if data.is_active is not None and current_user.role == UserRole.SUPER_ADMIN:
        org.is_active = data.is_active

    await db.commit()
    await db.refresh(org)

    return OrganizationResponse(
        organization_id=org.organization_id,
        name=org.name,
        code=org.code,
        description=org.description,
        address=org.address,
        contact_email=org.contact_email,
        contact_phone=org.contact_phone,
        is_active=org.is_active,
        created_at=org.created_at,
        updated_at=org.updated_at,
    )


@router.delete("/{org_id}", status_code=status.HTTP_200_OK)
async def delete_organization(
    org_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_super_admin),
):
    """Super Admin deletes an organization and all its associated users (including its Admin)."""
    result = await db.execute(
        select(Organization).where(Organization.organization_id == org_id)
    )
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found.",
        )

    org_name = org.name
    org_code = org.code

    # Fetch users to log
    users_res = await db.execute(
        select(User).where(User.organization_id == org_id)
    )
    associated_users = users_res.scalars().all()
    user_emails = [u.email for u in associated_users]

    # Delete users explicitly to ensure any cascading dependencies are cleaned up
    for u in associated_users:
        await db.delete(u)

    # Delete organization
    await db.delete(org)

    # Audit log
    audit = AuditLog(
        user_id=current_user.user_id,
        action="DELETE_ORGANIZATION",
        resource_type="organizations",
        resource_id=org_id,
        outcome=AuditOutcome.SUCCESS,
        details={
            "organization_name": org_name,
            "organization_code": org_code,
            "deleted_users_count": len(user_emails),
            "deleted_user_emails": user_emails,
        },
    )
    db.add(audit)
    await db.commit()

    return {
        "message": f"Organization '{org_name}' ({org_code}) and its {len(user_emails)} associated user(s) were successfully deleted.",
        "organization_id": str(org_id),
    }
