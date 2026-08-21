"""Voice Notes API routes."""

import os
import shutil
from datetime import datetime
from pathlib import Path
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.voice_note import (
    VoiceNoteListResponse,
    VoiceNoteResponse,
    VoiceNoteUpdate,
    VoiceNoteUploadResponse,
)
from app.database import get_db
from app.models import Appointment, Doctor, Patient, User, UserRole, VoiceNote
from app.services.auth.service import get_current_active_user

router = APIRouter(prefix="/voice-notes", tags=["voice-notes"])

# Storage configuration
STORAGE_DIR = Path(os.getenv("VOICE_NOTES_STORAGE", "./storage/voice_notes"))
STORAGE_DIR.mkdir(parents=True, exist_ok=True)

# Allowed audio MIME types
ALLOWED_CONTENT_TYPES = {
    "audio/webm",
    "audio/mp3",
    "audio/wav",
    "audio/ogg",
    "audio/mpeg",
    "audio/x-wav",
}


@router.post("/upload/", response_model=VoiceNoteUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_voice_note(
    appointment_id: UUID = Form(...),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Upload a voice note audio file for an appointment."""
    # Verify user is a doctor or admin
    if current_user.role != UserRole.DOCTOR and current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only doctors can upload voice notes",
        )
    
    # Get doctor profile (for doctors)
    doctor = None
    if current_user.role == UserRole.DOCTOR:
        doctor_result = await db.execute(
            select(Doctor).where(Doctor.user_id == current_user.user_id)
        )
        doctor = doctor_result.scalar_one_or_none()
        if not doctor:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Doctor profile not found",
            )
    
    # Verify appointment exists
    appointment = await db.get(Appointment, appointment_id)
    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found",
        )
    
    # Verify doctor owns this appointment (or is admin)
    if current_user.role == UserRole.DOCTOR and appointment.doctor_id != doctor.doctor_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Doctors can only upload voice notes for their own appointments",
        )
    
    # For admin, use the appointment's doctor_id
    doctor_id = doctor.doctor_id if doctor else appointment.doctor_id
    
    # Validate file type
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type. Allowed types: {', '.join(ALLOWED_CONTENT_TYPES)}",
        )
    
    # Generate unique file path
    file_extension = Path(file.filename).suffix if file.filename else ".webm"
    unique_filename = f"{appointment_id}_{doctor_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}{file_extension}"
    file_path = STORAGE_DIR / unique_filename
    
    # Save file
    try:
        with file_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        file_size = file_path.stat().st_size
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save file: {e!s}",
        )
    
    # Create voice note record
    voice_note = VoiceNote(
        appointment_id=appointment_id,
        doctor_id=doctor_id,
        patient_id=appointment.patient_id,
        file_path=str(file_path),
        file_name=file.filename or unique_filename,
        content_type=file.content_type,
        file_size=file_size,
        duration_seconds=None,  # Could be extracted with ffprobe
        transcription_status="pending",
    )
    db.add(voice_note)
    await db.commit()
    await db.refresh(voice_note)
    
    return VoiceNoteUploadResponse(
        voice_note_id=voice_note.voice_note_id,
        message="Voice note uploaded successfully",
    )


@router.get("/{voice_note_id}/", response_model=VoiceNoteResponse)
async def get_voice_note(
    voice_note_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get a voice note by ID."""
    voice_note = await db.get(VoiceNote, voice_note_id)
    if not voice_note:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Voice note not found",
        )
    
    # RBAC check
    if current_user.role == UserRole.DOCTOR:
        doctor_result = await db.execute(
            select(Doctor).where(Doctor.user_id == current_user.user_id)
        )
        doctor = doctor_result.scalar_one_or_none()
        if not doctor or voice_note.doctor_id != doctor.doctor_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Doctors can only access their own voice notes",
            )
    elif current_user.role == UserRole.PATIENT:
        patient_result = await db.execute(
            select(Patient).where(Patient.user_id == current_user.user_id)
        )
        patient = patient_result.scalar_one_or_none()
        if not patient or voice_note.patient_id != patient.patient_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Patients can only access their own voice notes",
            )
    elif current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to access voice note",
        )
    
    return voice_note


@router.get("/appointment/{appointment_id}/", response_model=VoiceNoteListResponse)
async def list_appointment_voice_notes(
    appointment_id: UUID,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Page size"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """List voice notes for an appointment."""
    # Verify appointment exists
    appointment = await db.get(Appointment, appointment_id)
    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found",
        )
    
    # RBAC check
    if current_user.role == UserRole.DOCTOR:
        doctor_result = await db.execute(
            select(Doctor).where(Doctor.user_id == current_user.user_id)
        )
        doctor = doctor_result.scalar_one_or_none()
        if not doctor or appointment.doctor_id != doctor.doctor_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Doctors can only access voice notes for their own appointments",
            )
    elif current_user.role == UserRole.PATIENT:
        patient_result = await db.execute(
            select(Patient).where(Patient.user_id == current_user.user_id)
        )
        patient = patient_result.scalar_one_or_none()
        if not patient or appointment.patient_id != patient.patient_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Patients can only access voice notes for their own appointments",
            )
    elif current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to list voice notes",
        )
    
    # Build query
    query = select(VoiceNote).where(VoiceNote.appointment_id == appointment_id)
    count_query = select(func.count(VoiceNote.voice_note_id)).where(VoiceNote.appointment_id == appointment_id)
    
    # Get total count
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # Apply pagination
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    voice_notes = result.scalars().all()
    
    total_pages = (total + page_size - 1) // page_size
    
    return VoiceNoteListResponse(
        voice_notes=voice_notes,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.put("/{voice_note_id}/", response_model=VoiceNoteResponse)
async def update_voice_note(
    voice_note_id: UUID,
    voice_note_data: VoiceNoteUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Update a voice note (e.g., add transcription)."""
    voice_note = await db.get(VoiceNote, voice_note_id)
    if not voice_note:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Voice note not found",
        )
    
    # RBAC check - only the doctor who created it or admin can update
    if current_user.role == UserRole.DOCTOR:
        doctor_result = await db.execute(
            select(Doctor).where(Doctor.user_id == current_user.user_id)
        )
        doctor = doctor_result.scalar_one_or_none()
        if not doctor or voice_note.doctor_id != doctor.doctor_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Doctors can only update their own voice notes",
            )
    elif current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to update voice note",
        )
    
    # Update fields
    update_data = voice_note_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(voice_note, field, value)
    
    await db.commit()
    await db.refresh(voice_note)
    return voice_note


@router.delete("/{voice_note_id}/", status_code=status.HTTP_204_NO_CONTENT)
async def delete_voice_note(
    voice_note_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Delete a voice note and its associated file."""
    voice_note = await db.get(VoiceNote, voice_note_id)
    if not voice_note:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Voice note not found",
        )
    
    # RBAC check
    if current_user.role == UserRole.DOCTOR:
        doctor_result = await db.execute(
            select(Doctor).where(Doctor.user_id == current_user.user_id)
        )
        doctor = doctor_result.scalar_one_or_none()
        if not doctor or voice_note.doctor_id != doctor.doctor_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Doctors can only delete their own voice notes",
            )
    elif current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to delete voice note",
        )
    
    # Delete file from storage
    try:
        file_path = Path(voice_note.file_path)
        if file_path.exists():
            file_path.unlink()
    except Exception:
        pass  # Log error but continue with DB deletion
    
    # Delete from database
    await db.delete(voice_note)
    await db.commit()