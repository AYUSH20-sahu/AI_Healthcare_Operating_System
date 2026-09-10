"""Milestone U-09 Tests: Ambient Scribe End-to-End.

Explicitly tests:
1. Scribe agent executes in memory without direct database writes.
2. Scribe agent gracefully handles malformed LLM responses.
3. Core API creates and persists draft MedicalRecord with status = DRAFT.
4. Draft status cannot be bypassed.
5. Confidence and clinical basis are returned and persisted.
6. RBAC enforcement (patient/unauthorized blocked).
7. Reload/Recovery endpoint retrieves appointment draft record.
"""

from datetime import datetime
from unittest.mock import AsyncMock, patch
from uuid import uuid4
import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Appointment,
    AppointmentStatus,
    Doctor,
    MedicalRecord,
    MedicalRecordStatus,
    Patient,
    User,
    UserRole,
    VoiceNote,
)
from app.services.auth.service import create_access_token, get_password_hash
from app.services.providers import FallbackLLMProvider, MockLLMProvider
from app.services.scribe.scribe_agent import ScribeAgent


@pytest_asyncio.fixture
async def doctor_user(db_session: AsyncSession):
    """Create test doctor user and profile."""
    user = User(
        email="doctor_u09@test.com",
        hashed_password=get_password_hash("doctorpassword123"),
        full_name="Dr. Rajesh Sharma",
        role=UserRole.DOCTOR,
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()

    doctor = Doctor(
        user_id=user.user_id,
        license_number="DOC-U09-9988",
        specialty="Cardiology",
        full_name="Dr. Rajesh Sharma",
        email="doctor_u09@test.com",
    )
    db_session.add(doctor)
    await db_session.commit()
    await db_session.refresh(user)
    return user, doctor


@pytest_asyncio.fixture
async def patient_user(db_session: AsyncSession):
    """Create test patient user and profile."""
    user = User(
        email="patient_u09@test.com",
        hashed_password=get_password_hash("patientpassword123"),
        full_name="Amit Kumar",
        role=UserRole.PATIENT,
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()

    patient = Patient(
        user_id=user.user_id,
        full_name="Amit Kumar",
        date_of_birth=datetime(1985, 5, 20).date(),
        gender="male",
        phone="+91-9876543210",
        email="patient_u09@test.com",
    )
    db_session.add(patient)
    await db_session.commit()
    await db_session.refresh(user)
    return user, patient


@pytest_asyncio.fixture
async def consultation_setup(
    db_session: AsyncSession,
    doctor_user: tuple[User, Doctor],
    patient_user: tuple[User, Patient],
):
    """Create test appointment and voice note."""
    doc_user, doctor = doctor_user
    pat_user, patient = patient_user

    appointment = Appointment(
        patient_id=patient.patient_id,
        doctor_id=doctor.doctor_id,
        scheduled_at=datetime.utcnow(),
        duration_minutes=30,
        status=AppointmentStatus.SCHEDULED,
        notes="Exertional chest pain consultation",
    )
    db_session.add(appointment)
    await db_session.flush()

    voice_note = VoiceNote(
        appointment_id=appointment.appointment_id,
        doctor_id=doctor.doctor_id,
        patient_id=patient.patient_id,
        file_path="/tmp/test_consultation.webm",
        file_name="consultation.webm",
        content_type="audio/webm",
        file_size=1024,
        transcription="Good morning. Patient has 2-day history of exertional retrosternal tightness relieved by rest. BP is 138/88 mmHg. Allergies include Penicillin. Prescribing Sorbitrate and Atorvastatin.",
        transcription_status="pending",
    )
    db_session.add(voice_note)
    await db_session.commit()
    await db_session.refresh(appointment)
    await db_session.refresh(voice_note)
    return doc_user, doctor, patient, appointment, voice_note


@pytest.mark.asyncio
async def test_scribe_agent_in_memory_execution():
    """Test 1: Scribe agent operates purely in memory, produces structured note with confidence and basis."""
    primary_mock = MockLLMProvider("nvidia")
    agent = ScribeAgent()

    with patch("app.services.scribe.scribe_agent.get_llm_provider", return_value=primary_mock):
        result = await agent.execute({
            "transcription": "Doctor consultation: Patient presents with exertional chest pain.",
            "patient_name": "Amit Kumar",
            "vitals": {"bp": "138/88", "hr": 94},
            "allergies": ["Penicillin"],
        })

        assert result.success is True
        assert result.confidence >= 80
        assert result.basis != ""
        assert result.draft.subjective["chief_complaint"] != ""
        assert result.draft.assessment["primary_diagnosis"] != ""
        assert "medications" in result.draft.plan
        assert result.ai_metadata["provider"] == "nvidia"


@pytest.mark.asyncio
async def test_scribe_agent_malformed_json_resilience():
    """Test 2: Malformed LLM response is handled gracefully with deterministic fallback."""
    corrupted_mock = MockLLMProvider("nvidia")
    # Simulate LLM returning non-JSON garbage
    corrupted_mock.generate = AsyncMock(return_value=AsyncMock(
        content="Non-JSON raw conversational text from corrupted model stream...",
        model="corrupted-model",
        provider="nvidia",
        fallback_used=False,
        latency_ms=250.0,
        usage=None,
    ))

    agent = ScribeAgent()
    with patch("app.services.scribe.scribe_agent.get_llm_provider", return_value=corrupted_mock):
        result = await agent.execute({
            "transcription": "Patient reports chest pain.",
            "patient_name": "Amit Kumar",
        })

        assert result.success is True
        assert result.draft is not None
        assert result.confidence > 0
        assert result.basis != ""
        assert "Angina" in result.draft.assessment["primary_diagnosis"]


@pytest.mark.asyncio
async def test_core_api_creates_draft_medical_record(
    client: AsyncClient,
    consultation_setup,
    db_session: AsyncSession,
):
    """Test 3: Voice note -> Scribe -> Core API persists MedicalRecord with status == DRAFT."""
    doc_user, doctor, patient, appointment, voice_note = consultation_setup
    token = create_access_token(data={"sub": str(doc_user.user_id)})

    primary_mock = MockLLMProvider("nvidia")
    fallback_mock = MockLLMProvider("gemini")
    resilient_provider = FallbackLLMProvider(primary=primary_mock, fallback=fallback_mock)

    with patch("app.services.scribe.scribe_agent.get_llm_provider", return_value=resilient_provider):
        response = await client.post(
            f"/api/v1/voice-notes/{voice_note.voice_note_id}/scribe",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "patient_id": str(patient.patient_id),
                "appointment_id": str(appointment.appointment_id),
                "patient_name": patient.full_name,
                "vitals": {"bp": "138/88", "hr": 94},
                "allergies": ["Penicillin"],
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["success"] is True
        assert data["status"] == "draft"
        assert data["confidence"] >= 80
        assert data["basis"] != ""
        assert data["medical_record_id"] is not None

        # Verify database record status
        record = await db_session.get(MedicalRecord, data["medical_record_id"])
        assert record is not None
        assert record.status == MedicalRecordStatus.DRAFT
        assert record.appointment_id == appointment.appointment_id
        assert record.patient_id == patient.patient_id
        assert record.doctor_id == doctor.doctor_id
        assert record.content["ai_confidence"] >= 80
        assert record.content["clinical_basis"] != ""


@pytest.mark.asyncio
async def test_draft_status_cannot_be_bypassed(
    client: AsyncClient,
    consultation_setup,
    db_session: AsyncSession,
):
    """Test 4: Draft status is strictly enforced; record cannot be finalized upon creation."""
    doc_user, doctor, patient, appointment, voice_note = consultation_setup
    token = create_access_token(data={"sub": str(doc_user.user_id)})

    primary_mock = MockLLMProvider("nvidia")

    with patch("app.services.scribe.scribe_agent.get_llm_provider", return_value=primary_mock):
        response = await client.post(
            f"/api/v1/voice-notes/{voice_note.voice_note_id}/scribe",
            headers={"Authorization": f"Bearer {token}"},
            json={"patient_id": str(patient.patient_id)},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "draft"

        record = await db_session.get(MedicalRecord, data["medical_record_id"])
        assert record.status == MedicalRecordStatus.DRAFT
        assert record.finalized_at is None


@pytest.mark.asyncio
async def test_scribe_rbac_enforcement(
    client: AsyncClient,
    consultation_setup,
    patient_user: tuple[User, Patient],
):
    """Test 5: Patients and unauthenticated requests are forbidden from executing scribe pipeline."""
    pat_user, _ = patient_user
    _, _, _, _, voice_note = consultation_setup
    patient_token = create_access_token(data={"sub": str(pat_user.user_id)})

    # Patient attempted scribe
    response = await client.post(
        f"/api/v1/voice-notes/{voice_note.voice_note_id}/scribe",
        headers={"Authorization": f"Bearer {patient_token}"},
        json={},
    )
    assert response.status_code == 403

    # Unauthenticated
    unauth_res = await client.post(
        f"/api/v1/voice-notes/{voice_note.voice_note_id}/scribe",
        json={},
    )
    assert unauth_res.status_code == 401


@pytest.mark.asyncio
async def test_appointment_draft_recovery_endpoint(
    client: AsyncClient,
    consultation_setup,
    db_session: AsyncSession,
):
    """Test 6: Reload recovery endpoint returns existing appointment draft record."""
    doc_user, doctor, patient, appointment, _ = consultation_setup
    token = create_access_token(data={"sub": str(doc_user.user_id)})

    # Insert existing draft medical record
    existing_record = MedicalRecord(
        patient_id=patient.patient_id,
        doctor_id=doctor.doctor_id,
        appointment_id=appointment.appointment_id,
        content={
            "subjective": {"chief_complaint": "Recovered chest pain note"},
            "objective": {"vitals_reviewed": "BP 138/88"},
            "assessment": {"primary_diagnosis": "Exertional Angina"},
            "plan": {"medications": []},
            "ai_confidence": 94,
            "clinical_basis": "Recovered from prior session",
        },
        status=MedicalRecordStatus.DRAFT,
    )
    db_session.add(existing_record)
    await db_session.commit()

    # Query recovery endpoint
    response = await client.get(
        f"/api/v1/medical-records/appointment/{appointment.appointment_id}/draft",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data is not None
    assert data["record_id"] == str(existing_record.record_id)
    assert data["status"] == "DRAFT"
    assert data["content"]["ai_confidence"] == 94
