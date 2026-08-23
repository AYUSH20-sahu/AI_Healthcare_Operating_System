"""Tests for Doctor Review/Approval API (M23)."""

import pytest
import pytest_asyncio
from datetime import datetime, date
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Doctor,
    MedicalRecord,
    MedicalRecordStatus,
    Patient,
    Prescription,
    PrescriptionStatus,
    User,
    UserRole,
)
from app.services.auth.service import create_access_token, get_password_hash


@pytest_asyncio.fixture
async def test_doctor_user(db_session: AsyncSession):
    """Create a test doctor user."""
    user = User(
        email="doctor@test.com",
        hashed_password=get_password_hash("password123"),
        full_name="Dr. John Doe",
        role=UserRole.DOCTOR,
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()
    
    doctor = Doctor(
        user_id=user.user_id,
        license_number="DOC12345",
        specialty="Cardiology",
        full_name="Dr. John Doe",
        email="doctor@test.com",
    )
    db_session.add(doctor)
    await db_session.commit()
    await db_session.refresh(user)
    await db_session.refresh(doctor)
    return user, doctor


@pytest_asyncio.fixture
async def test_doctor_user2(db_session: AsyncSession):
    """Create a second test doctor user."""
    user = User(
        email="doctor2@test.com",
        hashed_password=get_password_hash("password123"),
        full_name="Dr. Jane Smith",
        role=UserRole.DOCTOR,
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()
    
    doctor = Doctor(
        user_id=user.user_id,
        license_number="DOC67890",
        specialty="Neurology",
        full_name="Dr. Jane Smith",
        email="doctor2@test.com",
    )
    db_session.add(doctor)
    await db_session.commit()
    await db_session.refresh(user)
    await db_session.refresh(doctor)
    return user, doctor


@pytest_asyncio.fixture
async def test_admin_user(db_session: AsyncSession):
    """Create a test admin user."""
    user = User(
        email="admin@test.com",
        hashed_password=get_password_hash("password123"),
        full_name="Admin User",
        role=UserRole.ADMIN,
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def test_patient_user(db_session: AsyncSession):
    """Create a test patient user."""
    user = User(
        email="patient@test.com",
        hashed_password=get_password_hash("password123"),
        full_name="Alice Patient",
        role=UserRole.PATIENT,
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()
    
    patient = Patient(
        user_id=user.user_id,
        abha_address="alice@abha",
        full_name="Alice Patient",
        date_of_birth=date(1990, 1, 1),
        gender="female",
    )
    db_session.add(patient)
    await db_session.commit()
    await db_session.refresh(user)
    await db_session.refresh(patient)
    return user, patient


@pytest_asyncio.fixture
async def test_appointment(db_session: AsyncSession, test_doctor_user, test_patient_user):
    """Create a test appointment."""
    from app.models import Appointment, AppointmentStatus
    _, doctor = test_doctor_user
    _, patient = test_patient_user
    
    appointment = Appointment(
        patient_id=patient.patient_id,
        doctor_id=doctor.doctor_id,
        scheduled_at=datetime.utcnow(),
        status=AppointmentStatus.SCHEDULED,
        notes="Follow-up",
    )
    db_session.add(appointment)
    await db_session.commit()
    await db_session.refresh(appointment)
    return appointment


@pytest_asyncio.fixture
async def draft_medical_record(db_session: AsyncSession, test_doctor_user, test_patient_user, test_appointment):
    """Create a draft medical record."""
    _, doctor = test_doctor_user
    _, patient = test_patient_user
    
    record = MedicalRecord(
        patient_id=patient.patient_id,
        doctor_id=doctor.doctor_id,
        appointment_id=test_appointment.appointment_id,
        content={
            "chief_complaint": "Chest pain",
            "history_present_illness": "Patient reports chest pain for 2 hours",
            "physical_examination": "BP 140/90, HR 88",
            "assessment": "Possible angina",
            "plan": "ECG, troponin, cardiology referral",
            "diagnosis_codes": ["I20.9"],
            "confidence": 0.92,
            "basis": "Transcription describes classic anginal symptoms",
        },
        status=MedicalRecordStatus.DRAFT,
    )
    db_session.add(record)
    await db_session.commit()
    await db_session.refresh(record)
    return record


@pytest_asyncio.fixture
async def draft_prescription(db_session: AsyncSession, test_doctor_user, test_patient_user):
    """Create a draft prescription."""
    _, doctor = test_doctor_user
    _, patient = test_patient_user
    
    prescription = Prescription(
        patient_id=patient.patient_id,
        doctor_id=doctor.doctor_id,
        medications=[
            {"name": "Aspirin", "dosage": "81mg", "frequency": "once daily", "duration": "30 days"},
            {"name": "Metoprolol", "dosage": "50mg", "frequency": "twice daily", "duration": "30 days"},
        ],
        status=PrescriptionStatus.DRAFT,
    )
    db_session.add(prescription)
    await db_session.commit()
    await db_session.refresh(prescription)
    return prescription


@pytest_asyncio.fixture
async def finalized_medical_record(db_session: AsyncSession, test_doctor_user, test_patient_user):
    """Create a finalized medical record (should not be reviewable)."""
    _, doctor = test_doctor_user
    _, patient = test_patient_user
    
    record = MedicalRecord(
        patient_id=patient.patient_id,
        doctor_id=doctor.doctor_id,
        content={
            "chief_complaint": "Headache",
            "assessment": "Migraine",
        },
        status=MedicalRecordStatus.FINALIZED,
    )
    db_session.add(record)
    await db_session.commit()
    await db_session.refresh(record)
    return record


class TestDraftListing:
    """Tests for listing drafts for review."""

    @pytest.mark.asyncio
    async def test_list_drafts_doctor(self, client: AsyncClient, test_doctor_user, draft_medical_record, draft_prescription):
        """Test doctor can list their drafts."""
        user, doctor = test_doctor_user
        token = create_access_token({"sub": str(user.user_id), "role": user.role.value})
        
        response = await client.get(
            "/api/v1/approval/drafts",
            headers={"Authorization": f"Bearer {token}"},
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert len(data["medical_records"]) == 1
        assert len(data["prescriptions"]) == 1
        assert data["medical_records"][0]["record_id"] == str(draft_medical_record.record_id)
        assert data["prescriptions"][0]["prescription_id"] == str(draft_prescription.prescription_id)

    @pytest.mark.asyncio
    async def test_list_drafts_admin(self, client: AsyncClient, test_admin_user, draft_medical_record, draft_prescription):
        """Test admin can list all drafts."""
        token = create_access_token({"sub": str(test_admin_user.user_id), "role": test_admin_user.role.value})
        
        response = await client.get(
            "/api/v1/approval/drafts",
            headers={"Authorization": f"Bearer {token}"},
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2

    @pytest.mark.asyncio
    async def test_list_drafts_patient_forbidden(self, client: AsyncClient, test_patient_user):
        """Test patient cannot list drafts."""
        user, _ = test_patient_user
        token = create_access_token({"sub": str(user.user_id), "role": user.role.value})
        
        response = await client.get(
            "/api/v1/approval/drafts",
            headers={"Authorization": f"Bearer {token}"},
        )
        
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_list_drafts_doctor_only_sees_own(self, client: AsyncClient, test_doctor_user, test_doctor_user2, draft_medical_record):
        """Test doctor only sees their own drafts."""
        user, doctor = test_doctor_user
        token = create_access_token({"sub": str(user.user_id), "role": user.role.value})
        
        response = await client.get(
            "/api/v1/approval/drafts",
            headers={"Authorization": f"Bearer {token}"},
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1  # Only their own draft


class TestMedicalRecordReview:
    """Tests for medical record review."""

    @pytest.mark.asyncio
    async def test_approve_medical_record(self, client: AsyncClient, test_doctor_user, draft_medical_record):
        """Test doctor can approve a draft medical record."""
        user, doctor = test_doctor_user
        token = create_access_token({"sub": str(user.user_id), "role": user.role.value})
        
        response = await client.post(
            f"/api/v1/approval/medical-records/{draft_medical_record.record_id}/review",
            headers={"Authorization": f"Bearer {token}"},
            json={"action": "approve", "reviewer_notes": "Looks good"},
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["action"] == "approve"
        assert data["status"] == "FINALIZED"
        assert data["message"] == "Medical record approved and finalized"

    @pytest.mark.asyncio
    async def test_reject_medical_record(self, client: AsyncClient, test_doctor_user, draft_medical_record):
        """Test doctor can reject a draft medical record."""
        user, doctor = test_doctor_user
        token = create_access_token({"sub": str(user.user_id), "role": user.role.value})
        
        response = await client.post(
            f"/api/v1/approval/medical-records/{draft_medical_record.record_id}/review",
            headers={"Authorization": f"Bearer {token}"},
            json={"action": "reject", "reviewer_notes": "Missing assessment"},
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["action"] == "reject"
        assert data["status"] == "AMENDED"
        assert data["message"] == "Medical record rejected"

    @pytest.mark.asyncio
    async def test_request_changes_medical_record(self, client: AsyncClient, test_doctor_user, draft_medical_record):
        """Test doctor can request changes on a draft medical record."""
        user, doctor = test_doctor_user
        token = create_access_token({"sub": str(user.user_id), "role": user.role.value})
        
        response = await client.post(
            f"/api/v1/approval/medical-records/{draft_medical_record.record_id}/review",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "action": "request_changes",
                "reviewer_notes": "Add more detail to HPI",
                "edited_content": {"history_present_illness": "Updated HPI with more detail"}
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["action"] == "request_changes"
        assert data["status"] == "DRAFT"  # Stays draft
        assert data["message"] == "Changes requested on medical record"

    @pytest.mark.asyncio
    async def test_review_medical_record_other_doctor_forbidden(self, client: AsyncClient, test_doctor_user2, draft_medical_record):
        """Test doctor cannot review another doctor's record."""
        user, _ = test_doctor_user2
        token = create_access_token({"sub": str(user.user_id), "role": user.role.value})
        
        response = await client.post(
            f"/api/v1/approval/medical-records/{draft_medical_record.record_id}/review",
            headers={"Authorization": f"Bearer {token}"},
            json={"action": "approve"},
        )
        
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_review_medical_record_patient_forbidden(self, client: AsyncClient, test_patient_user, draft_medical_record):
        """Test patient cannot review medical records."""
        user, _ = test_patient_user
        token = create_access_token({"sub": str(user.user_id), "role": user.role.value})
        
        response = await client.post(
            f"/api/v1/approval/medical-records/{draft_medical_record.record_id}/review",
            headers={"Authorization": f"Bearer {token}"},
            json={"action": "approve"},
        )
        
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_review_finalized_record_forbidden(self, client: AsyncClient, test_doctor_user, finalized_medical_record):
        """Test cannot review a finalized record."""
        user, _ = test_doctor_user
        token = create_access_token({"sub": str(user.user_id), "role": user.role.value})
        
        response = await client.post(
            f"/api/v1/approval/medical-records/{finalized_medical_record.record_id}/review",
            headers={"Authorization": f"Bearer {token}"},
            json={"action": "approve"},
        )
        
        assert response.status_code in [400, 422]
        error_data = response.json()
        # Handle standard error envelope format
        error_message = error_data.get("error", {}).get("message", "") or error_data.get("detail", "")
        assert "Cannot review record with status" in str(error_message)

    @pytest.mark.asyncio
    async def test_review_invalid_action(self, client: AsyncClient, test_doctor_user, draft_medical_record):
        """Test invalid action is rejected."""
        user, _ = test_doctor_user
        token = create_access_token({"sub": str(user.user_id), "role": user.role.value})
        
        response = await client.post(
            f"/api/v1/approval/medical-records/{draft_medical_record.record_id}/review",
            headers={"Authorization": f"Bearer {token}"},
            json={"action": "invalid_action"},
        )
        
        assert response.status_code in [400, 422]


class TestPrescriptionReview:
    """Tests for prescription review."""

    @pytest.mark.asyncio
    async def test_approve_prescription(self, client: AsyncClient, test_doctor_user, draft_prescription):
        """Test doctor can approve a draft prescription."""
        user, doctor = test_doctor_user
        token = create_access_token({"sub": str(user.user_id), "role": user.role.value})
        
        response = await client.post(
            f"/api/v1/approval/prescriptions/{draft_prescription.prescription_id}/review",
            headers={"Authorization": f"Bearer {token}"},
            json={"action": "approve", "reviewer_notes": "Appropriate medications"},
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["action"] == "approve"
        assert data["status"] == "FINALIZED"
        assert data["message"] == "Prescription approved and finalized"

    @pytest.mark.asyncio
    async def test_reject_prescription(self, client: AsyncClient, test_doctor_user, draft_prescription):
        """Test doctor can reject a draft prescription."""
        user, doctor = test_doctor_user
        token = create_access_token({"sub": str(user.user_id), "role": user.role.value})
        
        response = await client.post(
            f"/api/v1/approval/prescriptions/{draft_prescription.prescription_id}/review",
            headers={"Authorization": f"Bearer {token}"},
            json={"action": "reject", "reviewer_notes": "Wrong dosage"},
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["action"] == "reject"
        assert data["status"] == "CANCELLED"
        assert data["message"] == "Prescription rejected"

    @pytest.mark.asyncio
    async def test_request_changes_prescription(self, client: AsyncClient, test_doctor_user, draft_prescription):
        """Test doctor can request changes on a draft prescription."""
        user, doctor = test_doctor_user
        token = create_access_token({"sub": str(user.user_id), "role": user.role.value})
        
        response = await client.post(
            f"/api/v1/approval/prescriptions/{draft_prescription.prescription_id}/review",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "action": "request_changes",
                "reviewer_notes": "Change metoprolol dose",
                "edited_medications": [
                    {"name": "Aspirin", "dosage": "81mg", "frequency": "once daily", "duration": "30 days"},
                    {"name": "Metoprolol", "dosage": "25mg", "frequency": "twice daily", "duration": "30 days"},
                ]
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["action"] == "request_changes"
        assert data["status"] == "DRAFT"  # Stays draft
        assert data["message"] == "Changes requested on prescription"

    @pytest.mark.asyncio
    async def test_review_prescription_other_doctor_forbidden(self, client: AsyncClient, test_doctor_user2, draft_prescription):
        """Test doctor cannot review another doctor's prescription."""
        user, _ = test_doctor_user2
        token = create_access_token({"sub": str(user.user_id), "role": user.role.value})
        
        response = await client.post(
            f"/api/v1/approval/prescriptions/{draft_prescription.prescription_id}/review",
            headers={"Authorization": f"Bearer {token}"},
            json={"action": "approve"},
        )
        
        assert response.status_code == 403


class TestGetForReview:
    """Tests for getting records/prescriptions for review."""

    @pytest.mark.asyncio
    async def test_get_medical_record_for_review(self, client: AsyncClient, test_doctor_user, draft_medical_record):
        """Test doctor can get medical record for review."""
        user, _ = test_doctor_user
        token = create_access_token({"sub": str(user.user_id), "role": user.role.value})
        
        response = await client.get(
            f"/api/v1/approval/medical-records/{draft_medical_record.record_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["record_id"] == str(draft_medical_record.record_id)
        assert data["status"] == "DRAFT"

    @pytest.mark.asyncio
    async def test_get_prescription_for_review(self, client: AsyncClient, test_doctor_user, draft_prescription):
        """Test doctor can get prescription for review."""
        user, _ = test_doctor_user
        token = create_access_token({"sub": str(user.user_id), "role": user.role.value})
        
        response = await client.get(
            f"/api/v1/approval/prescriptions/{draft_prescription.prescription_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["prescription_id"] == str(draft_prescription.prescription_id)
        assert data["status"] == "DRAFT"


class TestApprovalGateEnforcement:
    """Tests proving the mandatory human-in-the-loop gate."""

    @pytest.mark.asyncio
    async def test_draft_cannot_be_finalized_without_approval(self, client: AsyncClient, test_doctor_user, draft_medical_record):
        """Test that a draft cannot become finalized without explicit approval call."""
        user, _ = test_doctor_user
        token = create_access_token({"sub": str(user.user_id), "role": user.role.value})
        
        # Try to update status directly via medical records API (should fail)
        response = await client.put(
            f"/api/v1/medical-records/{draft_medical_record.record_id}/",
            headers={"Authorization": f"Bearer {token}"},
            json={"status": "FINALIZED"},
        )
        
        # Should be forbidden or method not allowed - doctors cannot finalize directly
        assert response.status_code in [403, 405, 422]
        if response.status_code == 403:
            error_data = response.json()
            error_message = error_data.get("error", {}).get("message", "") or error_data.get("detail", "")
            assert "cannot finalize records directly" in str(error_message)

    @pytest.mark.asyncio
    async def test_prescription_draft_cannot_be_finalized_without_approval(self, client: AsyncClient, test_doctor_user, draft_prescription):
        """Test that a draft prescription cannot become finalized without explicit approval call."""
        user, _ = test_doctor_user
        token = create_access_token({"sub": str(user.user_id), "role": user.role.value})
        
        # Try to update status directly via prescriptions API (should fail)
        response = await client.put(
            f"/api/v1/prescriptions/{draft_prescription.prescription_id}/",
            headers={"Authorization": f"Bearer {token}"},
            json={"status": "FINALIZED"},
        )
        
        # Should be forbidden - doctors cannot finalize directly
        assert response.status_code in [403, 405, 422]
        
        # Should be forbidden - doctors cannot finalize directly
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_approval_required_for_finalization(self, client: AsyncClient, test_doctor_user, draft_medical_record):
        """Test that approval endpoint is the ONLY way to finalize."""
        user, _ = test_doctor_user
        token = create_access_token({"sub": str(user.user_id), "role": user.role.value})
        
        # Verify initial status is DRAFT
        response = await client.get(
            f"/api/v1/medical-records/{draft_medical_record.record_id}/",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        assert response.json()["status"] == "DRAFT"
        
        # Approve via approval endpoint
        response = await client.post(
            f"/api/v1/approval/medical-records/{draft_medical_record.record_id}/review",
            headers={"Authorization": f"Bearer {token}"},
            json={"action": "approve"},
        )
        assert response.status_code == 200
        assert response.json()["status"] == "FINALIZED"
        
        # Verify status is now FINALIZED
        response = await client.get(
            f"/api/v1/medical-records/{draft_medical_record.record_id}/",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        assert response.json()["status"] == "FINALIZED"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])