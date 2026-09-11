from datetime import date, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
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
from app.database import get_db
from app.models import Patient, User, UserRole
from app.services.auth.service import get_current_active_user

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