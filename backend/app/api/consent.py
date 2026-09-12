"""Consent API routes (Milestone U-18).

Provides patient-driven consent governance, provider authorization scopes,
verified revocation lifecycles, and immutable audit logging.
"""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import (
    AuditLog,
    AuditOutcome,
    Consent,
    ConsentScope,
    Doctor,
    Patient,
    User,
    UserRole,
)
from app.services.auth.service import get_current_active_user

router = APIRouter(prefix="/consents", tags=["consents"])


# =============================================================================
# Schemas
# =============================================================================

class ConsentCreate(BaseModel):
    """Schema for granting a new consent."""
    provider_id: UUID = Field(..., description="Target doctor / practitioner ID")
    patient_id: Optional[UUID] = Field(None, description="Patient ID (auto-filled for authenticated patients)")
    record_scope: ConsentScope = Field(default=ConsentScope.FULL_ACCESS, description="Access scope: full_access, records_only, appointments_only, notes_only")


class ConsentResponse(BaseModel):
    """Enriched consent response with provider metadata and active status."""
    consent_id: UUID
    patient_id: UUID
    provider_id: UUID
    provider_name: Optional[str] = None
    provider_specialty: Optional[str] = None
    provider_hospital: Optional[str] = None
    record_scope: ConsentScope
    is_active: bool = True
    granted_at: datetime
    revoked_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# =============================================================================
# Helper Utilities
# =============================================================================

async def _get_or_create_patient_for_user(db: AsyncSession, user: User) -> Patient:
    """Helper to safely retrieve the patient profile for a user."""
    result = await db.execute(select(Patient).where(Patient.user_id == user.user_id))
    patient = result.scalar_one_or_none()
    if not patient:
        from datetime import date
        patient = Patient(
            user_id=user.user_id,
            full_name=user.full_name or "Registered Patient",
            email=user.email,
            date_of_birth=date(1995, 1, 1),
            gender="Not Specified",
        )
        db.add(patient)
        await db.commit()
        await db.refresh(patient)
    return patient


def _to_consent_response(consent: Consent, provider: Optional[Doctor] = None) -> ConsentResponse:
    """Map Consent and Doctor ORM objects into enriched ConsentResponse."""
    return ConsentResponse(
        consent_id=consent.consent_id,
        patient_id=consent.patient_id,
        provider_id=consent.provider_id,
        provider_name=provider.full_name if provider else None,
        provider_specialty=provider.specialty if provider else None,
        provider_hospital=provider.hospital_affiliation if provider else None,
        record_scope=consent.record_scope,
        is_active=consent.revoked_at is None,
        granted_at=consent.granted_at,
        revoked_at=consent.revoked_at,
        created_at=consent.created_at,
        updated_at=consent.updated_at,
    )


# =============================================================================
# Endpoints
# =============================================================================

@router.get("/me", response_model=List[ConsentResponse])
async def list_my_consents(
    active_only: bool = Query(False, description="Filter for active non-revoked consents only"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Retrieve all consents granted by the authenticated patient with enriched provider metadata."""
    if current_user.role != UserRole.PATIENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only patients can access their personal consents via /me",
        )

    patient = await _get_or_create_patient_for_user(db, current_user)

    query = (
        select(Consent, Doctor)
        .outerjoin(Doctor, Consent.provider_id == Doctor.doctor_id)
        .where(Consent.patient_id == patient.patient_id)
    )
    if active_only:
        query = query.where(Consent.revoked_at.is_(None))

    query = query.order_by(Consent.granted_at.desc())
    results = (await db.execute(query)).all()

    return [_to_consent_response(c, doc) for c, doc in results]


@router.post("", response_model=ConsentResponse, status_code=status.HTTP_201_CREATED)
async def create_consent(
    consent_data: ConsentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Grant a new provider consent with immutable audit trail.
    
    Patients grant consent for themselves; administrators can grant on behalf of patients.
    """
    # 1. Resolve Patient ID
    if current_user.role == UserRole.PATIENT:
        patient = await _get_or_create_patient_for_user(db, current_user)
        target_patient_id = patient.patient_id
    elif current_user.role == UserRole.ADMIN:
        if not consent_data.patient_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="patient_id is required when granted by administrator",
            )
        target_patient_id = consent_data.patient_id
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to grant consent",
        )

    # 2. Check Provider Existence
    provider = await db.get(Doctor, consent_data.provider_id)
    if not provider:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Target healthcare provider (Doctor) not found",
        )

    # 3. Check for Existing Active Consent
    existing = await db.execute(
        select(Consent).where(
            and_(
                Consent.patient_id == target_patient_id,
                Consent.provider_id == consent_data.provider_id,
                Consent.revoked_at.is_(None),
            )
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An active consent agreement already exists for this patient and provider",
        )

    # 4. Create Consent
    consent = Consent(
        patient_id=target_patient_id,
        provider_id=consent_data.provider_id,
        record_scope=consent_data.record_scope,
        granted_at=datetime.utcnow(),
    )
    db.add(consent)
    await db.flush()

    # 5. Immutable Audit Log
    audit_entry = AuditLog(
        user_id=current_user.user_id,
        action="GRANT_CONSENT",
        resource_type="consents",
        resource_id=consent.consent_id,
        outcome=AuditOutcome.SUCCESS,
        details={
            "patient_id": str(target_patient_id),
            "provider_id": str(consent_data.provider_id),
            "provider_name": provider.full_name,
            "record_scope": consent_data.record_scope.value if hasattr(consent_data.record_scope, "value") else str(consent_data.record_scope),
            "granted_by_user": str(current_user.user_id),
        },
    )
    db.add(audit_entry)
    await db.commit()
    await db.refresh(consent)

    return _to_consent_response(consent, provider)


@router.delete("/{consent_id}", response_model=ConsentResponse)
async def revoke_consent_endpoint(
    consent_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Revoke an existing consent.
    
    Patients can revoke their own consents; administrators can revoke any.
    Sets revoked_at timestamp and records an immutable audit event.
    """
    query = (
        select(Consent, Doctor)
        .outerjoin(Doctor, Consent.provider_id == Doctor.doctor_id)
        .where(Consent.consent_id == consent_id)
    )
    res = (await db.execute(query)).first()
    if not res:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Consent agreement not found")

    consent, provider = res

    # Permission check
    if current_user.role == UserRole.PATIENT:
        patient = await _get_or_create_patient_for_user(db, current_user)
        if consent.patient_id != patient.patient_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You can only revoke your own consent agreements",
            )
    elif current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to revoke consent",
        )

    if consent.revoked_at is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Consent has already been revoked",
        )

    # Soft-revoke
    consent.revoked_at = datetime.utcnow()
    consent.updated_at = datetime.utcnow()

    # Immutable Audit Log
    audit_entry = AuditLog(
        user_id=current_user.user_id,
        action="REVOKE_CONSENT",
        resource_type="consents",
        resource_id=consent.consent_id,
        outcome=AuditOutcome.SUCCESS,
        details={
            "patient_id": str(consent.patient_id),
            "provider_id": str(consent.provider_id),
            "revoked_by_user": str(current_user.user_id),
            "revoked_at": consent.revoked_at.isoformat(),
        },
    )
    db.add(audit_entry)
    await db.commit()
    await db.refresh(consent)

    return _to_consent_response(consent, provider)


@router.get("/patients/{patient_id}", response_model=List[ConsentResponse])
async def list_patient_consents(
    patient_id: UUID,
    active_only: bool = Query(True, description="Filter for active consents only"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """List consents for a patient. Patients can only see their own; doctors and admins per permissions."""
    if current_user.role == UserRole.PATIENT:
        patient = await _get_or_create_patient_for_user(db, current_user)
        if patient_id != patient.patient_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: Patients can only view their own consent records",
            )
    elif current_user.role not in (UserRole.DOCTOR, UserRole.ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to view patient consents",
        )

    query = (
        select(Consent, Doctor)
        .outerjoin(Doctor, Consent.provider_id == Doctor.doctor_id)
        .where(Consent.patient_id == patient_id)
    )
    if active_only:
        query = query.where(Consent.revoked_at.is_(None))

    query = query.order_by(Consent.granted_at.desc())
    results = (await db.execute(query)).all()

    return [_to_consent_response(c, doc) for c, doc in results]


@router.get("/{consent_id}", response_model=ConsentResponse)
async def get_consent(
    consent_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Retrieve metadata of a specific consent."""
    query = (
        select(Consent, Doctor)
        .outerjoin(Doctor, Consent.provider_id == Doctor.doctor_id)
        .where(Consent.consent_id == consent_id)
    )
    res = (await db.execute(query)).first()
    if not res:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Consent not found")

    consent, provider = res

    if current_user.role == UserRole.PATIENT:
        patient = await _get_or_create_patient_for_user(db, current_user)
        if consent.patient_id != patient.patient_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: Cannot view another patient's consent",
            )
    elif current_user.role not in (UserRole.DOCTOR, UserRole.ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to view consent",
        )

    return _to_consent_response(consent, provider)