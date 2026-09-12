"""Ayushman Bharat Digital Mission (ABDM) Integration API (Milestone U-21).

Provides endpoints for:
- Gateway status and sandbox configuration inspection (Zero Credential Exposure)
- ABHA address / health ID linking and OTP verification
- Consent Manager HIU / HIP lifecycle requests & webhook notifications
- HFR (Health Facility Registry) and HPR (Healthcare Professionals Registry) stubs
"""

from typing import Any, Dict, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Doctor, Patient, User, UserRole
from app.services.auth.service import get_current_active_user
from app.services.integration.abdm import ABDMIntegrationService

router = APIRouter(prefix="/abdm", tags=["abdm-integration"])


# =============================================================================
# Schemas
# =============================================================================

class AbhaInitRequest(BaseModel):
    abha_address: str = Field(..., description="Target ABHA address (e.g. rahul@abdm or 14-digit number)")
    auth_mode: str = Field("MOBILE_OTP", description="Authentication mode: MOBILE_OTP or AADHAAR_OTP")


class AbhaVerifyRequest(BaseModel):
    transaction_id: str = Field(..., description="Transaction ID returned by /abha/init")
    otp: str = Field(..., min_length=4, max_length=10, description="Verification OTP received on mobile (123456 in sandbox)")


class ConsentRequestPayload(BaseModel):
    provider_id: UUID = Field(..., description="Target clinician doctor ID")
    record_scope: str = Field("full_access", description="Scope of records requested")
    purpose: str = Field("Care Consultation", description="Clinical purpose of use")


class ConsentNotificationPayload(BaseModel):
    notification_id: Optional[str] = None
    request_id: Optional[str] = None
    status: str = Field("GRANTED", description="Status: GRANTED, DENIED, REVOKED")
    consent_artefact_id: Optional[str] = None


# =============================================================================
# Helper Resolvers
# =============================================================================

async def _resolve_patient_for_current_user(db: AsyncSession, current_user: User) -> Patient:
    """Retrieve the patient profile for the authenticated user, or raise 403."""
    if current_user.role != UserRole.PATIENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only patient accounts can manage personal ABHA address linking.",
        )
    stmt = select(Patient).where(Patient.user_id == current_user.user_id)
    res = await db.execute(stmt)
    patient = res.scalar_one_or_none()
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


# =============================================================================
# Endpoints
# =============================================================================

@router.get("/status")
async def get_abdm_gateway_status() -> Dict[str, Any]:
    """Retrieve public ABDM gateway and sandbox configuration status.
    
    CRITICAL: Never exposes ABDM_CLIENT_SECRET or sensitive internal tokens.
    """
    return ABDMIntegrationService.get_gateway_status()


@router.post("/abha/init")
async def initiate_abha_link(
    payload: AbhaInitRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """Initiate an ABHA linking transaction with OTP dispatch."""
    patient = await _resolve_patient_for_current_user(db, current_user)
    try:
        return ABDMIntegrationService.initiate_abha_linking(
            patient=patient,
            abha_address=payload.abha_address,
            auth_mode=payload.auth_mode,
        )
    except ValueError as val_err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(val_err))


@router.post("/abha/verify")
async def verify_abha_link(
    payload: AbhaVerifyRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """Verify OTP and link the validated ABHA address to the patient profile."""
    patient = await _resolve_patient_for_current_user(db, current_user)
    try:
        return await ABDMIntegrationService.verify_abha_linking(
            patient=patient,
            transaction_id=payload.transaction_id,
            otp=payload.otp,
            db=db,
            current_user=current_user,
        )
    except PermissionError as perm_err:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(perm_err))
    except ValueError as val_err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(val_err))


@router.delete("/abha/unlink")
async def unlink_abha_address(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """Unlink the ABHA address from the current patient profile."""
    patient = await _resolve_patient_for_current_user(db, current_user)
    return await ABDMIntegrationService.unlink_abha(
        patient=patient,
        db=db,
        current_user=current_user,
    )


@router.post("/consent/request")
async def request_abdm_consent(
    payload: ConsentRequestPayload,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """Create an ABDM Consent Request artefact."""
    patient = await _resolve_patient_for_current_user(db, current_user)
    provider = await db.get(Doctor, payload.provider_id)
    if not provider:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Provider not found.")

    return ABDMIntegrationService.create_consent_request(
        patient_id=patient.patient_id,
        provider_id=payload.provider_id,
        record_scope=payload.record_scope,
        purpose=payload.purpose,
    )


@router.post("/consent/notification")
async def consent_manager_notification_webhook(
    payload: ConsentNotificationPayload,
) -> Dict[str, Any]:
    """Callback webhook for ABDM Consent Manager notifications."""
    return ABDMIntegrationService.handle_consent_notification(payload.dict())


@router.get("/consent/{request_id}")
async def get_consent_request_status(
    request_id: str,
    current_user: User = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """Inspect the status of an ABDM consent request artefact."""
    return ABDMIntegrationService.get_consent_status(request_id)


@router.get("/hfr")
async def get_hfr_info() -> Dict[str, Any]:
    """Retrieve Health Facility Registry profile for the facility."""
    return ABDMIntegrationService.get_hfr_facility_info()


@router.get("/hpr/{doctor_id}")
async def get_hpr_info(
    doctor_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """Retrieve Healthcare Professionals Registry profile for an attending doctor."""
    doctor = await db.get(Doctor, doctor_id)
    if not doctor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Doctor not found.")
    return ABDMIntegrationService.get_hpr_practitioner_info(doctor)
