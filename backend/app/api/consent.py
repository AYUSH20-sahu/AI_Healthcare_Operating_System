"""Consent API routes."""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import ConsentScope, User, UserRole
from app.services.auth.consent import (
    get_active_consents_for_patient,
    get_all_consents_for_patient,
    get_consent_by_id,
    grant_consent,
    revoke_consent,
)
from app.services.auth.service import get_current_active_user


class ConsentCreate(BaseModel):
    patient_id: UUID
    provider_id: UUID
    record_scope: ConsentScope = ConsentScope.FULL_ACCESS


class ConsentResponse(BaseModel):
    consent_id: UUID
    patient_id: UUID
    provider_id: UUID
    record_scope: ConsentScope
    granted_at: datetime
    revoked_at: datetime | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


router = APIRouter(prefix="/consents", tags=["consents"])


@router.post("", response_model=ConsentResponse, status_code=status.HTTP_201_CREATED)
async def create_consent(
    consent_data: ConsentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Grant a new consent. Patients can grant consent for themselves; doctors/admins can grant for patients."""
    # Check permissions
    if current_user.role == UserRole.PATIENT:
        # Patients can only grant consent for themselves
        if consent_data.patient_id != current_user.patient_profile.patient_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Patients can only grant consent for themselves",
            )
    elif current_user.role not in (UserRole.DOCTOR, UserRole.ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to grant consent",
        )
    
    try:
        consent = await grant_consent(
            db=db,
            patient_id=consent_data.patient_id,
            provider_id=consent_data.provider_id,
            record_scope=consent_data.record_scope,
        )
        return consent
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete("/{consent_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_consent_endpoint(
    consent_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Revoke a consent. Patients can revoke their own consents; admins can revoke any."""
    consent = await get_consent_by_id(db, consent_id)
    if not consent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Consent not found")
    
    # Check permissions
    if current_user.role == UserRole.PATIENT:
        if consent.patient_id != current_user.patient_profile.patient_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Patients can only revoke their own consents",
            )
    elif current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to revoke consent",
        )
    
    try:
        await revoke_consent(db, consent_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/patients/{patient_id}", response_model=list[ConsentResponse])
async def list_patient_consents(
    patient_id: UUID,
    active_only: bool = True,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """List consents for a patient. Patients can only see their own; doctors/admins can see any."""
    # Check permissions
    if current_user.role == UserRole.PATIENT:
        if patient_id != current_user.patient_profile.patient_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Patients can only view their own consents",
            )
    elif current_user.role not in (UserRole.DOCTOR, UserRole.ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to view consents",
        )
    
    if active_only:
        consents = await get_active_consents_for_patient(db, patient_id)
    else:
        consents = await get_all_consents_for_patient(db, patient_id)
    
    return consents


@router.get("/{consent_id}", response_model=ConsentResponse)
async def get_consent(
    consent_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get a specific consent."""
    consent = await get_consent_by_id(db, consent_id)
    if not consent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Consent not found")
    
    # Check permissions
    if current_user.role == UserRole.PATIENT:
        if consent.patient_id != current_user.patient_profile.patient_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Patients can only view their own consents",
            )
    elif current_user.role not in (UserRole.DOCTOR, UserRole.ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to view consent",
        )
    
    return consent