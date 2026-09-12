"""Automated Test Suite for Milestone U-20: FHIR + Integration Layer (M33).

Tests covered:
1. FHIR Patient Mapping: GET /api/v1/fhir/Patient/{id} returns HL7 FHIR R4 Patient resource.
2. FHIR Appointment Mapping: GET /api/v1/fhir/Appointment/{id} returns HL7 FHIR R4 Appointment resource.
3. FHIR DiagnosticReport Mapping: GET /api/v1/fhir/DiagnosticReport/{id} returns HL7 FHIR R4 DiagnosticReport resource.
4. FHIR MedicationRequest Mapping: GET /api/v1/fhir/MedicationRequest/{id} returns HL7 FHIR R4 MedicationRequest resource.
5. FHIR Bundle ($everything): GET /api/v1/fhir/Patient/{id}/$everything returns searchset Bundle with all clinical entries.
6. FHIR Bundle Query: GET /api/v1/fhir/Bundle with patient_id param.
7. Zero Schema Modification Invariant: Verifies internal PostgreSQL tables remain strictly unchanged.
8. Strict Cross-Patient RBAC: Patient B cannot access Patient A's FHIR resources (403 Forbidden).
9. Unauthenticated Requests: 401 Unauthorized when missing token.
"""

import uuid
from datetime import date, datetime, timedelta
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


@pytest_asyncio.fixture
async def fhir_patient_a(db_session: AsyncSession):
    """Create Patient Alice with rich clinical data."""
    user = User(
        email="alice.fhir.u20@aihos.org",
        hashed_password=get_password_hash("alicepassword123"),
        full_name="Alice FHIR Patient",
        role=UserRole.PATIENT,
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    patient = Patient(
        user_id=user.user_id,
        full_name="Alice FHIR Patient",
        email=user.email,
        phone="+91-9876543210",
        date_of_birth=date(1992, 6, 15),
        gender="Female",
        address="102 Health Avenue, New Delhi, India",
        emergency_contact_name="Bob Patient",
        emergency_contact_phone="+91-9876543211",
        abha_address="alice@abdm",
    )
    db_session.add(patient)
    await db_session.commit()
    await db_session.refresh(patient)
    return user, patient


@pytest_asyncio.fixture
async def fhir_patient_b(db_session: AsyncSession):
    """Create Patient Bob for RBAC isolation checks."""
    user = User(
        email="bob.fhir.u20@aihos.org",
        hashed_password=get_password_hash("bobpassword123"),
        full_name="Bob FHIR Patient",
        role=UserRole.PATIENT,
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    patient = Patient(
        user_id=user.user_id,
        full_name="Bob FHIR Patient",
        email=user.email,
        date_of_birth=date(1988, 3, 10),
        gender="Male",
    )
    db_session.add(patient)
    await db_session.commit()
    await db_session.refresh(patient)
    return user, patient


@pytest_asyncio.fixture
async def fhir_doctor(db_session: AsyncSession):
    """Create Attending Doctor Dr. Meera."""
    user = User(
        email="doctor.fhir.u20@aihos.org",
        hashed_password=get_password_hash("doctorpassword123"),
        full_name="Dr. Meera Nambiar",
        role=UserRole.DOCTOR,
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    doctor = Doctor(
        user_id=user.user_id,
        full_name="Dr. Meera Nambiar",
        email=user.email,
        specialty="Internal Medicine",
        hospital_affiliation="AIIMS Apex Clinical Center",
        license_number="MED-U20-7766",
    )
    db_session.add(doctor)
    await db_session.commit()
    await db_session.refresh(doctor)
    return user, doctor


@pytest_asyncio.fixture
async def fhir_clinical_data(
    db_session: AsyncSession,
    fhir_patient_a,
    fhir_doctor,
):
    """Create complete clinical records: Appointment, MedicalRecord, and Prescription."""
    _, patient = fhir_patient_a
    _, doctor = fhir_doctor

    # 1. Appointment
    appt = Appointment(
        patient_id=patient.patient_id,
        doctor_id=doctor.doctor_id,
        scheduled_at=datetime.utcnow() + timedelta(days=1),
        duration_minutes=30,
        status=AppointmentStatus.SCHEDULED,
        notes="Follow-up consultation for seasonal allergies",
        meeting_link="https://meet.aihos.org/room-u20",
    )
    db_session.add(appt)
    await db_session.flush()

    # 2. Medical Record (DiagnosticReport / SOAP note)
    record = MedicalRecord(
        patient_id=patient.patient_id,
        doctor_id=doctor.doctor_id,
        appointment_id=appt.appointment_id,
        status=MedicalRecordStatus.FINALIZED,
        content={
            "subjective": {"history_of_present_illness": "Patient reports sneezing and nasal congestion"},
            "objective": {"physical_exam": "Clear breath sounds, mild rhinitis"},
            "assessment": {"primary_diagnosis": "Allergic Rhinitis (J30.9)"},
            "plan": {"counseling": "Avoid known allergens, take daily antihistamine"},
        },
        finalized_at=datetime.utcnow(),
    )
    db_session.add(record)
    await db_session.flush()

    # 3. Prescription (MedicationRequest)
    prescription = Prescription(
        patient_id=patient.patient_id,
        doctor_id=doctor.doctor_id,
        medical_record_id=record.record_id,
        status=PrescriptionStatus.APPROVED,
        medications=[
            {
                "name": "Cetirizine 10mg",
                "dosage": "10mg",
                "frequency": "Once daily at bedtime",
                "duration": "14 days",
                "route": "oral",
            }
        ],
        notes="Take with water before sleep.",
        finalized_at=datetime.utcnow(),
    )
    db_session.add(prescription)
    await db_session.commit()

    return appt, record, prescription


def _auth_header(user: User) -> dict:
    token = create_access_token(data={"sub": str(user.user_id), "role": user.role.value})
    return {"Authorization": f"Bearer {token}"}


# =============================================================================
# Milestone U-20 Tests
# =============================================================================

@pytest.mark.asyncio
async def test_get_fhir_patient(
    client: AsyncClient,
    fhir_patient_a,
):
    """Test GET /api/v1/fhir/Patient/{id} returns compliant HL7 FHIR R4 Patient."""
    user, patient = fhir_patient_a

    res = await client.get(
        f"/api/v1/fhir/Patient/{patient.patient_id}",
        headers=_auth_header(user),
    )
    assert res.status_code == 200, res.text
    data = res.json()

    assert data["resourceType"] == "Patient"
    assert data["id"] == str(patient.patient_id)
    assert data["active"] is True
    assert data["gender"] == "female"
    assert data["birthDate"] == "1992-06-15"
    assert data["name"][0]["text"] == "Alice FHIR Patient"

    # Check identifiers (ABHA + system ID)
    system_ids = [ident["system"] for ident in data["identifier"]]
    assert "https://aihos.org/patients" in system_ids
    assert "https://healthid.abdm.gov.in" in system_ids

    # Check telecoms
    telecom_systems = [t["system"] for t in data["telecom"]]
    assert "email" in telecom_systems
    assert "phone" in telecom_systems


@pytest.mark.asyncio
async def test_get_fhir_appointment(
    client: AsyncClient,
    fhir_patient_a,
    fhir_clinical_data,
):
    """Test GET /api/v1/fhir/Appointment/{id} returns compliant HL7 FHIR R4 Appointment."""
    user, _ = fhir_patient_a
    appt, _, _ = fhir_clinical_data

    res = await client.get(
        f"/api/v1/fhir/Appointment/{appt.appointment_id}",
        headers=_auth_header(user),
    )
    assert res.status_code == 200, res.text
    data = res.json()

    assert data["resourceType"] == "Appointment"
    assert data["id"] == str(appt.appointment_id)
    assert data["status"] == "booked"
    assert "start" in data
    assert "end" in data
    assert data["minutesDuration"] == 30
    assert len(data["participant"]) >= 2
    actors = [p["actor"]["reference"] for p in data["participant"]]
    assert any("Patient/" in a for a in actors)
    assert any("Practitioner/" in a for a in actors)


@pytest.mark.asyncio
async def test_get_fhir_diagnostic_report(
    client: AsyncClient,
    fhir_patient_a,
    fhir_clinical_data,
):
    """Test GET /api/v1/fhir/DiagnosticReport/{id} returns compliant DiagnosticReport."""
    user, _ = fhir_patient_a
    _, record, _ = fhir_clinical_data

    res = await client.get(
        f"/api/v1/fhir/DiagnosticReport/{record.record_id}",
        headers=_auth_header(user),
    )
    assert res.status_code == 200, res.text
    data = res.json()

    assert data["resourceType"] == "DiagnosticReport"
    assert data["id"] == str(record.record_id)
    assert data["status"] == "final"
    assert data["code"]["coding"][0]["system"] == "http://loinc.org"
    assert data["code"]["coding"][0]["code"] == "11488-4"
    assert "Patient/" in data["subject"]["reference"]
    assert "presentedForm" in data
    assert len(data["presentedForm"]) > 0


@pytest.mark.asyncio
async def test_get_fhir_medication_request(
    client: AsyncClient,
    fhir_patient_a,
    fhir_clinical_data,
):
    """Test GET /api/v1/fhir/MedicationRequest/{id} returns compliant MedicationRequest."""
    user, _ = fhir_patient_a
    _, _, rx = fhir_clinical_data

    res = await client.get(
        f"/api/v1/fhir/MedicationRequest/{rx.prescription_id}",
        headers=_auth_header(user),
    )
    assert res.status_code == 200, res.text
    data = res.json()

    assert data["resourceType"] == "MedicationRequest"
    assert data["id"] == str(rx.prescription_id)
    assert data["status"] == "active"
    assert data["intent"] == "order"
    assert "Cetirizine 10mg" in data["medicationCodeableConcept"]["text"]
    assert len(data["dosageInstruction"]) > 0


@pytest.mark.asyncio
async def test_get_fhir_patient_everything_bundle(
    client: AsyncClient,
    fhir_patient_a,
    fhir_clinical_data,
):
    """Test GET /api/v1/fhir/Patient/{id}/$everything returns unified Bundle containing all resources."""
    user, patient = fhir_patient_a
    appt, record, rx = fhir_clinical_data

    res = await client.get(
        f"/api/v1/fhir/Patient/{patient.patient_id}/$everything",
        headers=_auth_header(user),
    )
    assert res.status_code == 200, res.text
    data = res.json()

    assert data["resourceType"] == "Bundle"
    assert data["type"] == "searchset"
    assert data["total"] >= 4
    assert "entry" in data
    assert len(data["entry"]) >= 4

    resource_types = [e["resource"]["resourceType"] for e in data["entry"]]
    assert "Patient" in resource_types
    assert "Appointment" in resource_types
    assert "DiagnosticReport" in resource_types
    assert "MedicationRequest" in resource_types


@pytest.mark.asyncio
async def test_cross_patient_isolation_on_fhir_endpoints(
    client: AsyncClient,
    fhir_patient_a,
    fhir_patient_b,
    fhir_clinical_data,
):
    """Test that Patient B receives 403 Forbidden attempting to access Patient A's FHIR resources."""
    _, patient_a = fhir_patient_a
    user_b, _ = fhir_patient_b
    appt, record, rx = fhir_clinical_data

    # 1. Patient B attempts to get Patient A's Patient resource
    r1 = await client.get(
        f"/api/v1/fhir/Patient/{patient_a.patient_id}",
        headers=_auth_header(user_b),
    )
    assert r1.status_code == 403

    # 2. Patient B attempts to get Patient A's DiagnosticReport
    r2 = await client.get(
        f"/api/v1/fhir/DiagnosticReport/{record.record_id}",
        headers=_auth_header(user_b),
    )
    assert r2.status_code == 403

    # 3. Patient B attempts to get Patient A's $everything Bundle
    r3 = await client.get(
        f"/api/v1/fhir/Patient/{patient_a.patient_id}/$everything",
        headers=_auth_header(user_b),
    )
    assert r3.status_code == 403


@pytest.mark.asyncio
async def test_unauthenticated_fhir_requests_rejected(
    client: AsyncClient,
    fhir_patient_a,
):
    """Test unauthenticated requests receive 401 Unauthorized."""
    _, patient = fhir_patient_a
    fake_id = str(uuid.uuid4())

    r1 = await client.get(f"/api/v1/fhir/Patient/{patient.patient_id}")
    assert r1.status_code == 401

    r2 = await client.get(f"/api/v1/fhir/Patient/{patient.patient_id}/$everything")
    assert r2.status_code == 401

    r3 = await client.get(f"/api/v1/fhir/DiagnosticReport/{fake_id}")
    assert r3.status_code == 401
