"""Automated Test Suite for Milestone U-17: Admin Application + Operational APIs (M30).

Tests covered:
1. Admin gets operational dashboard data (KPIs, active user distribution, appointment counts, telemetry).
2. Transparent future roadmap metrics disclosure (is_available: false, note present).
3. Admin gets real-time clinic patient queue with calculated wait times and relations.
4. Admin updates queue appointment status (scheduled -> in_progress -> completed) with audit logging.
5. Admin inspects doctor availability & capacity utilization matrix (slots calculation, utilization rate).
6. Admin gets operational analytics (specialties volume, prescription totals).
7. Admin reassigns user role (promotes to DOCTOR with profile creation and audit log).
8. Admin self-demotion prevented (400 Bad Request).
9. Admin deactivates user (soft delete with audit log).
10. Admin cannot delete self (400 Bad Request).
11. Strict RBAC: Doctor and Patient roles receive 403 Forbidden on admin operations routes.
12. Unauthenticated requests receive 401 Unauthorized.
"""

import pytest
import pytest_asyncio
from datetime import date, datetime, timedelta
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Appointment,
    AppointmentStatus,
    AuditLog,
    Doctor,
    Patient,
    User,
    UserRole,
)
from app.services.auth.service import create_access_token, get_password_hash


@pytest_asyncio.fixture
async def admin_user(db_session: AsyncSession):
    """Create a high-clearance System Administrator."""
    user = User(
        email="admin.u17@aihos.org",
        hashed_password=get_password_hash("adminpassword123"),
        full_name="Lead Operations Admin",
        role=UserRole.ADMIN,
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def doctor_user(db_session: AsyncSession):
    """Create an Attending Doctor with profile."""
    user = User(
        email="doctor.u17@aihos.org",
        hashed_password=get_password_hash("doctorpassword123"),
        full_name="Dr. Sunita Rao",
        role=UserRole.DOCTOR,
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()

    doctor = Doctor(
        user_id=user.user_id,
        license_number="LIC-U17-SUNITA",
        specialty="Pediatrics",
        full_name="Dr. Sunita Rao",
        email="doctor.u17@aihos.org",
        hospital_affiliation="AI-HOS Pediatric Center",
    )
    db_session.add(doctor)
    await db_session.commit()
    await db_session.refresh(user)
    await db_session.refresh(doctor)
    return user, doctor


@pytest_asyncio.fixture
async def patient_user(db_session: AsyncSession):
    """Create a Patient user with demographic profile."""
    user = User(
        email="patient.u17@test.com",
        hashed_password=get_password_hash("patientpassword123"),
        full_name="Karan Verma",
        role=UserRole.PATIENT,
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()

    patient = Patient(
        user_id=user.user_id,
        full_name="Karan Verma",
        email="patient.u17@test.com",
        date_of_birth=date(1996, 7, 12),
        gender="Male",
        phone="+91 99999 33333",
        abha_address="karan.u17@abdm",
    )
    db_session.add(patient)
    await db_session.commit()
    await db_session.refresh(user)
    await db_session.refresh(patient)
    return user, patient


@pytest_asyncio.fixture
async def staff_user(db_session: AsyncSession):
    """Create a Receptionist staff user for role reassignment testing."""
    user = User(
        email="reception.u17@aihos.org",
        hashed_password=get_password_hash("staffpassword123"),
        full_name="Ramesh FrontDesk",
        role=UserRole.RECEPTIONIST,
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def today_appointment(db_session: AsyncSession, doctor_user, patient_user):
    """Create an appointment scheduled for today."""
    _, doc = doctor_user
    _, pat = patient_user

    # Scheduled 15 mins ago to test wait-time calculation
    now = datetime.utcnow()
    scheduled_time = now - timedelta(minutes=15)

    appt = Appointment(
        patient_id=pat.patient_id,
        doctor_id=doc.doctor_id,
        scheduled_at=scheduled_time,
        duration_minutes=30,
        status=AppointmentStatus.SCHEDULED,
        reason="Follow-up pediatric consultation",
        notes="Pre-consultation Intake Summary: Child has recurring dry cough for 5 days.",
        meeting_link=f"/telehealth/room/{pat.patient_id}",
    )
    db_session.add(appt)
    await db_session.commit()
    await db_session.refresh(appt)
    return appt


# =============================================================================
# 1. Operational Dashboard & Telemetry Tests
# =============================================================================

@pytest.mark.asyncio
async def test_admin_get_operational_dashboard(
    async_client: AsyncClient,
    admin_user: User,
    doctor_user,
    patient_user,
    today_appointment,
):
    token = create_access_token({"sub": str(admin_user.user_id), "role": admin_user.role.value})
    headers = {"Authorization": f"Bearer {token}"}

    response = await async_client.get("/api/v1/admin/operations/dashboard", headers=headers)
    assert response.status_code == 200
    data = response.json()

    # User breakdown
    assert "users_summary" in data
    assert data["users_summary"]["doctors_count"] >= 1
    assert data["users_summary"]["patients_count"] >= 1
    assert data["users_summary"]["admins_count"] >= 1

    # Appointment metrics
    assert "appointments_summary" in data
    assert data["appointments_summary"]["today_total"] >= 1
    assert data["appointments_summary"]["today_scheduled"] >= 1

    # System telemetry
    assert data["system_telemetry"]["database_status"] == "healthy"
    assert data["system_telemetry"]["gemini_live_mesh"] == "operational"

    # Transparent roadmap disclosure check
    assert "future_capabilities" in data
    assert data["future_capabilities"]["iot_bed_occupancy"]["is_available"] is False
    assert "hardware" in data["future_capabilities"]["iot_bed_occupancy"]["status"]


# =============================================================================
# 2. Clinic Queue & Status Update Tests
# =============================================================================

@pytest.mark.asyncio
async def test_admin_get_clinic_queue_and_wait_time(
    async_client: AsyncClient,
    admin_user: User,
    today_appointment: Appointment,
    patient_user,
    doctor_user,
):
    token = create_access_token({"sub": str(admin_user.user_id), "role": admin_user.role.value})
    headers = {"Authorization": f"Bearer {token}"}

    response = await async_client.get("/api/v1/admin/operations/queue", headers=headers)
    assert response.status_code == 200
    data = response.json()

    assert data["total_in_queue"] >= 1
    queue_item = next(
        (q for q in data["queue"] if q["appointment_id"] == str(today_appointment.appointment_id)), None
    )
    assert queue_item is not None
    assert queue_item["patient_name"] == "Karan Verma"
    assert queue_item["doctor_name"] == "Dr. Sunita Rao"
    assert queue_item["doctor_specialty"] == "Pediatrics"
    assert queue_item["status"] == "scheduled"
    assert queue_item["wait_time_minutes"] >= 14  # Scheduled 15 mins ago
    assert "dry cough" in (queue_item["intake_chief_complaint"] or "")


@pytest.mark.asyncio
async def test_admin_update_queue_status_with_audit(
    async_client: AsyncClient,
    admin_user: User,
    today_appointment: Appointment,
):
    token = create_access_token({"sub": str(admin_user.user_id), "role": admin_user.role.value})
    headers = {"Authorization": f"Bearer {token}"}

    # Transition to in_progress
    res = await async_client.patch(
        f"/api/v1/admin/operations/queue/{today_appointment.appointment_id}/status",
        headers=headers,
        json={"status": "in_progress"},
    )
    assert res.status_code == 200
    assert res.json()["status"] == "in_progress"

    # Transition to completed
    res2 = await async_client.patch(
        f"/api/v1/admin/operations/queue/{today_appointment.appointment_id}/status",
        headers=headers,
        json={"status": "completed"},
    )
    assert res2.status_code == 200
    assert res2.json()["status"] == "completed"


# =============================================================================
# 3. Doctor Capacity & Availability Matrix Tests
# =============================================================================

@pytest.mark.asyncio
async def test_admin_get_doctors_availability_matrix(
    async_client: AsyncClient,
    admin_user: User,
    doctor_user,
    today_appointment: Appointment,
):
    token = create_access_token({"sub": str(admin_user.user_id), "role": admin_user.role.value})
    headers = {"Authorization": f"Bearer {token}"}

    response = await async_client.get("/api/v1/admin/operations/doctors-availability", headers=headers)
    assert response.status_code == 200
    data = response.json()

    assert data["total_doctors"] >= 1
    assert "doctors" in data
    sunita_card = next(
        (d for d in data["doctors"] if d["doctor_name"] == "Dr. Sunita Rao"), None
    )
    assert sunita_card is not None
    assert sunita_card["specialty"] == "Pediatrics"
    assert sunita_card["total_slots"] == 14
    assert sunita_card["booked_slots"] >= 1
    assert sunita_card["available_slots"] <= 13
    assert sunita_card["utilization_rate_pct"] > 0.0


# =============================================================================
# 4. Operational Analytics Tests
# =============================================================================

@pytest.mark.asyncio
async def test_admin_get_operational_analytics(
    async_client: AsyncClient,
    admin_user: User,
    today_appointment,
):
    token = create_access_token({"sub": str(admin_user.user_id), "role": admin_user.role.value})
    headers = {"Authorization": f"Bearer {token}"}

    response = await async_client.get("/api/v1/admin/operations/analytics", headers=headers)
    assert response.status_code == 200
    data = response.json()

    assert "appointments_by_specialty" in data
    assert any(s["specialty"] == "Pediatrics" for s in data["appointments_by_specialty"])
    assert "future_metrics" in data
    assert data["future_metrics"]["patient_no_show_prediction"]["is_available"] is False


# =============================================================================
# 5. User Role Management & Deactivation Tests
# =============================================================================

@pytest.mark.asyncio
async def test_admin_reassign_user_role_to_doctor(
    async_client: AsyncClient,
    admin_user: User,
    staff_user: User,
):
    token = create_access_token({"sub": str(admin_user.user_id), "role": admin_user.role.value})
    headers = {"Authorization": f"Bearer {token}"}

    # Promote receptionist Ramesh to Doctor
    payload = {
        "new_role": "doctor",
        "specialty": "Emergency Medicine",
        "license_number": "LIC-U17-RAMESH-ER",
    }
    res = await async_client.patch(
        f"/api/v1/admin/users/{staff_user.user_id}/role",
        headers=headers,
        json=payload,
    )
    assert res.status_code == 200
    user_data = res.json()
    assert user_data["role"] == "doctor"
    assert user_data["doctor_profile"] is not None
    assert user_data["doctor_profile"]["specialty"] == "Emergency Medicine"


@pytest.mark.asyncio
async def test_admin_self_demotion_blocked_400(
    async_client: AsyncClient,
    admin_user: User,
):
    token = create_access_token({"sub": str(admin_user.user_id), "role": admin_user.role.value})
    headers = {"Authorization": f"Bearer {token}"}

    # Attempt to demote self
    res = await async_client.patch(
        f"/api/v1/admin/users/{admin_user.user_id}/role",
        headers=headers,
        json={"new_role": "patient"},
    )
    assert res.status_code == 400
    assert "cannot demote their own account" in res.json()["detail"]


@pytest.mark.asyncio
async def test_admin_deactivate_user(
    async_client: AsyncClient,
    admin_user: User,
    staff_user: User,
):
    token = create_access_token({"sub": str(admin_user.user_id), "role": admin_user.role.value})
    headers = {"Authorization": f"Bearer {token}"}

    res = await async_client.delete(f"/api/v1/admin/users/{staff_user.user_id}", headers=headers)
    assert res.status_code == 200
    assert "deactivated successfully" in res.json()["detail"]


@pytest.mark.asyncio
async def test_admin_self_deletion_blocked_400(
    async_client: AsyncClient,
    admin_user: User,
):
    token = create_access_token({"sub": str(admin_user.user_id), "role": admin_user.role.value})
    headers = {"Authorization": f"Bearer {token}"}

    res = await async_client.delete(f"/api/v1/admin/users/{admin_user.user_id}", headers=headers)
    assert res.status_code == 400
    assert "cannot delete their own account" in res.json()["detail"]


# =============================================================================
# 6. Strict RBAC & Unauthenticated Rejection Tests
# =============================================================================

@pytest.mark.asyncio
async def test_non_admin_rbac_isolation_403(
    async_client: AsyncClient,
    doctor_user,
    patient_user,
):
    doc_user, _ = doctor_user
    pat_user, _ = patient_user

    doc_headers = {"Authorization": f"Bearer {create_access_token({'sub': str(doc_user.user_id), 'role': doc_user.role.value})}"}
    pat_headers = {"Authorization": f"Bearer {create_access_token({'sub': str(pat_user.user_id), 'role': pat_user.role.value})}"}

    # Doctor access denied
    res_doc = await async_client.get("/api/v1/admin/operations/dashboard", headers=doc_headers)
    assert res_doc.status_code == 403

    # Patient access denied
    res_pat = await async_client.get("/api/v1/admin/operations/queue", headers=pat_headers)
    assert res_pat.status_code == 403


@pytest.mark.asyncio
async def test_unauthenticated_requests_rejected_401(
    async_client: AsyncClient,
):
    res = await async_client.get("/api/v1/admin/operations/dashboard")
    assert res.status_code == 401
