"""Prescriptions API routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.prescription import (
    InteractionCheckRequest,
    InteractionCheckResponse,
    InteractionWarning,
    PrescriptionCreate,
    PrescriptionDraftRequest,
    PrescriptionDraftResponse,
    PrescriptionListResponse,
    PrescriptionResponse,
    PrescriptionUpdate,
)
from app.database import get_db
from app.models import (
    Appointment,
    Doctor,
    MedicalRecord,
    Patient,
    Prescription,
    PrescriptionStatus,
    User,
    UserRole,
)
from app.services.auth.audit import audit_logger
from app.services.auth.service import get_current_active_user
from app.services.orchestrator import TaskRequest, TaskType, get_orchestrator

router = APIRouter(prefix="/prescriptions", tags=["prescriptions"])


# Static known drug interactions table (stub - will be replaced with real drug database)
KNOWN_INTERACTIONS = {
    ("warfarin", "aspirin"): {
        "severity": "severe",
        "description": "Increased risk of bleeding when warfarin is combined with aspirin",
        "recommendation": "Monitor INR closely; consider alternative analgesic"
    },
    ("warfarin", "ibuprofen"): {
        "severity": "severe",
        "description": "NSAIDs increase bleeding risk with warfarin",
        "recommendation": "Avoid combination; use acetaminophen instead"
    },
    ("lisinopril", "potassium"): {
        "severity": "moderate",
        "description": "ACE inhibitors can increase potassium levels",
        "recommendation": "Monitor serum potassium; adjust supplementation"
    },
    ("metformin", "contrast"): {
        "severity": "severe",
        "description": "Risk of lactic acidosis with IV contrast",
        "recommendation": "Hold metformin 48h before and after contrast administration"
    },
    ("simvastatin", "clarithromycin"): {
        "severity": "severe",
        "description": "Strong CYP3A4 inhibition increases statin levels",
        "recommendation": "Use alternative antibiotic or hold statin during therapy"
    },
    ("digoxin", "furosemide"): {
        "severity": "moderate",
        "description": "Loop diuretics can cause hypokalemia increasing digoxin toxicity",
        "recommendation": "Monitor potassium and digoxin levels"
    },
    ("methotrexate", "nsaids"): {
        "severity": "severe",
        "description": "NSAIDs reduce methotrexate clearance",
        "recommendation": "Avoid concurrent use; monitor for toxicity"
    },
}


# Static known allergies (stub - in reality would come from patient allergy records)
KNOWN_ALLERGIES = {
    "penicillin": ["amoxicillin", "ampicillin", "piperacillin", "ticarcillin"],
    "sulfa": ["sulfamethoxazole", "sulfasalazine", "sulfadiazine"],
    "aspirin": ["aspirin", "ibuprofen", "naproxen", "celecoxib"],  # NSAID cross-sensitivity
    "latex": [],  # Not a drug but relevant for medical supplies
}


def check_interactions(prescription_medications: list[dict], patient_allergies: list[str]) -> list[InteractionWarning]:
    """
    Check drug interactions and allergies for a prescription.
    
    This is a stub implementation using static tables.
    In production, this would integrate with a real drug database (e.g., First Databank, Medi-Span).
    
    Args:
        prescription_medications: List of medication dicts with 'name' key
        patient_allergies: List of patient's known allergies
        
    Returns:
        List of InteractionWarning objects
    """
    warnings = []
    med_names = [med.get("name", "").lower().strip() for med in prescription_medications]
    
    # Check drug-drug interactions
    for i, med1 in enumerate(med_names):
        for med2 in med_names[i+1:]:
            # Check both orderings
            for pair in [(med1, med2), (med2, med1)]:
                if pair in KNOWN_INTERACTIONS:
                    interaction = KNOWN_INTERACTIONS[pair]
                    warnings.append(InteractionWarning(
                        severity=interaction["severity"],
                        type="interaction",
                        medication=f"{pair[0].title()} + {pair[1].title()}",
                        description=interaction["description"],
                        recommendation=interaction.get("recommendation")
                    ))
    
    # Check drug-allergy interactions
    for allergy in patient_allergies:
        allergy_lower = allergy.lower().strip()
        if allergy_lower in KNOWN_ALLERGIES:
            cross_reactive = KNOWN_ALLERGIES[allergy_lower]
            for med in med_names:
                if med in cross_reactive:
                    warnings.append(InteractionWarning(
                        severity="severe",
                        type="allergy",
                        medication=med.title(),
                        description=f"Patient has known allergy to {allergy}; {med.title()} may cause cross-reaction",
                        recommendation=f"Avoid {med.title()}; use alternative medication class"
                    ))
        # Also check if the medication name matches the allergy directly
        for med in med_names:
            if med == allergy_lower:
                warnings.append(InteractionWarning(
                    severity="severe",
                    type="allergy",
                    medication=med.title(),
                    description=f"Patient has known allergy to {allergy}",
                    recommendation=f"Avoid {med.title()}; use alternative medication class"
                ))
    
    return warnings


@router.post("/", response_model=PrescriptionResponse, status_code=status.HTTP_201_CREATED)
async def create_prescription(
    prescription_data: PrescriptionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Create a new prescription. Only doctors can create prescriptions."""
    if current_user.role != UserRole.DOCTOR and current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only doctors can create prescriptions",
        )
    
    # Verify patient exists
    patient = await db.get(Patient, prescription_data.patient_id)
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found",
        )
    
    # Verify doctor exists
    doctor = await db.get(Doctor, prescription_data.doctor_id)
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
        if not current_doctor or current_doctor.doctor_id != prescription_data.doctor_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Doctors can only create prescriptions for themselves",
            )
    
    # Verify medical record exists if provided
    if prescription_data.medical_record_id:
        medical_record = await db.get(MedicalRecord, prescription_data.medical_record_id)
        if not medical_record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Medical record not found",
            )
        if medical_record.patient_id != prescription_data.patient_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Medical record does not belong to this patient",
            )
        if medical_record.doctor_id != prescription_data.doctor_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Medical record does not belong to this doctor",
            )
    
    # Force status to draft on creation
    prescription = Prescription(
        medical_record_id=prescription_data.medical_record_id,
        patient_id=prescription_data.patient_id,
        doctor_id=prescription_data.doctor_id,
        medications=[med.model_dump() for med in prescription_data.medications],
        status=PrescriptionStatus.DRAFT,
    )
    db.add(prescription)
    await db.commit()
    await db.refresh(prescription)
    return prescription


@router.post("/draft", response_model=PrescriptionDraftResponse, status_code=status.HTTP_201_CREATED)
async def draft_prescription(
    draft_req: PrescriptionDraftRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Draft an AI-assisted prescription with automated interaction and allergy safety review.
    
    Operates via Orchestrator (TaskType.PRESCRIPTION_DRAFT).
    Strict In-Memory Rule: Scribe/Prescription agent operates in-memory; only the Core API persists to PostgreSQL.
    Draft Invariant: Prescriptions are created strictly with status = PrescriptionStatus.DRAFT.
    """
    if current_user.role not in [UserRole.DOCTOR, UserRole.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only doctors and administrators can draft prescriptions",
        )
    
    # Verify patient exists
    patient = await db.get(Patient, draft_req.patient_id)
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found",
        )
    
    # Verify doctor exists
    doctor = await db.get(Doctor, draft_req.doctor_id)
    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Doctor not found",
        )
    
    # If doctor is creating, verify ownership
    if current_user.role == UserRole.DOCTOR:
        doctor_result = await db.execute(
            select(Doctor).where(Doctor.user_id == current_user.user_id)
        )
        current_doctor = doctor_result.scalar_one_or_none()
        if not current_doctor or current_doctor.doctor_id != draft_req.doctor_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Doctors can only draft prescriptions for themselves",
            )
            
    # Verify medical record exists if specified
    if draft_req.medical_record_id:
        mr = await db.get(MedicalRecord, draft_req.medical_record_id)
        if not mr:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Medical record not found",
            )
        if mr.patient_id != draft_req.patient_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Medical record does not belong to this patient",
            )
            
    # Verify appointment exists if specified
    if draft_req.appointment_id:
        appt = await db.get(Appointment, draft_req.appointment_id)
        if not appt:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Appointment not found",
            )
            
    # Prepare payload for in-memory PrescriptionDraftAgent
    agent_payload = {
        "consultation_text": draft_req.consultation_text or "",
        "assessment": draft_req.assessment or "",
        "icd10_code": draft_req.icd10_code or "",
        "suggested_medications": [m.model_dump() for m in draft_req.suggested_medications] if draft_req.suggested_medications else [],
        "patient_allergies": draft_req.patient_allergies or [],
        "current_medications": draft_req.current_medications or [],
        "patient_name": f"{patient.first_name} {patient.last_name}",
    }
    
    # Dispatch to orchestrator
    orchestrator = get_orchestrator()
    task_req = TaskRequest(
        task_type=TaskType.PRESCRIPTION_DRAFT,
        payload=agent_payload,
        timeout_seconds=30.0,
    )
    task_result = await orchestrator.dispatch(task_req)
    
    agent_res = task_result.result
    if not agent_res or not getattr(agent_res, "success", False):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Prescription draft orchestration failed: {task_result.error or 'Unknown agent error'}",
        )
        
    # Core API strictly persists the draft prescription with status = DRAFT
    medications_data = agent_res.medications
    prescription = Prescription(
        patient_id=draft_req.patient_id,
        doctor_id=draft_req.doctor_id,
        medical_record_id=draft_req.medical_record_id,
        medications=medications_data,
        status=PrescriptionStatus.DRAFT,
        notes=draft_req.notes,
    )
    db.add(prescription)
    await db.commit()
    await db.refresh(prescription)
    
    # Audit log
    await audit_logger.log_event(
        action="PRESCRIPTION_DRAFT_CREATED",
        user_id=current_user.user_id,
        resource_type="prescription",
        resource_id=prescription.prescription_id,
        details={
            "patient_id": str(draft_req.patient_id),
            "doctor_id": str(draft_req.doctor_id),
            "appointment_id": str(draft_req.appointment_id) if draft_req.appointment_id else None,
            "medical_record_id": str(draft_req.medical_record_id) if draft_req.medical_record_id else None,
            "status": "DRAFT",
            "medications_count": len(medications_data),
            "warnings_count": len(agent_res.warnings),
            "has_warnings": agent_res.has_warnings,
            "confidence": agent_res.confidence,
        },
    )
    
    return PrescriptionDraftResponse(
        prescription_id=prescription.prescription_id,
        patient_id=prescription.patient_id,
        doctor_id=prescription.doctor_id,
        appointment_id=draft_req.appointment_id,
        medical_record_id=prescription.medical_record_id,
        medications=medications_data,
        status="DRAFT",
        warnings=agent_res.warnings,
        has_warnings=agent_res.has_warnings,
        confidence=agent_res.confidence,
        basis=agent_res.basis,
        ai_metadata=agent_res.ai_metadata,
        notes=prescription.notes,
        created_at=prescription.created_at,
        updated_at=prescription.updated_at,
    )


@router.get("/{prescription_id}/", response_model=PrescriptionResponse)
async def get_prescription(
    prescription_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get a prescription by ID. Patients can read their own; doctors can read their patients'."""
    prescription = await db.get(Prescription, prescription_id)
    if not prescription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prescription not found",
        )
    
    # RBAC check
    if current_user.role == UserRole.PATIENT:
        patient_result = await db.execute(
            select(Patient).where(Patient.user_id == current_user.user_id)
        )
        patient = patient_result.scalar_one_or_none()
        if not patient or prescription.patient_id != patient.patient_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Patients can only read their own prescriptions",
            )
    elif current_user.role == UserRole.DOCTOR:
        doctor_result = await db.execute(
            select(Doctor).where(Doctor.user_id == current_user.user_id)
        )
        doctor = doctor_result.scalar_one_or_none()
        if not doctor or prescription.doctor_id != doctor.doctor_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Doctors can only read their own prescriptions",
            )
    elif current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to read prescription",
        )
    
    return prescription


@router.put("/{prescription_id}/", response_model=PrescriptionResponse)
async def update_prescription(
    prescription_id: UUID,
    prescription_data: PrescriptionUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Update a prescription. Doctors can update their own prescriptions; admins can update any."""
    prescription = await db.get(Prescription, prescription_id)
    if not prescription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prescription not found",
        )
    
    # RBAC check
    if current_user.role == UserRole.DOCTOR:
        doctor_result = await db.execute(
            select(Doctor).where(Doctor.user_id == current_user.user_id)
        )
        doctor = doctor_result.scalar_one_or_none()
        if not doctor or prescription.doctor_id != doctor.doctor_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Doctors can only update their own prescriptions",
            )
        # Doctors cannot finalize prescriptions directly (requires review flow)
        if prescription_data.status and prescription_data.status.upper() == "FINALIZED":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Doctors cannot finalize prescriptions directly (requires review flow)",
            )
    elif current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to update prescription",
        )
    
    # Update fields
    update_data = prescription_data.model_dump(exclude_unset=True)
    
    for field, value in update_data.items():
        if field == "medications" and value is not None:
            # value is already a list of dicts from model_dump
            setattr(prescription, field, value)
        else:
            setattr(prescription, field, value)
    
    await db.commit()
    await db.refresh(prescription)
    return prescription


@router.get("/patient/{patient_id}/", response_model=PrescriptionListResponse)
async def list_patient_prescriptions(
    patient_id: UUID,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Page size"),
    status_filter: str | None = Query(None, description="Filter by status (draft/finalized/cancelled)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """List prescriptions for a patient with pagination and filters."""
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
                detail="Patients can only list their own prescriptions",
            )
    elif current_user.role == UserRole.DOCTOR:
        # Doctors can list prescriptions for their patients
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
        from app.models import Appointment
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
                detail="Doctors can only list prescriptions for their own patients",
            )
    elif current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to list prescriptions",
        )
    
    # Build query
    query = select(Prescription).where(Prescription.patient_id == patient_id)
    count_query = select(func.count(Prescription.prescription_id)).where(Prescription.patient_id == patient_id)
    
    if status_filter:
        try:
            status_enum = PrescriptionStatus(status_filter.upper())
            query = query.where(Prescription.status == status_enum)
            count_query = count_query.where(Prescription.status == status_enum)
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
    prescriptions = result.scalars().all()
    
    total_pages = (total + page_size - 1) // page_size
    
    return PrescriptionListResponse(
        prescriptions=prescriptions,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/appointment/{appointment_id}/draft", response_model=PrescriptionDraftResponse | None)
async def get_appointment_draft_prescription(
    appointment_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Retrieve active draft prescription for an appointment if one exists.
    
    Enables instant state restoration when clinician returns or refreshes.
    """
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
                detail="Patients can only view prescriptions for their own appointments",
            )
    elif current_user.role == UserRole.DOCTOR:
        doctor_result = await db.execute(
            select(Doctor).where(Doctor.user_id == current_user.user_id)
        )
        doctor = doctor_result.scalar_one_or_none()
        if not doctor or appointment.doctor_id != doctor.doctor_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Doctors can only view prescriptions for their own appointments",
            )
    elif current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to view prescriptions",
        )
        
    # Find draft prescription linked either directly to medical records for this appointment or patient/doctor
    query = (
        select(Prescription)
        .join(MedicalRecord, Prescription.medical_record_id == MedicalRecord.record_id)
        .where(
            and_(
                MedicalRecord.appointment_id == appointment_id,
                Prescription.status == PrescriptionStatus.DRAFT,
            )
        )
        .order_by(Prescription.created_at.desc())
        .limit(1)
    )
    result = await db.execute(query)
    prescription = result.scalar_one_or_none()
    
    # If not found via medical record, search by patient and doctor
    if not prescription:
        alt_query = (
            select(Prescription)
            .where(
                and_(
                    Prescription.patient_id == appointment.patient_id,
                    Prescription.doctor_id == appointment.doctor_id,
                    Prescription.status == PrescriptionStatus.DRAFT,
                )
            )
            .order_by(Prescription.created_at.desc())
            .limit(1)
        )
        alt_res = await db.execute(alt_query)
        prescription = alt_res.scalar_one_or_none()
        
    if not prescription:
        return None
        
    from app.services.prescriptions.prescription_agent import prescription_agent
    warnings_list = prescription_agent.check_safety(
        medications=prescription.medications or [],
        patient_allergies=[],
    )
    warning_dicts = [
        {
            "severity": w.severity,
            "type": w.type,
            "medication": w.medication,
            "description": w.description,
            "recommendation": w.recommendation,
        }
        for w in warnings_list
    ]
    
    return PrescriptionDraftResponse(
        prescription_id=prescription.prescription_id,
        patient_id=prescription.patient_id,
        doctor_id=prescription.doctor_id,
        appointment_id=appointment_id,
        medical_record_id=prescription.medical_record_id,
        medications=prescription.medications or [],
        status="DRAFT",
        warnings=warning_dicts,
        has_warnings=len(warning_dicts) > 0,
        confidence=90,
        basis="Restored draft prescription for appointment review.",
        ai_metadata={"provider": "database", "model": "persisted-draft", "fallback_used": False},
        notes=prescription.notes,
        created_at=prescription.created_at,
        updated_at=prescription.updated_at,
    )


@router.get("/appointment/{appointment_id}/", response_model=PrescriptionListResponse)
async def list_appointment_prescriptions(
    appointment_id: UUID,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Page size"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """List prescriptions for an appointment."""
    # Verify appointment exists
    from app.models import Appointment
    appointment = await db.get(Appointment, appointment_id)
    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found",
        )
    
    # RBAC check - same as patient prescriptions
    if current_user.role == UserRole.PATIENT:
        patient_result = await db.execute(
            select(Patient).where(Patient.user_id == current_user.user_id)
        )
        patient = patient_result.scalar_one_or_none()
        if not patient or appointment.patient_id != patient.patient_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Patients can only view prescriptions for their own appointments",
            )
    elif current_user.role == UserRole.DOCTOR:
        doctor_result = await db.execute(
            select(Doctor).where(Doctor.user_id == current_user.user_id)
        )
        doctor = doctor_result.scalar_one_or_none()
        if not doctor or appointment.doctor_id != doctor.doctor_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Doctors can only view prescriptions for their own appointments",
            )
    elif current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to list prescriptions",
        )
    
    # Build query - prescriptions linked via medical record to appointment
    query = select(Prescription).join(MedicalRecord).where(MedicalRecord.appointment_id == appointment_id)
    count_query = select(func.count(Prescription.prescription_id)).join(MedicalRecord).where(MedicalRecord.appointment_id == appointment_id)
    
    # Get total count
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # Apply pagination
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    prescriptions = result.scalars().all()
    
    total_pages = (total + page_size - 1) // page_size
    
    return PrescriptionListResponse(
        prescriptions=prescriptions,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.post("/check-interactions/", response_model=InteractionCheckResponse)
async def check_prescription_interactions(
    request: InteractionCheckRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Check drug interactions and allergies for a proposed prescription.
    
    This endpoint allows doctors to check for potential issues before creating a prescription.
    """
    patient_id = request.patient_id
    medications = request.medications
    
    # Verify patient exists
    patient = await db.get(Patient, patient_id)
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found",
        )
    
    # RBAC check - only doctors and admins can check interactions
    if current_user.role not in [UserRole.DOCTOR, UserRole.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only doctors can check prescription interactions",
        )
    
    # If doctor, verify they treat this patient
    if current_user.role == UserRole.DOCTOR:
        doctor_result = await db.execute(
            select(Doctor).where(Doctor.user_id == current_user.user_id)
        )
        current_doctor = doctor_result.scalar_one_or_none()
        if not current_doctor:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Doctor profile not found",
            )
        
        from app.models import Appointment
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
                detail="Doctors can only check interactions for their own patients",
            )
    
    # Get patient allergies from request or patient record
    patient_allergies = request.patient_allergies if request.patient_allergies is not None else []
    current_medications = request.current_medications if request.current_medications is not None else []
    
    # Convert MedicationCreate objects to dicts
    medications_dict = [med.model_dump() for med in medications]
    
    # Run comprehensive safety check from prescription agent
    from app.services.prescriptions.prescription_agent import prescription_agent
    safety_warnings = prescription_agent.check_safety(
        medications=medications_dict,
        patient_allergies=patient_allergies,
        current_medications=current_medications,
    )
    
    # Also run static table check for any additional pairs
    static_warnings = check_interactions(medications_dict, patient_allergies)
    
    # Merge unique warnings
    all_warnings: list[InteractionWarning] = []
    seen_keys = set()
    
    for sw in safety_warnings:
        key = (sw.type, sw.medication.lower())
        if key not in seen_keys:
            seen_keys.add(key)
            all_warnings.append(InteractionWarning(
                severity=sw.severity,
                type=sw.type,
                medication=sw.medication,
                description=sw.description,
                recommendation=sw.recommendation,
            ))
            
    for stw in static_warnings:
        key = (stw.type, stw.medication.lower())
        if key not in seen_keys:
            seen_keys.add(key)
            all_warnings.append(stw)
    
    return InteractionCheckResponse(
        warnings=all_warnings,
        has_warnings=len(all_warnings) > 0
    )