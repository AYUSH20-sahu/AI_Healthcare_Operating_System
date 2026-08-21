"""Tests for consent service."""

from datetime import datetime
from uuid import uuid4

import pytest
import pytest_asyncio

from app.models import ConsentScope, Doctor, Patient, User, UserRole
from app.services.auth.consent import (
    get_active_consents_for_patient,
    get_all_consents_for_patient,
    get_consent_by_id,
    grant_consent,
    revoke_consent,
)


@pytest_asyncio.fixture
async def test_user(db_session):
    """Create a test user."""
    from app.services.auth.service import get_password_hash
    user = User(
        user_id=uuid4(),
        email="test@example.com",
        hashed_password=get_password_hash("testpassword123"),
        full_name="Test User",
        role=UserRole.PATIENT,
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def test_patient(db_session, test_user):
    """Create a test patient."""
    patient = Patient(
        patient_id=uuid4(),
        user_id=test_user.user_id,
        abha_address="test@abdm",
        full_name="Test Patient",
        date_of_birth=datetime(1990, 1, 1),
        gender="female",
        phone="+91-9876543210",
        email="patient@test.com",
    )
    db_session.add(patient)
    await db_session.commit()
    await db_session.refresh(patient)
    return patient


@pytest_asyncio.fixture
async def test_doctor_user(db_session):
    """Create a test doctor user."""
    from app.services.auth.service import get_password_hash
    user = User(
        user_id=uuid4(),
        email="doctor@test.com",
        hashed_password=get_password_hash("testpassword123"),
        full_name="Dr. Test",
        role=UserRole.DOCTOR,
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def test_doctor(db_session, test_doctor_user):
    """Create a test doctor."""
    doctor = Doctor(
        doctor_id=uuid4(),
        user_id=test_doctor_user.user_id,
        specialty="Cardiology",
        license_number="MD-CARD-001",
        hospital_affiliation="Test Hospital",
        email="doctor@test.com",
        full_name="Dr. Test",
        phone="+91-9876543210",
    )
    db_session.add(doctor)
    await db_session.commit()
    await db_session.refresh(doctor)
    return doctor


class TestConsentService:
    """Test consent service functions."""

    @pytest.mark.asyncio
    async def test_grant_consent(self, db_session, test_patient, test_doctor):
        """Test granting a new consent."""
        consent = await grant_consent(
            db=db_session,
            patient_id=test_patient.patient_id,
            provider_id=test_doctor.doctor_id,
            record_scope=ConsentScope.FULL_ACCESS,
        )
        
        assert consent.patient_id == test_patient.patient_id
        assert consent.provider_id == test_doctor.doctor_id
        assert consent.record_scope == ConsentScope.FULL_ACCESS
        assert consent.granted_at is not None
        assert consent.revoked_at is None

    @pytest.mark.asyncio
    async def test_grant_consent_duplicate_fails(self, db_session, test_patient, test_doctor):
        """Test that granting duplicate consent fails."""
        await grant_consent(
            db=db_session,
            patient_id=test_patient.patient_id,
            provider_id=test_doctor.doctor_id,
        )
        
        with pytest.raises(ValueError, match="Active consent already exists"):
            await grant_consent(
                db=db_session,
                patient_id=test_patient.patient_id,
                provider_id=test_doctor.doctor_id,
            )

    @pytest.mark.asyncio
    async def test_revoke_consent(self, db_session, test_patient, test_doctor):
        """Test revoking a consent."""
        consent = await grant_consent(
            db=db_session,
            patient_id=test_patient.patient_id,
            provider_id=test_doctor.doctor_id,
        )
        
        revoked = await revoke_consent(db_session, consent.consent_id)
        
        assert revoked.revoked_at is not None
        assert revoked.consent_id == consent.consent_id

    @pytest.mark.asyncio
    async def test_revoke_already_revoked_fails(self, db_session, test_patient, test_doctor):
        """Test that revoking already revoked consent fails."""
        consent = await grant_consent(
            db=db_session,
            patient_id=test_patient.patient_id,
            provider_id=test_doctor.doctor_id,
        )
        
        await revoke_consent(db_session, consent.consent_id)
        
        with pytest.raises(ValueError, match="Consent already revoked"):
            await revoke_consent(db_session, consent.consent_id)

    @pytest.mark.asyncio
    async def test_get_active_consents_for_patient(self, db_session, test_patient, test_doctor):
        """Test getting active consents for a patient."""
        await grant_consent(
            db=db_session,
            patient_id=test_patient.patient_id,
            provider_id=test_doctor.doctor_id,
        )
        
        consents = await get_active_consents_for_patient(db_session, test_patient.patient_id)
        
        assert len(consents) == 1
        assert consents[0].patient_id == test_patient.patient_id
        assert consents[0].revoked_at is None

    @pytest.mark.asyncio
    async def test_get_all_consents_for_patient(self, db_session, test_patient, test_doctor):
        """Test getting all consents for a patient."""
        consent = await grant_consent(
            db=db_session,
            patient_id=test_patient.patient_id,
            provider_id=test_doctor.doctor_id,
        )
        
        await revoke_consent(db_session, consent.consent_id)
        
        all_consents = await get_all_consents_for_patient(db_session, test_patient.patient_id)
        active_consents = await get_active_consents_for_patient(db_session, test_patient.patient_id)
        
        assert len(all_consents) == 1
        assert len(active_consents) == 0

    @pytest.mark.asyncio
    async def test_get_consent_by_id(self, db_session, test_patient, test_doctor):
        """Test getting a consent by ID."""
        consent = await grant_consent(
            db=db_session,
            patient_id=test_patient.patient_id,
            provider_id=test_doctor.doctor_id,
        )
        
        retrieved = await get_consent_by_id(db_session, consent.consent_id)
        
        assert retrieved is not None
        assert retrieved.consent_id == consent.consent_id
        
        # Test non-existent
        not_found = await get_consent_by_id(db_session, uuid4())
        assert not_found is None