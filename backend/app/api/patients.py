import logging
import os
import shutil
import uuid
from datetime import date, datetime
from pathlib import Path
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.patient import (
    PatientCreate,
    PatientListResponse,
    PatientResponse,
    PatientUpdate,
    PatientSelfUpdate,
    PatientPortalDashboardResponse,
    PatientPortalAppointmentItem,
    PatientPortalRecordItem,
    PatientPortalPrescriptionItem,
)
from app.api.schemas.patient_tools import (
    PatientReportResponse,
    PatientReportListResponse,
    MedicineReminderCreateRequest,
    MedicineReminderUpdateRequest,
    MedicineReminderResponse,
    MedicineReminderListResponse,
)
from app.database import get_db
from app.models import Patient, PatientReport, MedicineReminder, User, UserRole
from app.services.auth.service import get_current_active_user

logger = logging.getLogger(__name__)

# Constants for U-16 Report Management
ALLOWED_REPORT_MIME_TYPES = {
    "application/pdf",
    "image/png",
    "image/jpeg",
    "image/webp",
}
MAX_REPORT_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 Megabytes
BASE_REPORTS_DIR = Path("uploads/reports")

router = APIRouter(prefix="/patients", tags=["patients"])



@router.post("/", response_model=PatientResponse, status_code=status.HTTP_201_CREATED)
async def create_patient(
    patient_data: PatientCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Create a new patient. Only admins can create patients directly."""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can create patients",
        )
    
    # Check if ABHA address already exists
    if patient_data.abha_address:
        existing = await db.execute(
            select(Patient).where(Patient.abha_address == patient_data.abha_address)
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="ABHA address already registered",
            )
    
    patient = Patient(**patient_data.model_dump())
    db.add(patient)
    await db.commit()
    await db.refresh(patient)
    return patient


# =============================================================================
# Patient Portal Self Endpoints (Milestone U-12)
# =============================================================================

async def _get_or_create_patient_profile(db: AsyncSession, current_user: User) -> Patient:
    """Helper to retrieve or initialize the patient's own profile."""
    if current_user.role != UserRole.PATIENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only patient users can access this portal resource",
        )
    result = await db.execute(
        select(Patient).where(Patient.user_id == current_user.user_id)
    )
    patient = result.scalar_one_or_none()
    if not patient:
        from datetime import date
        patient = Patient(
            user_id=current_user.user_id,
            full_name=current_user.full_name or "Registered Patient",
            email=current_user.email,
            date_of_birth=date(1995, 1, 1),
            gender="Not Specified",
        )
        db.add(patient)
        await db.commit()
        await db.refresh(patient)
    return patient


@router.get("/me", response_model=PatientResponse)
async def get_my_patient_profile(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Retrieve authenticated patient's profile."""
    return await _get_or_create_patient_profile(db, current_user)


@router.put("/me", response_model=PatientResponse)
async def update_my_patient_profile(
    update_data: PatientSelfUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Update authenticated patient's own profile."""
    patient = await _get_or_create_patient_profile(db, current_user)
    
    # Check ABHA uniqueness if modified
    if update_data.abha_address and update_data.abha_address != patient.abha_address:
        existing = await db.execute(
            select(Patient).where(Patient.abha_address == update_data.abha_address)
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="ABHA address already registered",
            )

    data_dict = update_data.model_dump(exclude_unset=True)
    for field, value in data_dict.items():
        setattr(patient, field, value)

    await db.commit()
    await db.refresh(patient)
    return patient


@router.get("/me/dashboard", response_model=PatientPortalDashboardResponse)
async def get_my_patient_dashboard(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Fast summary endpoint for the patient portal dashboard."""
    patient = await _get_or_create_patient_profile(db, current_user)
    now = datetime.utcnow()

    # 1. Upcoming appointments count
    from app.models import Appointment, AppointmentStatus, Doctor, MedicalRecord, MedicalRecordStatus, Prescription, PrescriptionStatus
    appt_count_query = select(func.count(Appointment.appointment_id)).where(
        Appointment.patient_id == patient.patient_id,
        Appointment.status != AppointmentStatus.CANCELLED,
        Appointment.scheduled_at >= now,
    )
    upcoming_count = (await db.execute(appt_count_query)).scalar() or 0

    # 2. Next upcoming appointment
    next_appt_query = (
        select(Appointment, Doctor)
        .join(Doctor, Appointment.doctor_id == Doctor.doctor_id)
        .where(
            Appointment.patient_id == patient.patient_id,
            Appointment.status != AppointmentStatus.CANCELLED,
            Appointment.scheduled_at >= now,
        )
        .order_by(Appointment.scheduled_at.asc())
        .limit(1)
    )
    next_appt_result = (await db.execute(next_appt_query)).first()
    next_appt_item = None
    if next_appt_result:
        appt, doc = next_appt_result
        next_appt_item = PatientPortalAppointmentItem(
            appointment_id=appt.appointment_id,
            doctor_id=doc.doctor_id,
            doctor_name=doc.full_name,
            doctor_specialty=doc.specialty,
            hospital_affiliation=doc.hospital_affiliation,
            scheduled_at=appt.scheduled_at,
            duration_minutes=appt.duration_minutes,
            status=appt.status.value,
            reason=appt.reason,
            meeting_link=appt.meeting_link,
        )

    # 3. Finalized records count
    records_count_query = select(func.count(MedicalRecord.record_id)).where(
        MedicalRecord.patient_id == patient.patient_id,
        MedicalRecord.status.in_([MedicalRecordStatus.FINALIZED, MedicalRecordStatus.AMENDED]),
    )
    records_count = (await db.execute(records_count_query)).scalar() or 0

    # 4. Active prescriptions count & recent prescriptions
    rx_count_query = select(func.count(Prescription.prescription_id)).where(
        Prescription.patient_id == patient.patient_id,
        Prescription.status == PrescriptionStatus.FINALIZED,
    )
    rx_count = (await db.execute(rx_count_query)).scalar() or 0

    recent_rx_query = (
        select(Prescription, Doctor)
        .join(Doctor, Prescription.doctor_id == Doctor.doctor_id)
        .where(
            Prescription.patient_id == patient.patient_id,
            Prescription.status == PrescriptionStatus.FINALIZED,
        )
        .order_by(Prescription.created_at.desc())
        .limit(3)
    )
    recent_rx_result = (await db.execute(recent_rx_query)).all()
    recent_rx_items = [
        PatientPortalPrescriptionItem(
            prescription_id=rx.prescription_id,
            doctor_id=doc.doctor_id,
            doctor_name=doc.full_name,
            medical_record_id=rx.medical_record_id,
            status=rx.status.value,
            medications=rx.medications or [],
            notes=rx.notes,
            finalized_at=rx.finalized_at,
            created_at=rx.created_at,
        )
        for rx, doc in recent_rx_result
    ]

    return PatientPortalDashboardResponse(
        patient=patient,
        upcoming_appointments_count=upcoming_count,
        finalized_records_count=records_count,
        active_prescriptions_count=rx_count,
        next_appointment=next_appt_item,
        recent_prescriptions=recent_rx_items,
    )


@router.get("/me/appointments", response_model=list[PatientPortalAppointmentItem])
async def get_my_patient_appointments(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """List all appointments for the authenticated patient."""
    patient = await _get_or_create_patient_profile(db, current_user)
    from app.models import Appointment, Doctor
    query = (
        select(Appointment, Doctor)
        .join(Doctor, Appointment.doctor_id == Doctor.doctor_id)
        .where(Appointment.patient_id == patient.patient_id)
        .order_by(Appointment.scheduled_at.desc())
    )
    results = (await db.execute(query)).all()
    return [
        PatientPortalAppointmentItem(
            appointment_id=appt.appointment_id,
            doctor_id=doc.doctor_id,
            doctor_name=doc.full_name,
            doctor_specialty=doc.specialty,
            hospital_affiliation=doc.hospital_affiliation,
            scheduled_at=appt.scheduled_at,
            duration_minutes=appt.duration_minutes,
            status=appt.status.value,
            reason=appt.reason,
            meeting_link=appt.meeting_link,
        )
        for appt, doc in results
    ]


@router.get("/me/records", response_model=list[PatientPortalRecordItem])
async def get_my_patient_records(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """List finalized medical records for the authenticated patient."""
    patient = await _get_or_create_patient_profile(db, current_user)
    from app.models import MedicalRecord, MedicalRecordStatus, Doctor
    query = (
        select(MedicalRecord, Doctor)
        .join(Doctor, MedicalRecord.doctor_id == Doctor.doctor_id)
        .where(
            MedicalRecord.patient_id == patient.patient_id,
            MedicalRecord.status.in_([MedicalRecordStatus.FINALIZED, MedicalRecordStatus.AMENDED]),
        )
        .order_by(MedicalRecord.created_at.desc())
    )
    results = (await db.execute(query)).all()
    return [
        PatientPortalRecordItem(
            record_id=mr.record_id,
            doctor_id=doc.doctor_id,
            doctor_name=doc.full_name,
            appointment_id=mr.appointment_id,
            status=mr.status.value,
            chief_complaint=mr.content.get("chief_complaint") if mr.content else None,
            assessment=mr.content.get("assessment") if mr.content else None,
            plan=mr.content.get("plan") if mr.content else None,
            content=mr.content,
            finalized_at=mr.finalized_at,
            created_at=mr.created_at,
        )
        for mr, doc in results
    ]


@router.get("/me/prescriptions", response_model=list[PatientPortalPrescriptionItem])
async def get_my_patient_prescriptions(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """List finalized prescriptions for the authenticated patient."""
    patient = await _get_or_create_patient_profile(db, current_user)
    from app.models import Prescription, PrescriptionStatus, Doctor
    query = (
        select(Prescription, Doctor)
        .join(Doctor, Prescription.doctor_id == Doctor.doctor_id)
        .where(
            Prescription.patient_id == patient.patient_id,
            Prescription.status == PrescriptionStatus.FINALIZED,
        )
        .order_by(Prescription.created_at.desc())
    )
    results = (await db.execute(query)).all()
    return [
        PatientPortalPrescriptionItem(
            prescription_id=rx.prescription_id,
            doctor_id=doc.doctor_id,
            doctor_name=doc.full_name,
            medical_record_id=rx.medical_record_id,
            status=rx.status.value,
            medications=rx.medications or [],
            notes=rx.notes,
            finalized_at=rx.finalized_at,
            created_at=rx.created_at,
        )
        for rx, doc in results
    ]


# =============================================================================
# Milestone U-16: Patient Medical Reports Endpoints
# =============================================================================

@router.post("/me/reports", response_model=PatientReportResponse, status_code=status.HTTP_201_CREATED)
async def upload_patient_report(
    file: UploadFile = File(...),
    title: str = Form(...),
    report_type: str = Form("other"),
    notes: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Securely upload a medical report for the authenticated patient with MIME, magic-byte, and size validation."""
    from app.core.security import sanitize_filename, validate_file_upload

    patient = await _get_or_create_patient_profile(db, current_user)

    # 1. Read bytes and perform comprehensive security validation (MIME, size, magic bytes)
    file_bytes = await file.read()
    content_type = file.content_type or "application/octet-stream"
    safe_name = sanitize_filename(file.filename or "medical_report.pdf")

    validate_file_upload(
        file_bytes=file_bytes,
        filename=safe_name,
        content_type=content_type,
        max_size_bytes=MAX_REPORT_FILE_SIZE_BYTES,
        allowed_mimes=ALLOWED_REPORT_MIME_TYPES,
        allowed_extensions={"pdf", "png", "jpg", "jpeg", "webp"},
    )

    # 2. Secure isolated directory: uploads/reports/{patient_id}/
    patient_dir = BASE_REPORTS_DIR / str(patient.patient_id)
    patient_dir.mkdir(parents=True, exist_ok=True)

    unique_filename = f"{uuid.uuid4().hex[:12]}_{safe_name}"
    file_target_path = patient_dir / unique_filename

    with open(file_target_path, "wb") as f:
        f.write(file_bytes)

    # 4. Save metadata in DB
    report = PatientReport(
        patient_id=patient.patient_id,
        title=title.strip() if title else safe_filename,
        report_type=report_type.lower().strip() if report_type else "other",
        file_name=safe_filename,
        file_path=str(file_target_path.resolve()),
        file_size_bytes=file_size,
        mime_type=content_type,
        notes=notes.strip() if notes else None,
    )
    db.add(report)
    await db.commit()
    await db.refresh(report)

    logger.info(
        "Uploaded patient report %s (%s, %d bytes) for patient %s",
        report.report_id,
        report.file_name,
        report.file_size_bytes,
        patient.patient_id,
    )
    return report


@router.get("/me/reports", response_model=PatientReportListResponse)
async def list_my_patient_reports(
    report_type: Optional[str] = Query(None, description="Filter by report category (lab, imaging, prescription, discharge, other)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """List all medical reports uploaded by or for the authenticated patient."""
    patient = await _get_or_create_patient_profile(db, current_user)
    query = select(PatientReport).where(PatientReport.patient_id == patient.patient_id)
    if report_type:
        query = query.where(PatientReport.report_type == report_type.lower().strip())
    query = query.order_by(PatientReport.created_at.desc())

    result = await db.execute(query)
    reports = list(result.scalars().all())
    return PatientReportListResponse(reports=reports, total=len(reports))


@router.get("/me/reports/{report_id}", response_model=PatientReportResponse)
async def get_my_patient_report(
    report_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Retrieve metadata of a specific medical report for the authenticated patient."""
    patient = await _get_or_create_patient_profile(db, current_user)
    report = await db.get(PatientReport, report_id)
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Medical report not found",
        )
    if report.patient_id != patient.patient_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: You cannot access another patient's medical report",
        )
    return report


@router.get("/me/reports/{report_id}/download")
async def download_my_patient_report(
    report_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Stream download authenticated patient's medical report file."""
    patient = await _get_or_create_patient_profile(db, current_user)
    report = await db.get(PatientReport, report_id)
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Medical report not found",
        )
    if report.patient_id != patient.patient_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: You cannot download another patient's medical report",
        )

    file_path = Path(report.file_path)
    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report file does not exist on storage",
        )

    return FileResponse(
        path=str(file_path),
        filename=report.file_name,
        media_type=report.mime_type,
    )


@router.delete("/me/reports/{report_id}")
async def delete_my_patient_report(
    report_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Delete a medical report and remove its file from disk storage."""
    patient = await _get_or_create_patient_profile(db, current_user)
    report = await db.get(PatientReport, report_id)
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Medical report not found",
        )
    if report.patient_id != patient.patient_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: You cannot delete another patient's medical report",
        )

    # Attempt physical unlinking
    try:
        file_path = Path(report.file_path)
        if file_path.exists():
            file_path.unlink()
    except Exception as exc:
        logger.warning("Could not delete report file %s: %s", report.file_path, exc)

    await db.delete(report)
    await db.commit()
    return {"detail": "Medical report deleted successfully", "report_id": str(report_id)}


# =============================================================================
# Milestone U-16: Patient Medicine Reminders Endpoints
# =============================================================================

@router.get("/me/reminders", response_model=MedicineReminderListResponse)
async def list_my_medicine_reminders(
    active_only: Optional[bool] = Query(None, description="Filter for active reminders only"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """List medicine reminders for the authenticated patient."""
    patient = await _get_or_create_patient_profile(db, current_user)
    query = select(MedicineReminder).where(MedicineReminder.patient_id == patient.patient_id)
    if active_only is not None:
        query = query.where(MedicineReminder.is_active == active_only)
    query = query.order_by(MedicineReminder.created_at.desc())

    result = await db.execute(query)
    reminders = list(result.scalars().all())
    return MedicineReminderListResponse(reminders=reminders, total=len(reminders))


@router.post("/me/reminders", response_model=MedicineReminderResponse, status_code=status.HTTP_201_CREATED)
async def create_my_medicine_reminder(
    reminder_data: MedicineReminderCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Create a new medicine reminder and register schedule dispatch stub."""
    patient = await _get_or_create_patient_profile(db, current_user)

    reminder = MedicineReminder(
        patient_id=patient.patient_id,
        medication_name=reminder_data.medication_name.strip(),
        dosage=reminder_data.dosage.strip(),
        frequency=reminder_data.frequency.strip(),
        times_of_day=reminder_data.times_of_day,
        instructions=reminder_data.instructions.strip() if reminder_data.instructions else None,
        start_date=reminder_data.start_date,
        end_date=reminder_data.end_date,
        is_active=reminder_data.is_active,
    )
    db.add(reminder)
    await db.commit()
    await db.refresh(reminder)

    # Master prompt strict rule: Transparent logging of scheduler dispatch stub
    logger.info(
        "[Scheduler Stub] Scheduled reminder job for %s at %s for patient %s (delivery channel: simulated scheduler stub; external SMS/Push delivery pending)",
        reminder.medication_name,
        reminder.times_of_day,
        patient.patient_id,
    )

    return reminder


@router.put("/me/reminders/{reminder_id}", response_model=MedicineReminderResponse)
async def update_my_medicine_reminder(
    reminder_id: UUID,
    update_data: MedicineReminderUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Update or toggle active status of a medicine reminder."""
    patient = await _get_or_create_patient_profile(db, current_user)
    reminder = await db.get(MedicineReminder, reminder_id)
    if not reminder:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Medicine reminder not found",
        )
    if reminder.patient_id != patient.patient_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: You cannot update another patient's medicine reminder",
        )

    data = update_data.model_dump(exclude_unset=True)
    for field, val in data.items():
        if field in ("medication_name", "dosage", "frequency", "instructions") and isinstance(val, str):
            setattr(reminder, field, val.strip())
        else:
            setattr(reminder, field, val)

    await db.commit()
    await db.refresh(reminder)

    logger.info(
        "[Scheduler Stub] Updated reminder schedule for %s (active=%s, times=%s)",
        reminder.medication_name,
        reminder.is_active,
        reminder.times_of_day,
    )
    return reminder


@router.delete("/me/reminders/{reminder_id}")
async def delete_my_medicine_reminder(
    reminder_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Delete a medicine reminder."""
    patient = await _get_or_create_patient_profile(db, current_user)
    reminder = await db.get(MedicineReminder, reminder_id)
    if not reminder:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Medicine reminder not found",
        )
    if reminder.patient_id != patient.patient_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: You cannot delete another patient's medicine reminder",
        )

    await db.delete(reminder)
    await db.commit()

    logger.info("[Scheduler Stub] Cancelled reminder job for %s", reminder.medication_name)
    return {"detail": "Medicine reminder deleted successfully", "reminder_id": str(reminder_id)}


@router.get("/{patient_id}/reports", response_model=PatientReportListResponse)
async def list_patient_reports_for_provider(
    patient_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Allow healthcare providers (Doctors and Admins) to view a patient's medical reports."""
    if current_user.role not in (UserRole.DOCTOR, UserRole.ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only doctors and admins can view patient reports via provider endpoint",
        )
    patient = await db.get(Patient, patient_id)
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found",
        )
    query = select(PatientReport).where(PatientReport.patient_id == patient_id).order_by(PatientReport.created_at.desc())
    result = await db.execute(query)
    reports = list(result.scalars().all())
    return PatientReportListResponse(reports=reports, total=len(reports))


@router.get("/{patient_id}/", response_model=PatientResponse)
async def get_patient(
    patient_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get a patient by ID. Patients can only read their own record; doctors/admins per permissions."""
    patient = await db.get(Patient, patient_id)
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found",
        )
    
    # RBAC check
    if current_user.role == UserRole.PATIENT:
        if patient.user_id != current_user.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Patients can only read their own record",
            )
    elif current_user.role not in (UserRole.DOCTOR, UserRole.ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to read patient record",
        )
    
    return patient


@router.put("/{patient_id}/", response_model=PatientResponse)
async def update_patient(
    patient_id: UUID,
    patient_data: PatientUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Update a patient. Patients can only update their own record; admins can update any."""
    patient = await db.get(Patient, patient_id)
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found",
        )
    
    # RBAC check
    if current_user.role == UserRole.PATIENT:
        if patient.user_id != current_user.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Patients can only update their own record",
            )
    elif current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to update patient record",
        )
    
    # Check ABHA address uniqueness if being updated
    if patient_data.abha_address and patient_data.abha_address != patient.abha_address:
        existing = await db.execute(
            select(Patient).where(Patient.abha_address == patient_data.abha_address)
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="ABHA address already registered",
            )
    
    # Update fields
    update_data = patient_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(patient, field, value)
    
    await db.commit()
    await db.refresh(patient)
    return patient


@router.get("/", response_model=PatientListResponse)
async def list_patients(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Page size"),
    search: str | None = Query(None, description="Search by name or ABHA address"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """List patients with pagination. Only doctors and admins can list patients."""
    if current_user.role not in (UserRole.DOCTOR, UserRole.ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only doctors and admins can list patients",
        )
    
    query = select(Patient)
    
    if search:
        query = query.where(
            (Patient.full_name.ilike(f"%{search}%")) |
            (Patient.abha_address.ilike(f"%{search}%"))
        )
    
    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query)
    
    # Apply pagination
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    patients = list(result.scalars().all())
    
    total_pages = (total + page_size - 1) // page_size
    
    return PatientListResponse(
        patients=patients,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )