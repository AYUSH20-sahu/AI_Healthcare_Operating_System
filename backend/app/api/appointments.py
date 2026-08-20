"""Appointments API routes."""

from typing import Optional
from uuid import UUID
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Appointment, Patient, Doctor, User, UserRole, AppointmentStatus
from app.services.auth.service import get_current_active_user
from app.api.schemas.appointment import (
    AppointmentCreate,
    AppointmentUpdate,
    AppointmentResponse,
    AppointmentListResponse,
)

router = APIRouter(prefix="/appointments", tags=["appointments"])


async def check_slot_conflict(
    db: AsyncSession,
    doctor_id: UUID,
    scheduled_at: datetime,
    duration_minutes: int,
    exclude_appointment_id: Optional[UUID] = None
) -> Optional[Appointment]:
    """
    Check if a doctor has a conflicting appointment at the given time.
    Returns the conflicting appointment if there's a conflict, None otherwise.
    """
    new_end = scheduled_at + timedelta(minutes=duration_minutes)
    
    # Get all non-cancelled appointments for this doctor
    query = select(Appointment).where(
        and_(
            Appointment.doctor_id == doctor_id,
            Appointment.status != AppointmentStatus.CANCELLED
        )
    )
    
    if exclude_appointment_id:
        query = query.where(Appointment.appointment_id != exclude_appointment_id)
    
    result = await db.execute(query)
    appointments = result.scalars().all()
    
    # Check for overlap in Python (more reliable across databases)
    for appt in appointments:
        existing_end = appt.scheduled_at + timedelta(minutes=appt.duration_minutes)
        # Overlap if: new_start < existing_end AND new_end > existing_start
        if scheduled_at < existing_end and new_end > appt.scheduled_at:
            return appt
    
    return None


@router.post("/", response_model=AppointmentResponse, status_code=status.HTTP_201_CREATED)
async def create_appointment(
    appointment_data: AppointmentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Create a new appointment. Validates no double-booking for the doctor."""
    # Verify patient exists
    patient = await db.get(Patient, appointment_data.patient_id)
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found",
        )
    
    # Verify doctor exists
    doctor = await db.get(Doctor, appointment_data.doctor_id)
    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Doctor not found",
        )
    
    # Check for slot conflict
    conflicting = await check_slot_conflict(
        db,
        appointment_data.doctor_id,
        appointment_data.scheduled_at,
        appointment_data.duration_minutes
    )
    
    if conflicting:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Doctor has a conflicting appointment at this time (appointment {conflicting.appointment_id})",
        )
    
    appointment = Appointment(**appointment_data.model_dump())
    db.add(appointment)
    await db.commit()
    await db.refresh(appointment)
    return appointment


@router.get("/{appointment_id}/", response_model=AppointmentResponse)
async def get_appointment(
    appointment_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get an appointment by ID."""
    appointment = await db.get(Appointment, appointment_id)
    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found",
        )
    
    # RBAC check
    if current_user.role == UserRole.PATIENT:
        if appointment.patient_id != current_user.user_id:
            # Need to check if patient owns this appointment via patient profile
            patient_result = await db.execute(
                select(Patient).where(Patient.user_id == current_user.user_id)
            )
            patient = patient_result.scalar_one_or_none()
            if not patient or appointment.patient_id != patient.patient_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Patients can only read their own appointments",
                )
    elif current_user.role == UserRole.DOCTOR:
        if appointment.doctor_id != current_user.user_id:
            # Need to check if doctor owns this appointment via doctor profile
            doctor_result = await db.execute(
                select(Doctor).where(Doctor.user_id == current_user.user_id)
            )
            doctor = doctor_result.scalar_one_or_none()
            if not doctor or appointment.doctor_id != doctor.doctor_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Doctors can only read their own appointments",
                )
    elif current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to read appointment",
        )
    
    return appointment


@router.put("/{appointment_id}/", response_model=AppointmentResponse)
async def update_appointment(
    appointment_id: UUID,
    appointment_data: AppointmentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Update an appointment. Validates no double-booking for the doctor."""
    appointment = await db.get(Appointment, appointment_id)
    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found",
        )
    
    # RBAC check
    if current_user.role == UserRole.PATIENT:
        patient_result = await db.execute(
            select(Patient).where(Patient.user_id == current_user.user_id)
        )
        patient = patient_result.scalar_one_or_none()
        if not patient or appointment.patient_id != patient.patient_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Patients can only update their own appointments",
            )
    elif current_user.role == UserRole.DOCTOR:
        doctor_result = await db.execute(
            select(Doctor).where(Doctor.user_id == current_user.user_id)
        )
        doctor = doctor_result.scalar_one_or_none()
        if not doctor or appointment.doctor_id != doctor.doctor_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Doctors can only update their own appointments",
            )
    elif current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to update appointment",
        )
    
    # Check for slot conflict if time is being changed
    if appointment_data.scheduled_at is not None or appointment_data.duration_minutes is not None:
        new_scheduled_at = appointment_data.scheduled_at or appointment.scheduled_at
        new_duration = appointment_data.duration_minutes or appointment.duration_minutes
        
        conflicting = await check_slot_conflict(
            db,
            appointment.doctor_id,
            new_scheduled_at,
            new_duration,
            exclude_appointment_id=appointment_id
        )
        
        if conflicting:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Doctor has a conflicting appointment at this time (appointment {conflicting.appointment_id})",
            )
    
    # Update fields
    update_data = appointment_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(appointment, field, value)
    
    await db.commit()
    await db.refresh(appointment)
    return appointment


@router.delete("/{appointment_id}/", status_code=status.HTTP_204_NO_CONTENT)
async def delete_appointment(
    appointment_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Delete (cancel) an appointment."""
    appointment = await db.get(Appointment, appointment_id)
    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found",
        )
    
    # RBAC check
    if current_user.role == UserRole.PATIENT:
        patient_result = await db.execute(
            select(Patient).where(Patient.user_id == current_user.user_id)
        )
        patient = patient_result.scalar_one_or_none()
        if not patient or appointment.patient_id != patient.patient_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Patients can only cancel their own appointments",
            )
    elif current_user.role == UserRole.DOCTOR:
        doctor_result = await db.execute(
            select(Doctor).where(Doctor.user_id == current_user.user_id)
        )
        doctor = doctor_result.scalar_one_or_none()
        if not doctor or appointment.doctor_id != doctor.doctor_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Doctors can only cancel their own appointments",
            )
    elif current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to cancel appointment",
        )
    
    # Soft delete - mark as cancelled
    appointment.status = AppointmentStatus.CANCELLED
    await db.commit()


@router.get("/", response_model=AppointmentListResponse)
async def list_appointments(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Page size"),
    patient_id: Optional[UUID] = Query(None, description="Filter by patient ID"),
    doctor_id: Optional[UUID] = Query(None, description="Filter by doctor ID"),
    date_from: Optional[datetime] = Query(None, description="Filter by date from"),
    date_to: Optional[datetime] = Query(None, description="Filter by date to"),
    status: Optional[str] = Query(None, description="Filter by status"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """List appointments with pagination and filters."""
    # Build query
    query = select(Appointment)
    count_query = select(func.count(Appointment.appointment_id))
    
    # Apply RBAC filters
    if current_user.role == UserRole.PATIENT:
        patient_result = await db.execute(
            select(Patient).where(Patient.user_id == current_user.user_id)
        )
        patient = patient_result.scalar_one_or_none()
        if patient:
            query = query.where(Appointment.patient_id == patient.patient_id)
            count_query = count_query.where(Appointment.patient_id == patient.patient_id)
        else:
            # Patient with no profile - return empty
            return AppointmentListResponse(
                appointments=[],
                total=0,
                page=page,
                page_size=page_size,
                total_pages=0,
            )
    elif current_user.role == UserRole.DOCTOR:
        doctor_result = await db.execute(
            select(Doctor).where(Doctor.user_id == current_user.user_id)
        )
        doctor = doctor_result.scalar_one_or_none()
        if doctor:
            query = query.where(Appointment.doctor_id == doctor.doctor_id)
            count_query = count_query.where(Appointment.doctor_id == doctor.doctor_id)
        else:
            # Doctor with no profile - return empty
            return AppointmentListResponse(
                appointments=[],
                total=0,
                page=page,
                page_size=page_size,
                total_pages=0,
            )
    # Admin can see all - no additional filters
    
    # Apply optional filters
    if patient_id:
        query = query.where(Appointment.patient_id == patient_id)
        count_query = count_query.where(Appointment.patient_id == patient_id)
    
    if doctor_id:
        query = query.where(Appointment.doctor_id == doctor_id)
        count_query = count_query.where(Appointment.doctor_id == doctor_id)
    
    if date_from:
        query = query.where(Appointment.scheduled_at >= date_from)
        count_query = count_query.where(Appointment.scheduled_at >= date_from)
    
    if date_to:
        query = query.where(Appointment.scheduled_at <= date_to)
        count_query = count_query.where(Appointment.scheduled_at <= date_to)
    
    if status:
        try:
            status_enum = AppointmentStatus(status)
            query = query.where(Appointment.status == status_enum)
            count_query = count_query.where(Appointment.status == status_enum)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status: {status}",
            )
    
    # Get total count
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # Apply pagination
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    appointments = result.scalars().all()
    
    total_pages = (total + page_size - 1) // page_size
    
    return AppointmentListResponse(
        appointments=appointments,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )