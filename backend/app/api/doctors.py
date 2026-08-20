"""Doctors API routes."""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Doctor, User, UserRole
from app.services.auth.rbac import require_admin, require_doctor
from app.services.auth.service import get_current_active_user
from app.api.schemas.doctor import (
    DoctorCreate,
    DoctorUpdate,
    DoctorResponse,
    DoctorListResponse,
)

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


@router.get("/", response_model=DoctorListResponse)
async def list_doctors(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Page size"),
    specialty: Optional[str] = Query(None, description="Filter by specialty"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """List doctors with pagination and optional specialty filter. Admin and doctors can list."""
    if current_user.role not in (UserRole.ADMIN, UserRole.DOCTOR):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to list doctors",
        )

    # Build query
    query = select(Doctor)
    count_query = select(func.count(Doctor.doctor_id))

    if specialty:
        query = query.where(Doctor.specialty.ilike(f"%{specialty}%"))
        count_query = count_query.where(Doctor.specialty.ilike(f"%{specialty}%"))

    # Get total count
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Apply pagination
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    doctors = result.scalars().all()

    total_pages = (total + page_size - 1) // page_size

    return DoctorListResponse(
        doctors=doctors,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )