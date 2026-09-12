"""Telehealth & Doctor Schedule Consultation Endpoints for AI-HOS (Milestone U-14).

Provides endpoints for daily doctor scheduling, active consultation room context,
red-flag detection integration from U-13 intake summaries, and real-time consultation lifecycle.
"""

from datetime import date, datetime, time, timedelta
import re
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.telehealth import (
    DoctorScheduleItemResponse,
    DoctorScheduleListResponse,
    PatientIntakeSummary,
    TelehealthActionResponse,
    TelehealthRoomResponse,
)
from app.database import get_db
from app.models import (
    Appointment,
    AppointmentStatus,
    Doctor,
    IntakeSession,
    Patient,
    User,
    UserRole,
)
from app.services.auth.service import get_current_active_user

router = APIRouter(prefix="/telehealth", tags=["telehealth"])

# Defined clinical red-flag patterns for emergency detection & triage
RED_FLAG_PATTERNS = [
    (r"(?i)\b(chest\s*pain|crushing\s*pressure|cardiac|heart\s*attack|angina)\b", "Severe Acute Cardiovascular Symptom (Red Flag)"),
    (r"(?i)\b(shortness\s*of\s*breath|cannot\s*breathe|difficulty\s*breathing|asphyxiation|gasping)\b", "Acute Respiratory Distress (Red Flag)"),
    (r"(?i)\b(sudden\s*numbness|facial\s*droop|slurred\s*speech|stroke|paralysis)\b", "Acute Neurological / Stroke Indicator (Red Flag)"),
    (r"(?i)\b(uncontrolled\s*bleeding|hemorrhage|coughing\s*blood|vomiting\s*blood)\b", "Severe Uncontrolled Hemorrhage (Red Flag)"),
    (r"(?i)\b(loss\s*of\s*consciousness|unresponsive|syncope|fainted|blacked\s*out)\b", "Impaired Consciousness / Syncope (Red Flag)"),
    (r"(?i)\b(severe\s*anaphylaxis|throat\s*swelling|tongue\s*swelling|allergic\s*shock)\b", "Acute Anaphylactic Shock (Red Flag)"),
]


def detect_red_flags(text: str) -> list[str]:
    """Scan clinical text for immediate emergency red-flag triggers."""
    warnings = []
    for pattern, label in RED_FLAG_PATTERNS:
        if re.search(pattern, text):
            warnings.append(label)
    return warnings


async def _resolve_doctor_profile(db: AsyncSession, current_user: User) -> Doctor:
    """Retrieve or initialize the attending doctor's profile."""
    if current_user.role != UserRole.DOCTOR and current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only doctors and clinical administrators can access this schedule resource.",
        )
    stmt = select(Doctor).where(Doctor.user_id == current_user.user_id)
    res = await db.execute(stmt)
    doctor = res.scalar_one_or_none()
    if not doctor:
        doctor = Doctor(
            user_id=current_user.user_id,
            license_number=f"DOC-LIC-{str(current_user.user_id)[:8].upper()}",
            specialty="General Medicine",
            full_name=current_user.full_name or "Attending Physician",
            email=current_user.email,
            hospital_affiliation="AI-HOS Medical Center",
        )
        db.add(doctor)
        await db.commit()
        await db.refresh(doctor)
    return doctor


async def _get_patient_intake_summary(db: AsyncSession, patient_id: UUID) -> Optional[PatientIntakeSummary]:
    """Retrieve the most recent intake session and run red-flag detection."""
    stmt = (
        select(IntakeSession)
        .where(IntakeSession.patient_id == patient_id)
        .order_by(desc(IntakeSession.created_at))
        .limit(1)
    )
    res = await db.execute(stmt)
    intake = res.scalar_one_or_none()
    if not intake:
        return None

    struct = intake.structured_symptoms or {}
    chief_complaint = struct.get("chief_complaint")
    duration = struct.get("duration")
    severity = struct.get("severity")
    associated = struct.get("associated_symptoms") or []
    summary = struct.get("summary")

    # Aggregate text for red-flag scan
    corpus = f"{chief_complaint or ''} {' '.join(associated)} {summary or ''}"
    if intake.messages:
        corpus += " " + " ".join(m.get("content", "") for m in intake.messages if m.get("role") in ("patient", "user"))

    warnings = detect_red_flags(corpus)

    return PatientIntakeSummary(
        session_id=intake.session_id,
        chief_complaint=chief_complaint,
        duration=duration,
        severity=int(severity) if severity is not None else None,
        associated_symptoms=associated,
        summary=summary,
        has_red_flags=len(warnings) > 0,
        red_flag_warnings=warnings,
    )


@router.get("/schedule", response_model=DoctorScheduleListResponse)
async def get_doctor_schedule(
    date_str: Optional[str] = Query(None, description="Date in YYYY-MM-DD format (defaults to today)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Retrieve the doctor's appointment schedule enriched with patient intake summaries."""
    doctor = await _resolve_doctor_profile(db, current_user)

    if date_str:
        try:
            target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid date format. Use YYYY-MM-DD.")
    else:
        target_date = date.today()

    start_dt = datetime.combine(target_date, time.min)
    end_dt = datetime.combine(target_date, time.max)

    stmt = (
        select(Appointment)
        .where(
            Appointment.doctor_id == doctor.doctor_id,
            Appointment.scheduled_at >= start_dt,
            Appointment.scheduled_at <= end_dt,
            Appointment.status != AppointmentStatus.CANCELLED,
        )
        .order_by(Appointment.scheduled_at)
    )
    res = await db.execute(stmt)
    appointments = res.scalars().all()

    items: list[DoctorScheduleItemResponse] = []
    in_consultation_count = 0
    scheduled_count = 0
    completed_count = 0

    for appt in appointments:
        # Load patient
        p_res = await db.execute(select(Patient).where(Patient.patient_id == appt.patient_id))
        patient = p_res.scalar_one_or_none()

        patient_name = patient.full_name if patient else "Patient"
        patient_gender = patient.gender if patient else None
        patient_abha = patient.abha_address if patient else None
        patient_phone = patient.phone if patient else None
        patient_age = None
        if patient and patient.date_of_birth:
            today = date.today()
            patient_age = today.year - patient.date_of_birth.year - (
                (today.month, today.day) < (patient.date_of_birth.month, patient.date_of_birth.day)
            )

        intake_summary = await _get_patient_intake_summary(db, appt.patient_id)

        status_val = appt.status.value if hasattr(appt.status, "value") else str(appt.status)
        if status_val == "in_progress":
            in_consultation_count += 1
        elif status_val == "completed":
            completed_count += 1
        else:
            scheduled_count += 1

        items.append(
            DoctorScheduleItemResponse(
                appointment_id=appt.appointment_id,
                patient_id=appt.patient_id,
                patient_name=patient_name,
                patient_gender=patient_gender,
                patient_age=patient_age,
                patient_abha=patient_abha,
                patient_phone=patient_phone,
                scheduled_at=appt.scheduled_at,
                duration_minutes=appt.duration_minutes,
                status=status_val,
                meeting_link=appt.meeting_link,
                telehealth_room_id=appt.telehealth_room_id,
                notes=appt.notes,
                intake_summary=intake_summary,
            )
        )

    return DoctorScheduleListResponse(
        date=target_date.isoformat(),
        total_appointments=len(items),
        scheduled_count=scheduled_count,
        in_consultation_count=in_consultation_count,
        completed_count=completed_count,
        appointments=items,
    )


@router.get("/rooms/{appointment_id}", response_model=TelehealthRoomResponse)
async def get_telehealth_room(
    appointment_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Retrieve active telehealth room details, verifying participant authorization."""
    stmt = select(Appointment).where(Appointment.appointment_id == appointment_id)
    res = await db.execute(stmt)
    appointment = res.scalar_one_or_none()
    if not appointment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Appointment not found.")

    # Load participants
    d_res = await db.execute(select(Doctor).where(Doctor.doctor_id == appointment.doctor_id))
    doctor = d_res.scalar_one_or_none()

    p_res = await db.execute(select(Patient).where(Patient.patient_id == appointment.patient_id))
    patient = p_res.scalar_one_or_none()

    # RBAC Access Control
    is_authorized = False
    if current_user.role == UserRole.ADMIN:
        is_authorized = True
    elif current_user.role == UserRole.DOCTOR and doctor and doctor.user_id == current_user.user_id:
        is_authorized = True
    elif current_user.role == UserRole.PATIENT and patient and patient.user_id == current_user.user_id:
        is_authorized = True

    if not is_authorized:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: You are not an authorized participant for this consultation room.",
        )

    # Initialize room identifiers if not already assigned
    if not appointment.telehealth_room_id:
        appointment.telehealth_room_id = f"telehealth-{str(appointment.appointment_id)[:8]}"
    if not appointment.meeting_link:
        appointment.meeting_link = f"/doctor/consultations/{appointment.appointment_id}"
        await db.commit()
        await db.refresh(appointment)

    intake_summary = await _get_patient_intake_summary(db, appointment.patient_id)

    patient_age = None
    if patient and patient.date_of_birth:
        today = date.today()
        patient_age = today.year - patient.date_of_birth.year - (
            (today.month, today.day) < (patient.date_of_birth.month, patient.date_of_birth.day)
        )

    status_val = appointment.status.value if hasattr(appointment.status, "value") else str(appointment.status)

    return TelehealthRoomResponse(
        appointment_id=appointment.appointment_id,
        room_id=appointment.telehealth_room_id,
        meeting_link=appointment.meeting_link,
        status=status_val,
        doctor_id=appointment.doctor_id,
        doctor_name=doctor.full_name if doctor else "Doctor",
        doctor_specialty=doctor.specialty if doctor else "General Physician",
        doctor_hospital=doctor.hospital_affiliation if doctor else "AI-HOS Medical Center",
        patient_id=appointment.patient_id,
        patient_name=patient.full_name if patient else "Patient",
        patient_gender=patient.gender if patient else None,
        patient_age=patient_age,
        patient_abha=patient.abha_address if patient else None,
        patient_phone=patient.phone if patient else None,
        scheduled_at=appointment.scheduled_at,
        duration_minutes=appointment.duration_minutes,
        intake_summary=intake_summary,
        telehealth_started_at=appointment.telehealth_started_at,
        telehealth_ended_at=appointment.telehealth_ended_at,
    )


@router.post("/rooms/{appointment_id}/start", response_model=TelehealthActionResponse)
async def start_telehealth_consultation(
    appointment_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Doctor starts the telehealth consultation session."""
    stmt = select(Appointment).where(Appointment.appointment_id == appointment_id)
    res = await db.execute(stmt)
    appointment = res.scalar_one_or_none()
    if not appointment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Appointment not found.")

    # Doctor verification
    d_res = await db.execute(select(Doctor).where(Doctor.doctor_id == appointment.doctor_id))
    doctor = d_res.scalar_one_or_none()
    if current_user.role != UserRole.ADMIN and (not doctor or doctor.user_id != current_user.user_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the attending physician can start this consultation room.",
        )

    now = datetime.utcnow()
    appointment.telehealth_started_at = now
    appointment.telehealth_room_id = f"telehealth-{str(appointment.appointment_id)[:8]}"
    appointment.meeting_link = f"/doctor/consultations/{appointment.appointment_id}"
    appointment.status = AppointmentStatus.IN_PROGRESS

    await db.commit()
    await db.refresh(appointment)

    return TelehealthActionResponse(
        appointment_id=appointment.appointment_id,
        status=appointment.status.value,
        message="Telehealth consultation room started successfully.",
        meeting_link=appointment.meeting_link,
        telehealth_started_at=appointment.telehealth_started_at,
    )


@router.post("/rooms/{appointment_id}/end", response_model=TelehealthActionResponse)
async def end_telehealth_consultation(
    appointment_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Doctor completes and concludes the telehealth consultation."""
    stmt = select(Appointment).where(Appointment.appointment_id == appointment_id)
    res = await db.execute(stmt)
    appointment = res.scalar_one_or_none()
    if not appointment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Appointment not found.")

    d_res = await db.execute(select(Doctor).where(Doctor.doctor_id == appointment.doctor_id))
    doctor = d_res.scalar_one_or_none()
    if current_user.role != UserRole.ADMIN and (not doctor or doctor.user_id != current_user.user_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the attending physician can conclude this consultation room.",
        )

    now = datetime.utcnow()
    appointment.telehealth_ended_at = now
    appointment.status = AppointmentStatus.COMPLETED

    await db.commit()
    await db.refresh(appointment)

    return TelehealthActionResponse(
        appointment_id=appointment.appointment_id,
        status=appointment.status.value,
        message="Telehealth consultation concluded successfully.",
        meeting_link=appointment.meeting_link,
        telehealth_started_at=appointment.telehealth_started_at,
        telehealth_ended_at=appointment.telehealth_ended_at,
    )
