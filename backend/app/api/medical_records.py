"""Medical Records API routes."""

from typing import Optional, List
from uuid import UUID
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import MedicalRecord, Patient, Doctor, User, UserRole, MedicalRecordStatus
from app.services.auth.service import get_current_active_user
from app.api.schemas.medical_record import (
    MedicalRecordCreate,
    MedicalRecordUpdate,
    MedicalRecordResponse,
    MedicalRecordListResponse,
)

router = APIRouter(prefix="/medical-records", tags=["medical-records"])


@router.post("/", response_model=MedicalRecordResponse, status_code=status.HTTP_201_CREATED)
async def create_medical_record(
    record_data: MedicalRecordCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Create a new medical record. Only doctors can create medical records."""
    if current_user.role != UserRole.DOCTOR and current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only doctors can create medical records",
        )
    
    # Verify patient exists
    patient = await db.get(Patient, record_data.patient_id)
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found",
        )
    
    # Verify doctor exists
    doctor = await db.get(Doctor, record_data.doctor_id)
    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Doctor not found",
        )
    
    # If doctor is creating, verify they are the doctor
    if current_user.role == UserRole.DOCTOR:
        doctor_result = await db.execute(
            select(Doctor).where(Doctor.user_id == current_user.user_id)
        )
        current_doctor = doctor_result.scalar_one_or_none()
        if not current_doctor or current_doctor.doctor_id != record_data.doctor_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Doctors can only create records for themselves",
            )
    
    # Verify appointment exists if provided
    if record_data.appointment_id:
        from app.models import Appointment
        appointment = await db.get(Appointment, record_data.appointment_id)
        if not appointment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Appointment not found",
            )
        if appointment.patient_id != record_data.patient_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Appointment does not belong to this patient",
            )
        if appointment.doctor_id != record_data.doctor_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Appointment does not belong to this doctor",
            )
    
    # Force status to draft on creation
    record = MedicalRecord(
        patient_id=record_data.patient_id,
        doctor_id=record_data.doctor_id,
        appointment_id=record_data.appointment_id,
        content=record_data.content.model_dump(),
        status=MedicalRecordStatus.DRAFT,
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return record


@router.get("/{record_id}/", response_model=MedicalRecordResponse)
async def get_medical_record(
    record_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get a medical record by ID. Patients can read their own; doctors can read their patients'."""
    record = await db.get(MedicalRecord, record_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Medical record not found",
        )
    
    # RBAC check
    if current_user.role == UserRole.PATIENT:
        patient_result = await db.execute(
            select(Patient).where(Patient.user_id == current_user.user_id)
        )
        patient = patient_result.scalar_one_or_none()
        if not patient or record.patient_id != patient.patient_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Patients can only read their own medical records",
            )
    elif current_user.role == UserRole.DOCTOR:
        doctor_result = await db.execute(
            select(Doctor).where(Doctor.user_id == current_user.user_id)
        )
        doctor = doctor_result.scalar_one_or_none()
        if not doctor or record.doctor_id != doctor.doctor_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Doctors can only read their own medical records",
            )
    elif current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to read medical record",
        )
    
    return record


@router.put("/{record_id}/", response_model=MedicalRecordResponse)
async def update_medical_record(
    record_id: UUID,
    record_data: MedicalRecordUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Update a medical record. Doctors can update their own records; admins can update any."""
    record = await db.get(MedicalRecord, record_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Medical record not found",
        )
    
    # RBAC check
    if current_user.role == UserRole.DOCTOR:
        doctor_result = await db.execute(
            select(Doctor).where(Doctor.user_id == current_user.user_id)
        )
        doctor = doctor_result.scalar_one_or_none()
        if not doctor or record.doctor_id != doctor.doctor_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Doctors can only update their own medical records",
            )
        # Doctors cannot finalize records (that's M23)
        if record_data.status and record_data.status.upper() == "FINALIZED":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Doctors cannot finalize records directly (requires review flow)",
            )
    elif current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to update medical record",
        )
    
    # Update fields
    update_data = record_data.model_dump(exclude_unset=True)
    
    # Handle content update specially - merge with existing content
    if "content" in update_data and update_data["content"] is not None:
        existing_content = record.content or {}
        new_content = update_data["content"]
        # Merge: keep existing values for fields not provided in update
        merged_content = {**existing_content, **new_content}
        record.content = merged_content
        del update_data["content"]
    
    for field, value in update_data.items():
        setattr(record, field, value)
    
    await db.commit()
    await db.refresh(record)
    return record


@router.get("/patient/{patient_id}/", response_model=MedicalRecordListResponse)
async def list_patient_medical_records(
    patient_id: UUID,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Page size"),
    status_filter: Optional[str] = Query(None, description="Filter by status (draft/finalized/amended)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """List medical records for a patient with pagination and filters."""
    # Verify patient exists
    patient = await db.get(Patient, patient_id)
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found",
        )
    
    # RBAC check
    if current_user.role == UserRole.PATIENT:
        patient_result = await db.execute(
            select(Patient).where(Patient.user_id == current_user.user_id)
        )
        current_patient = patient_result.scalar_one_or_none()
        if not current_patient or current_patient.patient_id != patient_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Patients can only list their own medical records",
            )
    elif current_user.role == UserRole.DOCTOR:
        # Doctors can list records for their patients
        # Check if this doctor has any appointments with this patient
        from app.models import Appointment
        # Get the doctor profile for the current user
        doctor_result = await db.execute(
            select(Doctor).where(Doctor.user_id == current_user.user_id)
        )
        current_doctor = doctor_result.scalar_one_or_none()
        if not current_doctor:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Doctor profile not found",
            )
        
        # Check if this doctor has appointments with this patient
        appt_result = await db.execute(
            select(Appointment).where(
                and_(
                    Appointment.patient_id == patient_id,
                    Appointment.doctor_id == current_doctor.doctor_id
                )
            ).limit(1)
        )
        if not appt_result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Doctors can only list records for their own patients",
            )
    elif current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to list medical records",
        )
    
    # Build query
    query = select(MedicalRecord).where(MedicalRecord.patient_id == patient_id)
    count_query = select(func.count(MedicalRecord.record_id)).where(MedicalRecord.patient_id == patient_id)
    
    if status_filter:
        try:
            # Convert to uppercase to match enum values
            status_enum = MedicalRecordStatus(status_filter.upper())
            query = query.where(MedicalRecord.status == status_enum)
            count_query = count_query.where(MedicalRecord.status == status_enum)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status: {status_filter}",
            )
    
    # Get total count
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # Apply pagination
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    records = result.scalars().all()
    
    total_pages = (total + page_size - 1) // page_size
    
    return MedicalRecordListResponse(
        records=records,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/", response_model=MedicalRecordListResponse)
async def list_medical_records(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Page size"),
    patient_id: Optional[UUID] = Query(None, description="Filter by patient ID"),
    doctor_id: Optional[UUID] = Query(None, description="Filter by doctor ID"),
    status_filter: Optional[str] = Query(None, description="Filter by status"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """List all medical records with pagination and filters (admin only)."""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can list all medical records",
        )
    
    # Build query
    query = select(MedicalRecord)
    count_query = select(func.count(MedicalRecord.record_id))
    
    if patient_id:
        query = query.where(MedicalRecord.patient_id == patient_id)
        count_query = count_query.where(MedicalRecord.patient_id == patient_id)
    
    if doctor_id:
        query = query.where(MedicalRecord.doctor_id == doctor_id)
        count_query = count_query.where(MedicalRecord.doctor_id == doctor_id)
    
    if status_filter:
        try:
            # Convert to uppercase to match enum values
            status_enum = MedicalRecordStatus(status_filter.upper())
            query = query.where(MedicalRecord.status == status_enum)
            count_query = count_query.where(MedicalRecord.status == status_enum)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status: {status_filter}",
            )
    
    # Get total count
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # Apply pagination
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    records = result.scalars().all()
    
    total_pages = (total + page_size - 1) // page_size
    
    return MedicalRecordListResponse(
        records=records,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )