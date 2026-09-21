"""Nursing department and staff management API routes."""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import AuditLog, AuditOutcome, User, UserRole
from app.services.auth.rbac import require_head_nurse, require_medical_staff
from app.services.auth.service import (
    check_credentials_available,
    get_password_hash,
    normalize_phone,
)

router = APIRouter(prefix="/nurses", tags=["nurses"])


class JuniorNurseProvisionRequest(BaseModel):
    """Schema for Head Nurse to provision junior nursing staff within their department."""
    email: EmailStr
    password: str = Field(min_length=8)
    full_name: str
    license_number: str = Field(..., description="Nursing Council Registration Number")
    qualifications: str = Field(..., description="E.g. B.Sc Nursing, GNM, Critical Care Diploma")
    designation: str = Field(default="Staff Nurse", description="E.g. Staff Nurse, ICU Nurse, Ward Incharge")
    experience_years: int = 1
    room_number: Optional[str] = Field(default=None, description="Assigned Ward or Nursing Station")
    shift: str = Field(default="Morning (07:00 - 15:00)")
    phone: Optional[str] = None


class NurseResponse(BaseModel):
    user_id: uuid.UUID
    email: str
    full_name: str
    role: str
    phone: Optional[str] = None
    department: Optional[str] = None
    designation: Optional[str] = None
    qualifications: Optional[str] = None
    experience_years: Optional[int] = None
    room_number: Optional[str] = None
    shift: Optional[str] = None
    is_active: bool

    class Config:
        from_attributes = True


@router.get("/department-team")
async def get_department_team(
    db: AsyncSession = Depends(get_db),
    current_head: User = Depends(require_head_nurse),
):
    """Fetch nursing team members belonging strictly to the Head Nurse's department/ward."""
    dept = current_head.department or "General Ward"
    query = select(User).where(
        User.role.in_([UserRole.NURSE, UserRole.HEAD_NURSE]),
        (User.department == dept) | (User.supervisor_id == current_head.user_id),
    )
    if current_head.organization_id:
        query = query.where(User.organization_id == current_head.organization_id)

    result = await db.execute(query.order_by(User.role.desc(), User.full_name.asc()))
    nurses = result.scalars().all()

    return {
        "department": dept,
        "head_nurse": {
            "name": current_head.full_name,
            "email": current_head.email,
            "designation": current_head.designation,
        },
        "total_members": len(nurses),
        "team": [NurseResponse.model_validate(n) for n in nurses],
    }


@router.post("/junior-staff", status_code=status.HTTP_201_CREATED)
async def provision_junior_staff(
    req: JuniorNurseProvisionRequest,
    db: AsyncSession = Depends(get_db),
    current_head: User = Depends(require_head_nurse),
):
    """Head Nurse provisions a junior staff nurse strictly scoped to their department."""
    dept = current_head.department or "General Ward"
    clean_phone = normalize_phone(req.phone) if req.phone else None

    # 1. Universal credential uniqueness check across all account types
    await check_credentials_available(db, email=req.email, phone=clean_phone)

    # 2. Create User account locked to Head Nurse's department and supervisor
    hashed_pwd = get_password_hash(req.password)
    new_user = User(
        email=req.email,
        phone=clean_phone,
        hashed_password=hashed_pwd,
        full_name=req.full_name,
        role=UserRole.NURSE,
        organization_id=current_head.organization_id,
        department=dept,
        designation=req.designation,
        qualifications=req.qualifications,
        experience_years=req.experience_years,
        room_number=req.room_number,
        shift=req.shift,
        supervisor_id=current_head.user_id,
        is_active=True,
    )
    db.add(new_user)
    await db.flush()

    # 3. Audit Logging
    audit_entry = AuditLog(
        user_id=current_head.user_id,
        action="HEAD_NURSE_PROVISION_JUNIOR",
        resource_type="users",
        resource_id=new_user.user_id,
        outcome=AuditOutcome.SUCCESS,
        details={
            "provisioned_email": new_user.email,
            "department": dept,
            "designation": req.designation,
            "license_number": req.license_number,
            "supervisor_id": str(current_head.user_id),
        },
    )
    db.add(audit_entry)
    await db.commit()
    await db.refresh(new_user)

    return {
        "message": f"Successfully onboarded {req.full_name} ({req.designation}) into Department of {dept}.",
        "nurse": NurseResponse.model_validate(new_user),
    }


@router.get("/", response_model=list[NurseResponse])
async def list_nurses(
    department: Optional[str] = Query(None, description="Filter by department"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_medical_staff),
):
    """List nurses available within the organization."""
    query = select(User).where(User.role.in_([UserRole.NURSE, UserRole.HEAD_NURSE]))
    if current_user.role != UserRole.SUPER_ADMIN and current_user.organization_id:
        query = query.where(User.organization_id == current_user.organization_id)
    if department:
        query = query.where(User.department.ilike(f"%{department.strip()}%"))

    result = await db.execute(query.order_by(User.full_name.asc()))
    return [NurseResponse.model_validate(n) for n in result.scalars().all()]
