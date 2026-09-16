from datetime import date, datetime, time, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.appointment import (
    AppointmentCreate,
    AppointmentListResponse,
    AppointmentResponse,
    AppointmentUpdate,
    DoctorAvailabilityResponse,
    PatientAppointmentBookRequest,
    TimeSlotItem,
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

router = APIRouter(prefix="/appointments", tags=["appointments"])


async def check_slot_conflict(
    db: AsyncSession,
    doctor_id: UUID,
    scheduled_at: datetime,
    duration_minutes: int,
    exclude_appointment_id: UUID | None = None
) -> Appointment | None:
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


@router.get("/availability", response_model=DoctorAvailabilityResponse)
async def get_doctor_availability(
    doctor_id: UUID = Query(..., description="Target doctor ID"),
    date_str: str = Query(..., description="Target date in YYYY-MM-DD format"),
    duration_minutes: int = Query(30, ge=15, le=120, description="Slot duration in minutes"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Calculate and return daily consultation time slots for a doctor, highlighting open vs booked slots."""
    doctor = await db.get(Doctor, doctor_id)
    if not doctor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Doctor not found.")

    try:
        target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid date format. Use YYYY-MM-DD.")

    # Retrieve all non-cancelled appointments for this doctor on target date
    start_of_day = datetime.combine(target_date, time(0, 0, 0))
    end_of_day = datetime.combine(target_date, time(23, 59, 59))

    query = select(Appointment).where(
        and_(
            Appointment.doctor_id == doctor_id,
            Appointment.scheduled_at >= start_of_day,
            Appointment.scheduled_at <= end_of_day,
            Appointment.status != AppointmentStatus.CANCELLED,
        )
    )
    result = await db.execute(query)
    booked_appointments = result.scalars().all()

    slots: list[TimeSlotItem] = []
    now_utc = datetime.utcnow()

    # Clinic hours: 9am - 1pm, 2pm - 5pm
    clinic_hours = [
        (9, 0, 13, 0),
        (14, 0, 17, 0),
    ]

    for start_h, start_m, end_h, end_m in clinic_hours:
        slot_dt = datetime.combine(target_date, time(start_h, start_m))
        session_end_dt = datetime.combine(target_date, time(end_h, end_m))

        while slot_dt + timedelta(minutes=duration_minutes) <= session_end_dt:
            slot_end = slot_dt + timedelta(minutes=duration_minutes)
            slot_time_str = slot_dt.strftime("%I:%M %p")

            # Check if in the past
            is_past = slot_dt < now_utc

            # Check conflict
            conflict = None
            for appt in booked_appointments:
                appt_end = appt.scheduled_at + timedelta(minutes=appt.duration_minutes)
                if slot_dt < appt_end and slot_end > appt.scheduled_at:
                    conflict = appt
                    break

            if is_past:
                is_available = False
                conflict_reason = "Past"
            elif conflict:
                is_available = False
                conflict_reason = "Booked"
            else:
                is_available = True
                conflict_reason = None

            slots.append(
                TimeSlotItem(
                    slot_time=slot_time_str,
                    start_time=slot_dt,
                    end_time=slot_end,
                    duration_minutes=duration_minutes,
                    is_available=is_available,
                    conflict_reason=conflict_reason,
                )
            )

            slot_dt = slot_end

    available_count = sum(1 for s in slots if s.is_available)

    return DoctorAvailabilityResponse(
        doctor_id=doctor.doctor_id,
        doctor_name=doctor.full_name,
        specialty=doctor.specialty,
        hospital_affiliation=doctor.hospital_affiliation,
        date=date_str,
        total_slots=len(slots),
        available_slots_count=available_count,
        slots=slots,
    )


@router.post("/book", response_model=AppointmentResponse, status_code=status.HTTP_201_CREATED)
async def book_patient_appointment(
    payload: PatientAppointmentBookRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Patient-facing appointment booking endpoint with automatic profile resolution and conflict locking."""
    # Resolve patient
    if current_user.role == UserRole.PATIENT:
        p_res = await db.execute(select(Patient).where(Patient.user_id == current_user.user_id))
        patient = p_res.scalar_one_or_none()
        if not patient:
            patient = Patient(
                user_id=current_user.user_id,
                full_name=current_user.full_name or "Patient",
                email=current_user.email,
                date_of_birth=date(1995, 1, 1),
                gender="Not Specified",
            )
            db.add(patient)
            await db.commit()
            await db.refresh(patient)
    elif current_user.role in (UserRole.ADMIN, UserRole.DOCTOR):
        p_res = await db.execute(select(Patient).limit(1))
        patient = p_res.scalar_one_or_none()
        if not patient:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No patient found in system.")
    else:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorized role.")

    doctor = await db.get(Doctor, payload.doctor_id)
    if not doctor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Doctor not found.")

    # Check for slot conflict
    conflicting = await check_slot_conflict(
        db,
        payload.doctor_id,
        payload.scheduled_at,
        payload.duration_minutes,
    )
    if conflicting:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This appointment slot is no longer available. Please select another time slot.",
        )

    # Contextual notes, linking intake session if available
    notes_text = payload.reason or ""
    if payload.intake_session_id:
        intake_res = await db.execute(
            select(IntakeSession).where(IntakeSession.session_id == payload.intake_session_id)
        )
        intake = intake_res.scalar_one_or_none()
        if intake and intake.structured_symptoms:
            struct = intake.structured_symptoms
            cc = struct.get("chief_complaint") or ""
            notes_text = f"[AI Intake]: {cc}. " + (notes_text if notes_text else "")

    appointment = Appointment(
        patient_id=patient.patient_id,
        doctor_id=doctor.doctor_id,
        scheduled_at=payload.scheduled_at,
        duration_minutes=payload.duration_minutes,
        status=AppointmentStatus.SCHEDULED,
        notes=notes_text.strip() or None,
    )
    db.add(appointment)
    await db.flush()

    # Assign room and meeting link
    appointment.telehealth_room_id = f"telehealth-{str(appointment.appointment_id)[:8]}"
    appointment.meeting_link = f"/doctor/consultations/{appointment.appointment_id}"

    await db.commit()
    await db.refresh(appointment)
    return appointment


@router.post("/", response_model=AppointmentResponse, status_code=status.HTTP_201_CREATED)
async def create_appointment(
    appointment_data: AppointmentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Create a new appointment. Validates no double-booking for the doctor."""
    # RBAC check: patients can only book for themselves
    if current_user.role == UserRole.PATIENT:
        p_res = await db.execute(select(Patient).where(Patient.user_id == current_user.user_id))
        caller_patient = p_res.scalar_one_or_none()
        if not caller_patient or caller_patient.patient_id != appointment_data.patient_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Patients can only book appointments for themselves.",
            )

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
    if not appointment.meeting_link:
        appointment.telehealth_room_id = f"telehealth-{str(appointment.appointment_id)[:8]}"
        appointment.meeting_link = f"/doctor/consultations/{appointment.appointment_id}"

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


@router.get("", response_model=AppointmentListResponse)
@router.get("/", response_model=AppointmentListResponse)
async def list_appointments(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Page size"),
    patient_id: UUID | None = Query(None, description="Filter by patient ID"),
    doctor_id: UUID | None = Query(None, description="Filter by doctor ID"),
    date_from: datetime | None = Query(None, description="Filter by date from"),
    date_to: datetime | None = Query(None, description="Filter by date to"),
    status: str | None = Query(None, description="Filter by status"),
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