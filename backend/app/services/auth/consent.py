"""Consent service - grant, revoke, list consents."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Consent, ConsentScope, Doctor, Patient


async def grant_consent(
    db: AsyncSession,
    patient_id: UUID,
    provider_id: UUID,
    record_scope: ConsentScope = ConsentScope.FULL_ACCESS,
) -> Consent:
    """Grant a new consent."""
    # Check if patient exists
    patient = await db.get(Patient, patient_id)
    if not patient:
        raise ValueError("Patient not found")
    
    # Check if provider exists
    provider = await db.get(Doctor, provider_id)
    if not provider:
        raise ValueError("Provider not found")
    
    # Check for existing active consent
    existing = await db.execute(
        select(Consent).where(
            and_(
                Consent.patient_id == patient_id,
                Consent.provider_id == provider_id,
                Consent.revoked_at.is_(None),
            )
        )
    )
    if existing.scalar_one_or_none():
        raise ValueError("Active consent already exists for this patient-provider pair")
    
    consent = Consent(
        patient_id=patient_id,
        provider_id=provider_id,
        record_scope=record_scope,
        granted_at=datetime.utcnow(),
    )
    db.add(consent)
    await db.commit()
    await db.refresh(consent)
    return consent


async def revoke_consent(db: AsyncSession, consent_id: UUID) -> Consent:
    """Revoke a consent."""
    consent = await db.get(Consent, consent_id)
    if not consent:
        raise ValueError("Consent not found")
    
    if consent.revoked_at is not None:
        raise ValueError("Consent already revoked")
    
    consent.revoked_at = datetime.utcnow()
    consent.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(consent)
    return consent


async def get_active_consents_for_patient(db: AsyncSession, patient_id: UUID) -> list[Consent]:
    """Get all active consents for a patient."""
    result = await db.execute(
        select(Consent).where(
            and_(
                Consent.patient_id == patient_id,
                Consent.revoked_at.is_(None),
            )
        ).order_by(Consent.granted_at.desc())
    )
    return list(result.scalars().all())


async def get_all_consents_for_patient(db: AsyncSession, patient_id: UUID) -> list[Consent]:
    """Get all consents (active and revoked) for a patient."""
    result = await db.execute(
        select(Consent).where(
            Consent.patient_id == patient_id
        ).order_by(Consent.granted_at.desc())
    )
    return list(result.scalars().all())


async def get_consent_by_id(db: AsyncSession, consent_id: UUID) -> Consent | None:
    """Get a consent by ID."""
    return await db.get(Consent, consent_id)