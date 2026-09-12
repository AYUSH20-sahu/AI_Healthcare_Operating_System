"""FHIR R4 Interoperability Integration API (Milestone U-20).

Provides standard HL7 FHIR Release 4 RESTful endpoints for Patient, Appointment,
DiagnosticReport (MedicalRecord), MedicationRequest (Prescription), and Bundle
($everything operation) exports.

Strictly preserves internal database schemas and enforces fine-grained RBAC isolation.
"""

from typing import Any, Dict, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import (
    Appointment,
    Doctor,
    MedicalRecord,
    Patient,
    Prescription,
    User,
    UserRole,
)
from app.services.auth.service import get_current_active_user
from app.services.integration.fhir_mapper import (
    to_fhir_appointment,
    to_fhir_bundle,
    to_fhir_diagnostic_report,
    to_fhir_medication_request,
    to_fhir_patient,
)

router = APIRouter(prefix="/fhir", tags=["fhir-integration"])


async def _resolve_current_patient_id(db: AsyncSession, current_user: User) -> Optional[UUID]:
    """Helper to find the patient_id associated with a user if role is PATIENT."""
    if current_user.role == UserRole.PATIENT:
        stmt = select(Patient.patient_id).where(Patient.user_id == current_user.user_id)
        res = await db.execute(stmt)
        return res.scalar_one_or_none()
    return None


def _check_patient_access(target_patient_id: UUID, current_user: User, caller_patient_id: Optional[UUID]) -> None:
    """Ensure Patients cannot access other patients' FHIR records (403 Forbidden)."""
    if current_user.role == UserRole.PATIENT:
        if caller_patient_id != target_patient_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You are not authorized to view another patient's FHIR record.",
            )


@router.get("/Patient/{patient_id}")
async def get_fhir_patient(
    patient_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """Retrieve an HL7 FHIR R4 Patient resource."""
    caller_patient_id = await _resolve_current_patient_id(db, current_user)
    _check_patient_access(patient_id, current_user, caller_patient_id)

    patient = await db.get(Patient, patient_id)
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient {patient_id} not found",
        )

    return to_fhir_patient(patient)


@router.get("/Appointment/{appointment_id}")
async def get_fhir_appointment(
    appointment_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """Retrieve an HL7 FHIR R4 Appointment resource."""
    appointment = await db.get(Appointment, appointment_id)
    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Appointment {appointment_id} not found",
        )

    caller_patient_id = await _resolve_current_patient_id(db, current_user)
    _check_patient_access(appointment.patient_id, current_user, caller_patient_id)

    doctor = await db.get(Doctor, appointment.doctor_id)
    patient = await db.get(Patient, appointment.patient_id)

    return to_fhir_appointment(appointment, doctor=doctor, patient=patient)


@router.get("/DiagnosticReport/{record_id}")
async def get_fhir_diagnostic_report(
    record_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """Retrieve an HL7 FHIR R4 DiagnosticReport resource representing a Medical Record."""
    record = await db.get(MedicalRecord, record_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Medical record {record_id} not found",
        )

    caller_patient_id = await _resolve_current_patient_id(db, current_user)
    _check_patient_access(record.patient_id, current_user, caller_patient_id)

    doctor = await db.get(Doctor, record.doctor_id)
    patient = await db.get(Patient, record.patient_id)

    return to_fhir_diagnostic_report(record, doctor=doctor, patient=patient)


@router.get("/MedicationRequest/{prescription_id}")
async def get_fhir_medication_request(
    prescription_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """Retrieve an HL7 FHIR R4 MedicationRequest resource representing a Prescription."""
    prescription = await db.get(Prescription, prescription_id)
    if not prescription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Prescription {prescription_id} not found",
        )

    caller_patient_id = await _resolve_current_patient_id(db, current_user)
    _check_patient_access(prescription.patient_id, current_user, caller_patient_id)

    doctor = await db.get(Doctor, prescription.doctor_id)
    patient = await db.get(Patient, prescription.patient_id)

    return to_fhir_medication_request(prescription, doctor=doctor, patient=patient)


@router.get("/Patient/{patient_id}/$everything")
async def get_fhir_patient_everything(
    patient_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """HL7 FHIR R4 standard $everything operation: Returns comprehensive Patient Bundle."""
    caller_patient_id = await _resolve_current_patient_id(db, current_user)
    _check_patient_access(patient_id, current_user, caller_patient_id)

    patient = await db.get(Patient, patient_id)
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient {patient_id} not found",
        )

    # Fetch associated records, appointments, prescriptions
    appts_res = await db.execute(select(Appointment).where(Appointment.patient_id == patient_id))
    appointments = appts_res.scalars().all()

    recs_res = await db.execute(select(MedicalRecord).where(MedicalRecord.patient_id == patient_id))
    records = recs_res.scalars().all()

    rxs_res = await db.execute(select(Prescription).where(Prescription.patient_id == patient_id))
    prescriptions = rxs_res.scalars().all()

    return to_fhir_bundle(
        patient=patient,
        appointments=appointments,
        records=records,
        prescriptions=prescriptions,
    )


@router.get("/Bundle")
async def get_fhir_bundle(
    patient_id: Optional[UUID] = Query(None, description="Target patient ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """Retrieve FHIR R4 Bundle query."""
    caller_patient_id = await _resolve_current_patient_id(db, current_user)

    target_id = patient_id or caller_patient_id
    if not target_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="patient_id query parameter is required.",
        )

    _check_patient_access(target_id, current_user, caller_patient_id)

    patient = await db.get(Patient, target_id)
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient {target_id} not found",
        )

    appts_res = await db.execute(select(Appointment).where(Appointment.patient_id == target_id))
    appointments = appts_res.scalars().all()

    recs_res = await db.execute(select(MedicalRecord).where(MedicalRecord.patient_id == target_id))
    records = recs_res.scalars().all()

    rxs_res = await db.execute(select(Prescription).where(Prescription.patient_id == target_id))
    prescriptions = rxs_res.scalars().all()

    return to_fhir_bundle(
        patient=patient,
        appointments=appointments,
        records=records,
        prescriptions=prescriptions,
    )
