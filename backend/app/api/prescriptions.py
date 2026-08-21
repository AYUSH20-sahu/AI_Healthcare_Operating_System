"""Prescriptions API routes."""

from typing import Optional, List
from uuid import UUID
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Prescription, Patient, Doctor, User, UserRole, PrescriptionStatus, MedicalRecord
from app.services.auth.service import get_current_active_user
from app.api.schemas.prescription import (
    PrescriptionCreate,
    PrescriptionUpdate,
    PrescriptionResponse,
    PrescriptionListResponse,
    InteractionCheckResponse,
    InteractionWarning,
    MedicationCreate,
    InteractionCheckRequest,
)

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


def check_interactions(prescription_medications: List[dict], patient_allergies: List[str]) -> List[InteractionWarning]:
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
    status_filter: Optional[str] = Query(None, description="Filter by status (draft/finalized/cancelled)"),
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
    
    # Get patient allergies (stub - in reality would come from patient allergy records)
    # For now, we'll use a static list or could be extended to fetch from a patient_allergies table
    patient_allergies = []  # TODO: Fetch from patient allergy records
    
    # Convert MedicationCreate objects to dicts for check_interactions
    medications_dict = [med.model_dump() for med in medications]
    
    # Check interactions
    warnings = check_interactions(medications_dict, patient_allergies)
    
    return InteractionCheckResponse(
        warnings=warnings,
        has_warnings=len(warnings) > 0
    )