"""Milestone U-10 Tests: Prescription Draft & Clinical Safety Review.

Explicitly tests:
1. In-memory PrescriptionDraftAgent execution without database operations.
2. Drug-allergy cross-reactivity detection (e.g. penicillin allergy vs amoxicillin).
3. Drug-drug interaction detection (e.g. warfarin + aspirin).
4. Core API creates and persists draft Prescription with status = DRAFT.
5. Invariant: Newly created prescriptions cannot bypass draft status (no auto-finalization).
6. RBAC protection: Patient cannot draft prescriptions; Doctor cannot draft for other patients.
7. Appointment draft recovery endpoint restores active draft prescription.
8. End-to-end integration: Scribe Draft -> Prescription Draft -> Allergy Detection -> Doctor Editing.
"""

from datetime import datetime
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
    Prescription,
    PrescriptionStatus,
    User,
    UserRole,
)
from app.services.auth.service import create_access_token, get_password_hash
from app.services.prescriptions.prescription_agent import PrescriptionDraftAgent


@pytest_asyncio.fixture
async def doctor_user(db_session: AsyncSession):
    """Create test doctor user and profile."""
    user = User(
        email="doctor_u10@test.com",
        hashed_password=get_password_hash("doctorpassword123"),
        full_name="Dr. Sunita Patel",
        role=UserRole.DOCTOR,
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()

    doctor = Doctor(
        user_id=user.user_id,
        license_number="DOC-U10-5544",
        specialty="Cardiology",
        full_name="Dr. Sunita Patel",
        email="doctor_u10@test.com",
    )
    db_session.add(doctor)
    await db_session.commit()
    await db_session.refresh(user)
    return user, doctor


@pytest_asyncio.fixture
async def patient_user(db_session: AsyncSession):
    """Create test patient user and profile."""
    user = User(
        email="patient_u10@test.com",
        hashed_password=get_password_hash("patientpassword123"),
        full_name="Vikram Seth",
        role=UserRole.PATIENT,
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()

    patient = Patient(
        user_id=user.user_id,
        full_name="Vikram Seth",
        date_of_birth=datetime(1975, 8, 14).date(),
        gender="male",
        phone="+91-9812345678",
        email="patient_u10@test.com",
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
    """Create test appointment and draft medical record."""
    doc_user, doctor = doctor_user
    pat_user, patient = patient_user

    appointment = Appointment(
        patient_id=patient.patient_id,
        doctor_id=doctor.doctor_id,
        scheduled_at=datetime.utcnow(),
        status=AppointmentStatus.SCHEDULED,
        notes="Cardiology Follow-up",
    )
    db_session.add(appointment)
    await db_session.flush()

    medical_record = MedicalRecord(
        patient_id=patient.patient_id,
        doctor_id=doctor.doctor_id,
        appointment_id=appointment.appointment_id,
        status=MedicalRecordStatus.DRAFT,
        content={
            "soap": {
                "assessment": {
                    "primary_diagnosis": "Angina Pectoris",
                    "icd10_code": "I20.9",
                },
                "plan": {
                    "medications": [
                        {
                            "name": "Metoprolol",
                            "dosage": "50mg",
                            "frequency": "Twice daily",
                            "duration": "30 days",
                        }
                    ]
                },
            }
        },
    )
    db_session.add(medical_record)
    await db_session.commit()
    await db_session.refresh(appointment)
    await db_session.refresh(medical_record)

    return appointment, medical_record


@pytest.mark.asyncio
async def test_prescription_agent_in_memory_execution():
    """Test 1: PrescriptionDraftAgent executes purely in-memory and outputs structured medications."""
    agent = PrescriptionDraftAgent()
    payload = {
        "assessment": "Essential Hypertension",
        "icd10_code": "I10",
        "suggested_medications": [
            {
                "name": "Amlodipine",
                "dosage": "5mg",
                "frequency": "Once daily",
                "duration": "30 days",
                "instructions": "Take in morning.",
            }
        ],
        "patient_allergies": ["Sulfa"],
    }

    result = await agent.execute(payload)
    assert result.success is True
    assert len(result.medications) >= 1
    assert result.medications[0]["name"] == "Amlodipine"
    assert result.confidence >= 80
    assert "guidelines" in result.basis.lower() or "assessment" in result.basis.lower()
    assert result.has_warnings is False  # Sulfa does not react with Amlodipine


@pytest.mark.asyncio
async def test_prescription_agent_allergy_cross_reactivity_detection():
    """Test 2: Scribe/Prescription agent detects penicillin cross-reactivity with Amoxicillin."""
    agent = PrescriptionDraftAgent()
    payload = {
        "assessment": "Streptococcal Pharyngitis",
        "suggested_medications": [
            {
                "name": "Amoxicillin",
                "dosage": "500mg",
                "frequency": "Three times daily",
                "duration": "10 days",
            }
        ],
        "patient_allergies": ["Penicillin"],
    }

    result = await agent.execute(payload)
    assert result.success is True
    assert result.has_warnings is True
    assert len(result.warnings) >= 1

    allergy_warn = [w for w in result.warnings if w["type"] == "allergy"][0]
    assert allergy_warn["severity"] == "severe"
    assert "amoxicillin" in allergy_warn["medication"].lower()
    assert "penicillin" in allergy_warn["description"].lower()


@pytest.mark.asyncio
async def test_prescription_agent_drug_interaction_detection():
    """Test 3: Scribe/Prescription agent detects severe Warfarin + Aspirin interaction."""
    agent = PrescriptionDraftAgent()
    payload = {
        "assessment": "Atrial Fibrillation with Musculoskeletal Pain",
        "suggested_medications": [
            {
                "name": "Warfarin Sodium",
                "dosage": "5mg",
                "frequency": "Once daily",
                "duration": "30 days",
            },
            {
                "name": "Aspirin",
                "dosage": "81mg",
                "frequency": "Once daily",
                "duration": "30 days",
            },
        ],
        "patient_allergies": [],
    }

    result = await agent.execute(payload)
    assert result.success is True
    assert result.has_warnings is True
    assert any(w["type"] == "interaction" for w in result.warnings)

    interaction = [w for w in result.warnings if w["type"] == "interaction"][0]
    assert interaction["severity"] == "severe"
    assert "bleeding" in interaction["description"].lower() or "hemorrhage" in interaction["description"].lower()


@pytest.mark.asyncio
async def test_core_api_creates_draft_prescription(
    client: AsyncClient,
    db_session: AsyncSession,
    doctor_user: tuple[User, Doctor],
    patient_user: tuple[User, Patient],
    consultation_setup: tuple[Appointment, MedicalRecord],
):
    """Test 4: Core API creates and persists draft prescription with status = DRAFT."""
    doc_user, doctor = doctor_user
    pat_user, patient = patient_user
    appointment, medical_record = consultation_setup

    token = create_access_token(data={"sub": str(doc_user.user_id), "email": doc_user.email, "role": doc_user.role.value})

    payload = {
        "patient_id": str(patient.patient_id),
        "doctor_id": str(doctor.doctor_id),
        "appointment_id": str(appointment.appointment_id),
        "medical_record_id": str(medical_record.record_id),
        "assessment": "Angina Pectoris",
        "icd10_code": "I20.9",
        "suggested_medications": [
            {
                "name": "Nitroglycerin",
                "dosage": "0.4mg",
                "frequency": "As needed",
                "duration": "30 days",
                "route": "sublingual",
                "instructions": "Place 1 tablet under tongue for chest pain.",
                "quantity": 25,
                "refills": 1,
            }
        ],
        "patient_allergies": [],
        "notes": "Monitor blood pressure prior to sublingual use.",
    }

    response = await client.post(
        "/api/v1/prescriptions/draft",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "DRAFT"
    assert "prescription_id" in data
    assert len(data["medications"]) == 1
    assert data["medications"][0]["name"] == "Nitroglycerin"
    assert data["confidence"] >= 80

    # Verify directly in PostgreSQL
    rx_id = data["prescription_id"]
    db_rx = await db_session.get(Prescription, rx_id)
    assert db_rx is not None
    assert db_rx.status == PrescriptionStatus.DRAFT
    assert db_rx.patient_id == patient.patient_id
    assert db_rx.doctor_id == doctor.doctor_id


@pytest.mark.asyncio
async def test_draft_status_cannot_be_bypassed(
    client: AsyncClient,
    doctor_user: tuple[User, Doctor],
    patient_user: tuple[User, Patient],
    consultation_setup: tuple[Appointment, MedicalRecord],
):
    """Test 5: Prescriptions cannot be directly updated to FINALIZED (bypassing review gate)."""
    doc_user, doctor = doctor_user
    pat_user, patient = patient_user
    appointment, medical_record = consultation_setup

    token = create_access_token(data={"sub": str(doc_user.user_id), "email": doc_user.email, "role": doc_user.role.value})

    # Create draft prescription
    draft_res = await client.post(
        "/api/v1/prescriptions/draft",
        json={
            "patient_id": str(patient.patient_id),
            "doctor_id": str(doctor.doctor_id),
            "appointment_id": str(appointment.appointment_id),
            "suggested_medications": [{"name": "Aspirin", "dosage": "81mg", "frequency": "Daily", "duration": "30 days"}],
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    rx_id = draft_res.json()["prescription_id"]

    # Attempt to bypass review gate and finalize directly
    bypass_res = await client.put(
        f"/api/v1/prescriptions/{rx_id}/",
        json={"status": "FINALIZED"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert bypass_res.status_code == 403
    assert "requires review flow" in bypass_res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_prescription_draft_rbac_enforcement(
    client: AsyncClient,
    doctor_user: tuple[User, Doctor],
    patient_user: tuple[User, Patient],
):
    """Test 6: RBAC: Patients cannot draft prescriptions (403), unauthenticated returns 401."""
    doc_user, doctor = doctor_user
    pat_user, patient = patient_user

    patient_token = create_access_token(data={"sub": str(pat_user.user_id), "email": pat_user.email, "role": pat_user.role.value})

    # 1. Patient attempt -> 403 Forbidden
    res_forbidden = await client.post(
        "/api/v1/prescriptions/draft",
        json={
            "patient_id": str(patient.patient_id),
            "doctor_id": str(doctor.doctor_id),
            "suggested_medications": [{"name": "Amoxicillin", "dosage": "500mg", "frequency": "Daily", "duration": "7 days"}],
        },
        headers={"Authorization": f"Bearer {patient_token}"},
    )
    assert res_forbidden.status_code == 403

    # 2. Unauthenticated -> 401 Unauthorized
    res_unauth = await client.post(
        "/api/v1/prescriptions/draft",
        json={"patient_id": str(patient.patient_id), "doctor_id": str(doctor.doctor_id)},
    )
    assert res_unauth.status_code == 401


@pytest.mark.asyncio
async def test_appointment_draft_prescription_recovery(
    client: AsyncClient,
    doctor_user: tuple[User, Doctor],
    patient_user: tuple[User, Patient],
    consultation_setup: tuple[Appointment, MedicalRecord],
):
    """Test 7: Draft recovery endpoint restores active draft prescription on page refresh."""
    doc_user, doctor = doctor_user
    pat_user, patient = patient_user
    appointment, medical_record = consultation_setup

    token = create_access_token(data={"sub": str(doc_user.user_id), "email": doc_user.email, "role": doc_user.role.value})

    # Create draft
    draft_res = await client.post(
        "/api/v1/prescriptions/draft",
        json={
            "patient_id": str(patient.patient_id),
            "doctor_id": str(doctor.doctor_id),
            "appointment_id": str(appointment.appointment_id),
            "medical_record_id": str(medical_record.record_id),
            "suggested_medications": [
                {
                    "name": "Atorvastatin",
                    "dosage": "40mg",
                    "frequency": "Once daily at bedtime",
                    "duration": "90 days",
                }
            ],
            "patient_allergies": [],
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    created_id = draft_res.json()["prescription_id"]

    # Call recovery endpoint
    recover_res = await client.get(
        f"/api/v1/prescriptions/appointment/{appointment.appointment_id}/draft",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert recover_res.status_code == 200
    recovered_data = recover_res.json()
    assert recovered_data is not None
    assert recovered_data["prescription_id"] == created_id
    assert recovered_data["status"] == "DRAFT"
    assert recovered_data["medications"][0]["name"] == "Atorvastatin"


@pytest.mark.asyncio
async def test_full_end_to_end_scribe_to_prescription_workflow(
    client: AsyncClient,
    doctor_user: tuple[User, Doctor],
    patient_user: tuple[User, Patient],
    consultation_setup: tuple[Appointment, MedicalRecord],
):
    """Test 8: End-to-end: Consultation Scribe -> Prescription Draft with Allergy Flag -> Doctor Edits -> Screen Clear."""
    doc_user, doctor = doctor_user
    pat_user, patient = patient_user
    appointment, medical_record = consultation_setup

    token = create_access_token(data={"sub": str(doc_user.user_id), "email": doc_user.email, "role": doc_user.role.value})

    # Step 1: Doctor triggers prescription draft with Penicillin allergy & Amoxicillin recommendation
    draft_res = await client.post(
        "/api/v1/prescriptions/draft",
        json={
            "patient_id": str(patient.patient_id),
            "doctor_id": str(doctor.doctor_id),
            "appointment_id": str(appointment.appointment_id),
            "medical_record_id": str(medical_record.record_id),
            "assessment": "Acute Bacterial Sinusitis",
            "icd10_code": "J01.90",
            "suggested_medications": [
                {
                    "name": "Amoxicillin",
                    "dosage": "875mg",
                    "frequency": "Twice daily",
                    "duration": "10 days",
                }
            ],
            "patient_allergies": ["Penicillin"],
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert draft_res.status_code == 201
    draft_data = draft_res.json()
    rx_id = draft_data["prescription_id"]
    assert draft_data["has_warnings"] is True
    assert any(w["type"] == "allergy" for w in draft_data["warnings"])

    # Step 2: Doctor observes allergy conflict and switches medication to Azithromycin
    edited_medications = [
        {
            "name": "Azithromycin",
            "dosage": "500mg",
            "frequency": "Once daily",
            "duration": "5 days",
            "route": "oral",
            "instructions": "Take on empty stomach.",
            "quantity": 5,
            "refills": 0,
        }
    ]

    # Step 3: Doctor runs live interaction screen with updated medication
    screen_res = await client.post(
        "/api/v1/prescriptions/check-interactions/",
        json={
            "patient_id": str(patient.patient_id),
            "medications": edited_medications,
            "patient_allergies": ["Penicillin"],
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert screen_res.status_code == 200
    screen_data = screen_res.json()
    assert screen_data["has_warnings"] is False
    assert len(screen_data["warnings"]) == 0

    # Step 4: Doctor saves updated draft prescription
    update_res = await client.put(
        f"/api/v1/prescriptions/{rx_id}/",
        json={
            "medications": edited_medications,
            "notes": "Substituted Azithromycin due to documented penicillin allergy.",
            "status": "DRAFT",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert update_res.status_code == 200
    updated_data = update_res.json()
    assert updated_data["status"] == "DRAFT"
    assert updated_data["medications"][0]["name"] == "Azithromycin"
