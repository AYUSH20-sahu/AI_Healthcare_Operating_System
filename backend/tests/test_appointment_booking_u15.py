"""Automated Test Suite for Milestone U-15: Patient Appointment Booking End-to-End.

Tests covered:
1. Patient can view doctor directory (GET /api/v1/doctors) and specialties (GET /api/v1/doctors/specialties).
2. Doctor availability calculation (GET /api/v1/appointments/availability) returns structured 30-min slots.
3. Patient successfully schedules an appointment via dedicated booking endpoint (POST /api/v1/appointments/book).
4. Booked slot is immediately marked unavailable in subsequent availability checks.
5. Conflict detection blocks double-booking with 409 Conflict.
6. Contextual U-13 intake session is linked into appointment notes.
7. RBAC prevents patients from creating appointments for other patients (403 Forbidden).
8. Unauthenticated requests are rejected (401 Unauthorized).
"""

import pytest
import pytest_asyncio
from datetime import date, datetime, time, timedelta
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Appointment,
    AppointmentStatus,
    Doctor,
    IntakeSession,
    IntakeStatus,
    Patient,
    User,
    UserRole,
)
from app.services.auth.service import create_access_token, get_password_hash


@pytest_asyncio.fixture
async def attending_doctor(db_session: AsyncSession):
    """Create an attending cardiologist."""
    user = User(
        email="doctor.u15@test.com",
        hashed_password=get_password_hash("password123"),
        full_name="Dr. Priya Patel",
        role=UserRole.DOCTOR,
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()

    doctor = Doctor(
        user_id=user.user_id,
        license_number="LIC-U15-PRIYA",
        specialty="Cardiology",
        full_name="Dr. Priya Patel",
        email="doctor.u15@test.com",
        hospital_affiliation="AI-HOS Heart Institute",
    )
    db_session.add(doctor)
    await db_session.commit()
    await db_session.refresh(user)
    await db_session.refresh(doctor)
    return user, doctor


@pytest_asyncio.fixture
async def patient_alice(db_session: AsyncSession):
    """Create Patient Alice with an intake session."""
    user = User(
        email="alice.u15@test.com",
        hashed_password=get_password_hash("password123"),
        full_name="Alice Booking",
        role=UserRole.PATIENT,
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()

    patient = Patient(
        user_id=user.user_id,
        full_name="Alice Booking",
        email="alice.u15@test.com",
        date_of_birth=date(1993, 5, 20),
        gender="Female",
        phone="+91 96666 11111",
        abha_address="alice.u15@abdm",
    )
    db_session.add(patient)
    await db_session.flush()

    intake = IntakeSession(
        patient_id=patient.patient_id,
        status=IntakeStatus.COMPLETED,
        messages=[{"role": "patient", "content": "Mild chest tightness when climbing stairs."}],
        structured_symptoms={
            "chief_complaint": "Exertional chest tightness",
            "duration": "2 weeks",
            "severity": 6,
            "summary": "Patient reports retrosternal tightness on exertion.",
        },
        ai_confidence=92.0,
    )
    db_session.add(intake)
    await db_session.commit()
    await db_session.refresh(user)
    await db_session.refresh(patient)
    await db_session.refresh(intake)
    return user, patient, intake


@pytest_asyncio.fixture
async def patient_bob(db_session: AsyncSession):
    """Create Patient Bob."""
    user = User(
        email="bob.u15@test.com",
        hashed_password=get_password_hash("password123"),
        full_name="Bob Competitor",
        role=UserRole.PATIENT,
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()

    patient = Patient(
        user_id=user.user_id,
        full_name="Bob Competitor",
        email="bob.u15@test.com",
        date_of_birth=date(1985, 11, 10),
        gender="Male",
        phone="+91 96666 22222",
        abha_address="bob.u15@abdm",
    )
    db_session.add(patient)
    await db_session.commit()
    await db_session.refresh(user)
    await db_session.refresh(patient)
    return user, patient


def auth_headers_for(user: User) -> dict[str, str]:
    token = create_access_token(data={"sub": user.email, "role": user.role.value})
    return {"Authorization": f"Bearer {token}"}


# =============================================================================
# Tests
# =============================================================================

@pytest.mark.asyncio
async def test_patient_lists_doctors_and_specialties(
    async_client: AsyncClient,
    patient_alice,
    attending_doctor,
):
    """Patient can discover doctors and distinct specialties."""
    pat_user, _, _ = patient_alice
    headers = auth_headers_for(pat_user)

    # 1. Specialties
    spec_res = await async_client.get("/api/v1/doctors/specialties", headers=headers)
    assert spec_res.status_code == 200
    specialties = spec_res.json()
    assert "Cardiology" in specialties

    # 2. Doctors list
    docs_res = await async_client.get("/api/v1/doctors/?specialty=Cardiology", headers=headers)
    assert docs_res.status_code == 200
    data = docs_res.json()
    assert data["total"] >= 1
    assert any(d["specialty"] == "Cardiology" for d in data["doctors"])


@pytest.mark.asyncio
async def test_doctor_availability_slots_generation(
    async_client: AsyncClient,
    patient_alice,
    attending_doctor,
):
    """Doctor availability engine generates daily 30-minute consultation slots."""
    pat_user, _, _ = patient_alice
    _, doctor = attending_doctor
    headers = auth_headers_for(pat_user)

    tomorrow_str = (date.today() + timedelta(days=2)).isoformat()
    res = await async_client.get(
        f"/api/v1/appointments/availability?doctor_id={doctor.doctor_id}&date_str={tomorrow_str}&duration_minutes=30",
        headers=headers,
    )
    assert res.status_code == 200
    data = res.json()

    assert data["doctor_id"] == str(doctor.doctor_id)
    assert data["total_slots"] > 0
    assert data["available_slots_count"] > 0
    # Check slots include standard clinic times
    times = [s["slot_time"] for s in data["slots"]]
    assert any("09:00" in t for t in times)
    assert any("10:00" in t for t in times)


@pytest.mark.asyncio
async def test_patient_book_appointment_flow(
    async_client: AsyncClient,
    patient_alice,
    attending_doctor,
):
    """Patient Alice books an appointment linking active U-13 intake session."""
    pat_user, patient, intake = patient_alice
    _, doctor = attending_doctor
    headers = auth_headers_for(pat_user)

    booking_date = date.today() + timedelta(days=3)
    slot_dt = datetime.combine(booking_date, time(10, 0, 0))

    payload = {
        "doctor_id": str(doctor.doctor_id),
        "scheduled_at": slot_dt.isoformat(),
        "duration_minutes": 30,
        "reason": "Cardiology checkup following symptom review",
        "intake_session_id": str(intake.session_id),
    }

    res = await async_client.post("/api/v1/appointments/book", json=payload, headers=headers)
    assert res.status_code == 201
    data = res.json()

    assert data["doctor_id"] == str(doctor.doctor_id)
    assert data["patient_id"] == str(patient.patient_id)
    assert data["status"] == "scheduled"
    assert "[AI Intake]" in data["notes"]
    assert "Exertional chest tightness" in data["notes"]


@pytest.mark.asyncio
async def test_slot_unavailable_and_double_booking_conflict(
    async_client: AsyncClient,
    patient_alice,
    patient_bob,
    attending_doctor,
):
    """Double-booking is prevented: booked slot becomes unavailable and returns 409 Conflict."""
    alice_user, _, _ = patient_alice
    bob_user, _ = patient_bob
    _, doctor = attending_doctor

    alice_headers = auth_headers_for(alice_user)
    bob_headers = auth_headers_for(bob_user)

    booking_date = date.today() + timedelta(days=4)
    target_dt = datetime.combine(booking_date, time(11, 0, 0))

    # 1. Alice books 11:00 AM slot
    alice_payload = {
        "doctor_id": str(doctor.doctor_id),
        "scheduled_at": target_dt.isoformat(),
        "duration_minutes": 30,
        "reason": "Routine consult",
    }
    alice_res = await async_client.post("/api/v1/appointments/book", json=alice_payload, headers=alice_headers)
    assert alice_res.status_code == 201

    # 2. Availability query now marks 11:00 AM as unavailable
    avail_res = await async_client.get(
        f"/api/v1/appointments/availability?doctor_id={doctor.doctor_id}&date_str={booking_date.isoformat()}",
        headers=bob_headers,
    )
    assert avail_res.status_code == 200
    slots = avail_res.json()["slots"]
    slot_11 = next(s for s in slots if "11:00" in s["slot_time"])
    assert slot_11["is_available"] is False
    assert slot_11["conflict_reason"] == "Booked"

    # 3. Bob attempts to book the same 11:00 AM slot -> 409 Conflict
    bob_payload = {
        "doctor_id": str(doctor.doctor_id),
        "scheduled_at": target_dt.isoformat(),
        "duration_minutes": 30,
        "reason": "Conflicting attempt",
    }
    bob_res = await async_client.post("/api/v1/appointments/book", json=bob_payload, headers=bob_headers)
    assert bob_res.status_code == 409
    assert "no longer available" in bob_res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_patient_cannot_book_for_another_patient(
    async_client: AsyncClient,
    patient_alice,
    patient_bob,
    attending_doctor,
):
    """RBAC prevents Patient Alice from using create_appointment with Patient Bob's ID (403 Forbidden)."""
    alice_user, _, _ = patient_alice
    _, bob_patient = patient_bob
    _, doctor = attending_doctor

    alice_headers = auth_headers_for(alice_user)

    malicious_payload = {
        "patient_id": str(bob_patient.patient_id),
        "doctor_id": str(doctor.doctor_id),
        "scheduled_at": (datetime.utcnow() + timedelta(days=5)).isoformat(),
        "duration_minutes": 30,
        "notes": "Impersonation attempt",
    }

    res = await async_client.post("/api/v1/appointments/", json=malicious_payload, headers=alice_headers)
    assert res.status_code == 403
    assert "only book appointments for themselves" in res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_unauthenticated_booking_blocked(async_client: AsyncClient):
    """Unauthenticated access is blocked with 401."""
    res1 = await async_client.get("/api/v1/appointments/availability?doctor_id=00000000-0000-0000-0000-000000000000&date_str=2026-09-15")
    assert res1.status_code == 401

    res2 = await async_client.post("/api/v1/appointments/book", json={})
    assert res2.status_code == 401
