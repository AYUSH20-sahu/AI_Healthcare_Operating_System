"""Automated Test Suite for Milestone U-14: Doctor Schedule + Telehealth Consultation Room.

Tests covered:
1. Doctor retrieves daily schedule enriched with patient intake summaries.
2. Red-flag detection identifies emergency symptoms in patient intake.
3. Doctor accesses telehealth consultation room.
4. Patient accesses their own telehealth consultation room.
5. Unauthorized patient is rejected from foreign telehealth room (403 Forbidden).
6. Doctor starts telehealth consultation room (status -> in_progress).
7. Patient cannot start or modify consultation lifecycle (403 Forbidden).
8. Doctor concludes telehealth consultation room (status -> completed).
9. Unauthenticated requests are rejected (401 Unauthorized).
10. Direct red-flag pattern detector unit tests.
"""

import pytest
import pytest_asyncio
from datetime import date, datetime, timedelta
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.telehealth import detect_red_flags
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
async def doctor_dr_smith(db_session: AsyncSession):
    """Create Doctor Smith."""
    user = User(
        email="smith.u14@test.com",
        hashed_password=get_password_hash("password123"),
        full_name="Dr. Alan Smith",
        role=UserRole.DOCTOR,
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()

    doctor = Doctor(
        user_id=user.user_id,
        license_number="LIC-U14-SMITH",
        specialty="Internal Medicine",
        full_name="Dr. Alan Smith",
        email="smith.u14@test.com",
        hospital_affiliation="AI-HOS General Hospital",
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
        email="alice.u14@test.com",
        hashed_password=get_password_hash("password123"),
        full_name="Alice Wonder",
        role=UserRole.PATIENT,
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()

    patient = Patient(
        user_id=user.user_id,
        full_name="Alice Wonder",
        email="alice.u14@test.com",
        date_of_birth=date(1994, 6, 12),
        gender="Female",
        phone="+91 97777 11111",
        abha_address="alice.u14@abdm",
    )
    db_session.add(patient)
    await db_session.flush()

    # Create U-13 intake session with red flags
    intake = IntakeSession(
        patient_id=patient.patient_id,
        status=IntakeStatus.COMPLETED,
        messages=[
            {"role": "patient", "content": "I have crushing chest pain and shortness of breath for 1 hour."},
        ],
        structured_symptoms={
            "chief_complaint": "Severe crushing chest pain and shortness of breath",
            "duration": "1 hour",
            "severity": 9,
            "associated_symptoms": ["diaphoresis", "shortness of breath"],
            "summary": "Patient reports sudden onset of acute retrosternal pressure radiating to arm.",
        },
        ai_confidence=95.0,
    )
    db_session.add(intake)
    await db_session.commit()
    await db_session.refresh(user)
    await db_session.refresh(patient)
    return user, patient, intake


@pytest_asyncio.fixture
async def patient_bob(db_session: AsyncSession):
    """Create Patient Bob."""
    user = User(
        email="bob.u14@test.com",
        hashed_password=get_password_hash("password123"),
        full_name="Bob Builder",
        role=UserRole.PATIENT,
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()

    patient = Patient(
        user_id=user.user_id,
        full_name="Bob Builder",
        email="bob.u14@test.com",
        date_of_birth=date(1987, 2, 14),
        gender="Male",
        phone="+91 97777 22222",
        abha_address="bob.u14@abdm",
    )
    db_session.add(patient)
    await db_session.commit()
    await db_session.refresh(user)
    await db_session.refresh(patient)
    return user, patient


@pytest_asyncio.fixture
async def appointment_alice(db_session: AsyncSession, doctor_dr_smith, patient_alice):
    """Create today's appointment between Doctor Smith and Patient Alice."""
    _, doctor = doctor_dr_smith
    _, patient, _ = patient_alice

    appt = Appointment(
        patient_id=patient.patient_id,
        doctor_id=doctor.doctor_id,
        scheduled_at=datetime.utcnow() + timedelta(hours=1),
        duration_minutes=30,
        status=AppointmentStatus.SCHEDULED,
        notes="Urgent clinical evaluation",
    )
    db_session.add(appt)
    await db_session.commit()
    await db_session.refresh(appt)
    return appt


def auth_headers_for(user: User) -> dict[str, str]:
    token = create_access_token(data={"sub": user.email, "role": user.role.value})
    return {"Authorization": f"Bearer {token}"}


# =============================================================================
# Unit Tests
# =============================================================================

def test_red_flag_detection_helper_unit():
    """Verify red-flag pattern detector catches emergency conditions."""
    alerts = detect_red_flags("Patient experiencing severe crushing chest pain and fainting.")
    assert len(alerts) >= 2
    assert any("Cardiovascular" in a for a in alerts)
    assert any("Consciousness" in a for a in alerts)

    safe = detect_red_flags("Mild runny nose and dry throat for 2 days.")
    assert len(safe) == 0


# =============================================================================
# Telehealth Schedule & Room API Tests
# =============================================================================

@pytest.mark.asyncio
async def test_doctor_gets_schedule_with_intake_and_red_flags(
    async_client: AsyncClient,
    doctor_dr_smith,
    appointment_alice,
):
    """Doctor retrieves today's schedule and sees patient with U-13 intake & red flags."""
    doc_user, _ = doctor_dr_smith
    headers = auth_headers_for(doc_user)

    today_str = date.today().isoformat()
    response = await async_client.get(f"/api/v1/telehealth/schedule?date_str={today_str}", headers=headers)
    assert response.status_code == 200
    data = response.json()

    assert data["total_appointments"] >= 1
    assert data["date"] == today_str

    appt_data = next(a for a in data["appointments"] if a["appointment_id"] == str(appointment_alice.appointment_id))
    assert appt_data["patient_name"] == "Alice Wonder"
    assert appt_data["intake_summary"] is not None
    assert "chest pain" in appt_data["intake_summary"]["chief_complaint"].lower()
    assert appt_data["intake_summary"]["has_red_flags"] is True
    assert len(appt_data["intake_summary"]["red_flag_warnings"]) > 0


@pytest.mark.asyncio
async def test_doctor_gets_telehealth_room(
    async_client: AsyncClient,
    doctor_dr_smith,
    appointment_alice,
):
    """Doctor accesses the telehealth room."""
    doc_user, _ = doctor_dr_smith
    headers = auth_headers_for(doc_user)

    response = await async_client.get(
        f"/api/v1/telehealth/rooms/{appointment_alice.appointment_id}",
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()

    assert data["appointment_id"] == str(appointment_alice.appointment_id)
    assert data["room_id"] is not None
    assert data["meeting_link"] is not None
    assert data["doctor_name"] == "Dr. Alan Smith"
    assert data["patient_name"] == "Alice Wonder"
    assert data["intake_summary"]["has_red_flags"] is True


@pytest.mark.asyncio
async def test_patient_gets_telehealth_room(
    async_client: AsyncClient,
    patient_alice,
    appointment_alice,
):
    """Patient Alice accesses her own consultation room."""
    pat_user, _, _ = patient_alice
    headers = auth_headers_for(pat_user)

    response = await async_client.get(
        f"/api/v1/telehealth/rooms/{appointment_alice.appointment_id}",
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["patient_name"] == "Alice Wonder"


@pytest.mark.asyncio
async def test_cross_patient_unauthorized_room_access_forbidden(
    async_client: AsyncClient,
    patient_bob,
    appointment_alice,
):
    """Patient Bob tries to access Alice's consultation room (403 Forbidden)."""
    bob_user, _ = patient_bob
    headers = auth_headers_for(bob_user)

    response = await async_client.get(
        f"/api/v1/telehealth/rooms/{appointment_alice.appointment_id}",
        headers=headers,
    )
    assert response.status_code == 403
    assert "access denied" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_start_and_end_telehealth_consultation(
    async_client: AsyncClient,
    doctor_dr_smith,
    patient_alice,
    appointment_alice,
):
    """Doctor starts consultation and concludes it, verifying status lifecycle and timestamps."""
    doc_user, _ = doctor_dr_smith
    pat_user, _, _ = patient_alice
    doc_headers = auth_headers_for(doc_user)
    pat_headers = auth_headers_for(pat_user)

    # 1. Patient attempts to start room -> 403 Forbidden
    pat_start_res = await async_client.post(
        f"/api/v1/telehealth/rooms/{appointment_alice.appointment_id}/start",
        headers=pat_headers,
    )
    assert pat_start_res.status_code == 403

    # 2. Doctor starts room -> 200 OK (in_progress)
    start_res = await async_client.post(
        f"/api/v1/telehealth/rooms/{appointment_alice.appointment_id}/start",
        headers=doc_headers,
    )
    assert start_res.status_code == 200
    start_data = start_res.json()
    assert start_data["status"] == "in_progress"
    assert start_data["telehealth_started_at"] is not None

    # 3. Doctor ends room -> 200 OK (completed)
    end_res = await async_client.post(
        f"/api/v1/telehealth/rooms/{appointment_alice.appointment_id}/end",
        headers=doc_headers,
    )
    assert end_res.status_code == 200
    end_data = end_res.json()
    assert end_data["status"] == "completed"
    assert end_data["telehealth_ended_at"] is not None


@pytest.mark.asyncio
async def test_unauthenticated_requests_blocked(async_client: AsyncClient, appointment_alice):
    """Unauthenticated access to telehealth endpoints is blocked with 401."""
    res1 = await async_client.get("/api/v1/telehealth/schedule")
    assert res1.status_code == 401

    res2 = await async_client.get(f"/api/v1/telehealth/rooms/{appointment_alice.appointment_id}")
    assert res2.status_code == 401
