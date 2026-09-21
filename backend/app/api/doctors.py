"""Doctors API routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.doctor import (
    DoctorCreate,
    DoctorListResponse,
    DoctorResponse,
    DoctorUpdate,
)
from app.database import get_db
from app.models import Doctor, User, UserRole
from app.services.auth.service import get_current_active_user

router = APIRouter(prefix="/doctors", tags=["doctors"])


@router.post("/", response_model=DoctorResponse, status_code=status.HTTP_201_CREATED)
async def create_doctor(
    doctor_data: DoctorCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Create a new doctor. Only admins can create doctors."""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can create doctors",
        )

    # Check if license number already exists
    existing = await db.execute(
        select(Doctor).where(Doctor.license_number == doctor_data.license_number)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="License number already registered",
        )

    # Check if email already exists
    existing = await db.execute(
        select(Doctor).where(Doctor.email == doctor_data.email)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    doctor = Doctor(**doctor_data.model_dump())
    db.add(doctor)
    await db.commit()
    await db.refresh(doctor)
    return doctor


@router.get("/{doctor_id}/", response_model=DoctorResponse)
async def get_doctor(
    doctor_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get a doctor by ID. Doctors can read their own profile; admins can read any."""
    doctor = await db.get(Doctor, doctor_id)
    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Doctor not found",
        )

    # RBAC check
    if current_user.role == UserRole.DOCTOR:
        if doctor.user_id != current_user.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Doctors can only read their own profile",
            )
    elif current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to read doctor profile",
        )

    return doctor


@router.put("/{doctor_id}/", response_model=DoctorResponse)
async def update_doctor(
    doctor_id: UUID,
    doctor_data: DoctorUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Update a doctor. Doctors can update their own profile; admins can update any."""
    doctor = await db.get(Doctor, doctor_id)
    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Doctor not found",
        )

    # RBAC check
    if current_user.role == UserRole.DOCTOR:
        if doctor.user_id != current_user.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Doctors can only update their own profile",
            )
    elif current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to update doctor profile",
        )

    # Check for duplicate license number if being updated
    if doctor_data.license_number and doctor_data.license_number != doctor.license_number:
        existing = await db.execute(
            select(Doctor).where(Doctor.license_number == doctor_data.license_number)
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="License number already registered",
            )

    # Check for duplicate email if being updated
    if doctor_data.email and doctor_data.email != doctor.email:
        existing = await db.execute(
            select(Doctor).where(Doctor.email == doctor_data.email)
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered",
            )

    # Update fields
    update_data = doctor_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(doctor, field, value)

    await db.commit()
    await db.refresh(doctor)
    return doctor


@router.get("/specialties", response_model=list[str])
async def get_specialties(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Retrieve distinct specialties available across all registered doctors."""
    stmt = select(Doctor.specialty).distinct().order_by(Doctor.specialty)
    res = await db.execute(stmt)
    specialties = [s for s in res.scalars().all() if s]
    return specialties


@router.get("/", response_model=DoctorListResponse)
async def list_doctors(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Page size"),
    specialty: str | None = Query(None, description="Filter by specialty"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """List doctors with pagination and optional specialty filter. Accessible to patients, doctors, and admins."""
    if current_user.role not in (
        UserRole.ADMIN,
        UserRole.SUPER_ADMIN,
        UserRole.DOCTOR,
        UserRole.HEAD_PHYSICIAN,
        UserRole.NURSE,
        UserRole.HEAD_NURSE,
        UserRole.PATIENT,
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to list doctors",
        )

    # Build query
    query = select(Doctor)
    count_query = select(func.count(Doctor.doctor_id))

    if specialty and specialty.strip() and specialty.lower() != "all":
        query = query.where(Doctor.specialty.ilike(f"%{specialty.strip()}%"))
        count_query = count_query.where(Doctor.specialty.ilike(f"%{specialty.strip()}%"))

    # Get total count
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Apply pagination
    query = query.order_by(Doctor.full_name).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    doctors = result.scalars().all()

    total_pages = (total + page_size - 1) // page_size if total else 0

    return DoctorListResponse(
        doctors=doctors,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


from pydantic import BaseModel, EmailStr, Field
from app.services.auth.rbac import require_head_physician
from app.services.auth.service import check_credentials_available, get_password_hash, normalize_phone
from app.models import AuditLog, AuditOutcome


class JuniorPhysicianProvisionRequest(BaseModel):
    """Schema for Head Physician to provision junior clinical staff within their department."""
    email: EmailStr
    password: str = Field(min_length=8)
    full_name: str
    license_number: str
    qualifications: str
    designation: str = "Junior Resident"
    specialty: str | None = None
    experience_years: int = 1
    room_number: str | None = None
    shift: str = "Morning (08:00 - 16:00)"
    phone: str | None = None


@router.get("/department-team")
async def get_department_team(
    db: AsyncSession = Depends(get_db),
    current_head: User = Depends(require_head_physician),
):
    """Fetch clinical team members belonging strictly to the Head Physician's department."""
    dept = current_head.department or "General Medicine"
    query = select(Doctor).join(User, Doctor.user_id == User.user_id).where(
        (Doctor.department == dept) | (Doctor.supervisor_id == current_head.user_id)
    )
    if current_head.organization_id:
        query = query.where(User.organization_id == current_head.organization_id)

    result = await db.execute(query.order_by(Doctor.is_head_physician.desc(), Doctor.full_name.asc()))
    doctors = result.scalars().all()

    return {
        "department": dept,
        "head_physician": {
            "name": current_head.full_name,
            "email": current_head.email,
            "designation": current_head.designation,
        },
        "total_members": len(doctors),
        "team": doctors,
    }


@router.post("/junior-staff", status_code=status.HTTP_201_CREATED)
async def provision_junior_staff(
    req: JuniorPhysicianProvisionRequest,
    db: AsyncSession = Depends(get_db),
    current_head: User = Depends(require_head_physician),
):
    """Head Physician provisions a junior physician or resident strictly scoped to their department."""
    dept = current_head.department or "General Medicine"
    clean_phone = normalize_phone(req.phone) if req.phone else None

    # 1. Universal uniqueness validation across all account types
    await check_credentials_available(db, email=req.email, phone=clean_phone)

    # 2. Validate medical license uniqueness
    existing_license = await db.execute(
        select(Doctor).where(Doctor.license_number == req.license_number)
    )
    if existing_license.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Medical license {req.license_number} is already registered to another doctor.",
        )

    # 3. Create User account locked to Head Physician's department and supervisor
    hashed_pwd = get_password_hash(req.password)
    new_user = User(
        email=req.email,
        phone=clean_phone,
        hashed_password=hashed_pwd,
        full_name=req.full_name,
        role=UserRole.DOCTOR,
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

    # 4. Create Doctor clinical profile
    new_doctor = Doctor(
        user_id=new_user.user_id,
        email=new_user.email,
        full_name=new_user.full_name,
        specialty=req.specialty or dept,
        license_number=req.license_number,
        hospital_affiliation=current_head.doctor_profile.hospital_affiliation if current_head.doctor_profile else "AI-HOS Medical Center",
        phone=clean_phone,
        department=dept,
        designation=req.designation,
        qualifications=req.qualifications,
        experience_years=req.experience_years,
        room_number=req.room_number,
        shift=req.shift,
        is_head_physician=False,
        supervisor_id=current_head.user_id,
    )
    db.add(new_doctor)
    await db.flush()

    # 5. Audit Logging
    audit_entry = AuditLog(
        user_id=current_head.user_id,
        action="HEAD_PHYSICIAN_PROVISION_JUNIOR",
        resource_type="doctors",
        resource_id=new_doctor.doctor_id,
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
    await db.refresh(new_doctor)

    return {
        "message": f"Successfully onboarded {req.full_name} ({req.designation}) into Department of {dept}.",
        "doctor": new_doctor,
    }