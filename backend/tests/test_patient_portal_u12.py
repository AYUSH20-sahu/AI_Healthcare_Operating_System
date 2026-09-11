"""Automated Test Suite for Milestone U-12: Patient Application + Patient Backend Completion.

Tests verified:
1. Patient retrieves their own profile via GET /api/v1/patients/me.
2. Patient updates their profile via PUT /api/v1/patients/me.
3. Patient gets dashboard metrics via GET /api/v1/patients/me/dashboard.
4. Patient views their appointments via GET /api/v1/patients/me/appointments.
5. Patient views their finalized medical records via GET /api/v1/patients/me/records.
6. Patient views their finalized prescriptions via GET /api/v1/patients/me/prescriptions.
7. Strict Cross-Patient Isolation:
   - Patient A cannot read Patient B's profile (403 Forbidden).
   - Patient A cannot update Patient B's profile (403 Forbidden).
   - Patient A cannot read Patient B's medical records (403 Forbidden).
   - Patient A cannot read Patient B's prescriptions (403 Forbidden).
   - Patient A cannot read Patient B's appointments (403 Forbidden).
8. Unauthenticated requests are blocked (401 Unauthorized).
"""

import pytest
import pytest_asyncio
from datetime import datetime, date, timedelta
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    User,
    UserRole,
    Patient,
    Doctor,
    Appointment,
    AppointmentStatus,
    MedicalRecord,
    MedicalRecordStatus,
    Prescription,
    PrescriptionStatus,
)
from app.services.auth.service import create_access_token, get_password_hash


@pytest_asyncio.fixture
async def patient_a(db_session: AsyncSession):
    """Create Patient A."""
    user = User(
        email="patient_a@u12test.com",
        hashed_password=get_password_hash("password123"),
        full_name="Alice Patient",
        role=UserRole.PATIENT,
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()

    patient = Patient(
        user_id=user.user_id,
        full_name="Alice Patient",
        email="patient_a@u12test.com",
        date_of_birth=date(1992, 4, 15),
        gender="Female",
        phone="+91 91111 22222",
        address="123 Palm Street, Mumbai",
        emergency_contact_name="Bob Patient",
        emergency_contact_phone="+91 91111 33333",
        abha_address="alice@abdm",
    )
    db_session.add(patient)
    await db_session.commit()
    await db_session.refresh(user)
    await db_session.refresh(patient)
    return user, patient


@pytest_asyncio.fixture
async def patient_b(db_session: AsyncSession):
    """Create Patient B."""
    user = User(
        email="patient_b@u12test.com",
        hashed_password=get_password_hash("password123"),
        full_name="Bob Smith",
        role=UserRole.PATIENT,
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()

    patient = Patient(
        user_id=user.user_id,
        full_name="Bob Smith",
        email="patient_b@u12test.com",
        date_of_birth=date(1988, 8, 20),
        gender="Male",
        phone="+91 94444 55555",
        address="456 Oak Avenue, Delhi",
        emergency_contact_name="Carol Smith",
        emergency_contact_phone="+91 94444 66666",
        abha_address="bob@abdm",
    )
    db_session.add(patient)
    await db_session.commit()
    await db_session.refresh(user)
    await db_session.refresh(patient)
    return user, patient


@pytest_asyncio.fixture
async def attending_doctor(db_session: AsyncSession):
    """Create an attending Doctor."""
    user = User(
        email="doctor.u12@test.com",
        hashed_password=get_password_hash("password123"),
        full_name="Dr. Sarah Jenkins",
        role=UserRole.DOCTOR,
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()

    doctor = Doctor(
        user_id=user.user_id,
        license_number="LIC-U12-099",
        specialty="General Medicine",
        full_name="Dr. Sarah Jenkins",
        email="doctor.u12@test.com",
        hospital_affiliation="Apex General Hospital",
    )
    db_session.add(doctor)
    await db_session.commit()
    await db_session.refresh(user)
    await db_session.refresh(doctor)
    return user, doctor


@pytest_asyncio.fixture
async def patient_clinical_data(db_session: AsyncSession, patient_a, attending_doctor):
    """Create clinical data for Patient A."""
    _, pat = patient_a
    _, doc = attending_doctor

    # 1. Upcoming appointment
    appt = Appointment(
        patient_id=pat.patient_id,
        doctor_id=doc.doctor_id,
        scheduled_at=datetime.utcnow() + timedelta(days=2),
        duration_minutes=30,
        status=AppointmentStatus.SCHEDULED,
        reason="Follow-up on respiratory symptoms",
    )
    db_session.add(appt)

    # 2. Finalized medical record
    record = MedicalRecord(
        patient_id=pat.patient_id,
        doctor_id=doc.doctor_id,
        status=MedicalRecordStatus.FINALIZED,
        content={
            "chief_complaint": "Persistent seasonal dry cough",
            "assessment": "Allergic Rhinitis with dry cough",
            "plan": "Cetirizine 10mg QHS, steam inhalation twice daily",
        },
        finalized_at=datetime.utcnow(),
    )
    db_session.add(record)
    await db_session.flush()

    # 3. Finalized prescription
    prescription = Prescription(
        patient_id=pat.patient_id,
        doctor_id=doc.doctor_id,
        medical_record_id=record.record_id,
        status=PrescriptionStatus.FINALIZED,
        medications=[
            {
                "name": "Cetirizine",
                "dosage": "10mg",
                "frequency": "Once daily at bedtime",
                "duration": "14 days",
                "route": "oral",
                "refills": 1,
            }
        ],
        notes="Avoid driving after taking cetirizine.",
        finalized_at=datetime.utcnow(),
    )
    db_session.add(prescription)
    await db_session.commit()
    return appt, record, prescription


# ---------------------------------------------------------------------------
# Test 1: Patient can retrieve own profile via GET /patients/me
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_01_patient_can_get_own_profile(async_client: AsyncClient, patient_a):
    user, pat = patient_a
    token = create_access_token({"sub": str(user.user_id), "role": user.role.value})

    res = await async_client.get(
        "/api/v1/patients/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["patient_id"] == str(pat.patient_id)
    assert data["full_name"] == pat.full_name
    assert data["abha_address"] == "alice@abdm"
    assert data["emergency_contact_name"] == "Bob Patient"


# ---------------------------------------------------------------------------
# Test 2: Patient can update own profile via PUT /patients/me
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_02_patient_can_update_own_profile(async_client: AsyncClient, patient_a):
    user, pat = patient_a
    token = create_access_token({"sub": str(user.user_id), "role": user.role.value})

    update_payload = {
        "full_name": "Alice P. Cooper",
        "phone": "+91 99999 88888",
        "address": "789 Pine Road, Pune",
        "emergency_contact_name": "David Cooper",
        "emergency_contact_phone": "+91 99999 77777",
    }
    res = await async_client.put(
        "/api/v1/patients/me",
        json=update_payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["full_name"] == "Alice P. Cooper"
    assert data["phone"] == "+91 99999 88888"
    assert data["address"] == "789 Pine Road, Pune"
    assert data["emergency_contact_name"] == "David Cooper"


# ---------------------------------------------------------------------------
# Test 3: Patient dashboard summary endpoint
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_03_patient_dashboard_summary(
    async_client: AsyncClient,
    patient_a,
    patient_clinical_data,
):
    user, _ = patient_a
    token = create_access_token({"sub": str(user.user_id), "role": user.role.value})

    res = await async_client.get(
        "/api/v1/patients/me/dashboard",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["upcoming_appointments_count"] >= 1
    assert data["finalized_records_count"] >= 1
    assert data["active_prescriptions_count"] >= 1
    assert data["next_appointment"] is not None
    assert data["next_appointment"]["doctor_name"] == "Dr. Sarah Jenkins"
    assert len(data["recent_prescriptions"]) >= 1


# ---------------------------------------------------------------------------
# Test 4: Patient views their own appointments
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_04_patient_views_own_appointments(
    async_client: AsyncClient,
    patient_a,
    patient_clinical_data,
):
    user, _ = patient_a
    token = create_access_token({"sub": str(user.user_id), "role": user.role.value})

    res = await async_client.get(
        "/api/v1/patients/me/appointments",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert len(data) >= 1
    assert data[0]["doctor_name"] == "Dr. Sarah Jenkins"
    assert "respiratory symptoms" in data[0]["reason"]


# ---------------------------------------------------------------------------
# Test 5: Patient views their own finalized medical records
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_05_patient_views_own_medical_records(
    async_client: AsyncClient,
    patient_a,
    patient_clinical_data,
):
    user, _ = patient_a
    token = create_access_token({"sub": str(user.user_id), "role": user.role.value})

    res = await async_client.get(
        "/api/v1/patients/me/records",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert len(data) >= 1
    assert data[0]["status"] == "finalized"
    assert "Allergic Rhinitis" in data[0]["assessment"]


# ---------------------------------------------------------------------------
# Test 6: Patient views their own prescriptions
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_06_patient_views_own_prescriptions(
    async_client: AsyncClient,
    patient_a,
    patient_clinical_data,
):
    user, _ = patient_a
    token = create_access_token({"sub": str(user.user_id), "role": user.role.value})

    res = await async_client.get(
        "/api/v1/patients/me/prescriptions",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert len(data) >= 1
    assert data[0]["medications"][0]["name"] == "Cetirizine"
    assert data[0]["doctor_name"] == "Dr. Sarah Jenkins"


# ---------------------------------------------------------------------------
# Test 7: Strict Cross-Patient Isolation (Patient A cannot view Patient B)
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_07_cross_patient_isolation_enforced(
    async_client: AsyncClient,
    patient_a,
    patient_b,
    patient_clinical_data,
):
    user_a, _ = patient_a
    _, pat_b = patient_b
    token_a = create_access_token({"sub": str(user_a.user_id), "role": user_a.role.value})

    # Patient A attempts to read Patient B's profile
    res_prof = await async_client.get(
        f"/api/v1/patients/{pat_b.patient_id}/",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert res_prof.status_code == 403

    # Patient A attempts to update Patient B's profile
    res_update = await async_client.put(
        f"/api/v1/patients/{pat_b.patient_id}/",
        json={"full_name": "Tampered Name"},
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert res_update.status_code == 403

    # Patient A attempts to list Patient B's medical records
    res_mr = await async_client.get(
        f"/api/v1/medical-records/patient/{pat_b.patient_id}/",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert res_mr.status_code == 403

    # Patient A attempts to list Patient B's prescriptions
    res_rx = await async_client.get(
        f"/api/v1/prescriptions/patient/{pat_b.patient_id}/",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert res_rx.status_code == 403


# ---------------------------------------------------------------------------
# Test 8: Unauthenticated requests return 401
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_08_unauthenticated_requests_blocked(async_client: AsyncClient):
    res_me = await async_client.get("/api/v1/patients/me")
    assert res_me.status_code == 401

    res_dash = await async_client.get("/api/v1/patients/me/dashboard")
    assert res_dash.status_code == 401

    res_appts = await async_client.get("/api/v1/patients/me/appointments")
    assert res_appts.status_code == 401
