"""Unit and integration tests for Inpatient Care, Bedside Telemetry, and Nurse Workstation."""

import pytest
from uuid import uuid4
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User, UserRole
from app.services.auth.service import create_access_token, get_password_hash


@pytest.fixture
async def nurse_user(db_session: AsyncSession):
    """Create a staff nurse user."""
    user = User(
        user_id=uuid4(),
        email="nurse.duty@aihos.org",
        hashed_password=get_password_hash("nursepassword123"),
        full_name="Nurse Florence Nightingale",
        role=UserRole.NURSE,
        department="Intensive Care Unit (ICU)",
        designation="ICU Staff Nurse",
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
def nurse_headers(nurse_user: User):
    token = create_access_token(
        data={"sub": str(nurse_user.user_id), "email": nurse_user.email, "role": nurse_user.role.value}
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_get_inpatient_beds_autoseeding(client: AsyncClient, nurse_headers: dict):
    """Verify GET /api/v1/nurses/inpatient-beds auto-seeds baseline ward beds when empty."""
    resp = await client.get("/api/v1/nurses/inpatient-beds", headers=nurse_headers)
    assert resp.status_code == 200
    beds = resp.json()
    assert isinstance(beds, list)
    assert len(beds) >= 5

    icu_beds = [b for b in beds if "ICU" in b["bedNumber"]]
    assert len(icu_beds) >= 2

    first_bed = beds[0]
    assert "bedId" in first_bed
    assert "bedNumber" in first_bed
    assert "vitals" in first_bed
    assert "bp" in first_bed["vitals"]
    assert "pulse" in first_bed["vitals"]
    assert "spo2" in first_bed["vitals"]
    assert "temp" in first_bed["vitals"]


@pytest.mark.asyncio
async def test_ward_filtering(client: AsyncClient, nurse_headers: dict):
    """Test filtering beds by ward e.g. icu vs ward."""
    icu_resp = await client.get("/api/v1/nurses/inpatient-beds?ward=icu", headers=nurse_headers)
    assert icu_resp.status_code == 200
    icu_beds = icu_resp.json()
    assert all("Intensive Care" in b["ward"] for b in icu_beds)

    ward_resp = await client.get("/api/v1/nurses/inpatient-beds?ward=ward", headers=nurse_headers)
    assert ward_resp.status_code == 200
    general_beds = ward_resp.json()
    assert all("General Ward" in b["ward"] for b in general_beds)


@pytest.mark.asyncio
async def test_log_bedside_vitals_normal_and_critical(client: AsyncClient, nurse_headers: dict):
    """Verify logging calibrated telemetry vitals and automated safety threshold evaluation."""
    beds_resp = await client.get("/api/v1/nurses/inpatient-beds", headers=nurse_headers)
    beds = beds_resp.json()
    target_bed = beds[0]
    bed_id = target_bed["bedId"]

    # 1. Log stable vitals
    log_resp = await client.post(
        f"/api/v1/nurses/inpatient-beds/{bed_id}/vitals",
        headers=nurse_headers,
        json={
            "systolic": 118,
            "diastolic": 76,
            "pulse": 72,
            "spo2": 99,
            "temp": 98.4,
            "respiratory_rate": 16,
            "pain_score": 1,
            "notes": "Patient resting comfortably after lunch.",
        },
    )
    assert log_resp.status_code == 200
    data = log_resp.json()
    assert data["bed"]["status"] == "Stable"
    assert data["vitalsLog"]["isCritical"] is False
    assert data["bed"]["vitals"]["spo2"] == 99

    # 2. Log critical vitals (hypoxia + tachycardia)
    crit_resp = await client.post(
        f"/api/v1/nurses/inpatient-beds/{bed_id}/vitals",
        headers=nurse_headers,
        json={
            "systolic": 185,
            "diastolic": 105,
            "pulse": 128,
            "spo2": 88,
            "temp": 102.5,
            "respiratory_rate": 28,
            "pain_score": 8,
            "notes": "Acute distress, oxygen cannula dislodged, emergency call placed.",
        },
    )
    assert crit_resp.status_code == 200
    crit_data = crit_resp.json()
    assert crit_data["bed"]["status"] == "Critical"
    assert crit_data["vitalsLog"]["isCritical"] is True
    assert crit_data["vitalsLog"]["spo2"] == 88


@pytest.mark.asyncio
async def test_get_bed_vitals_history(client: AsyncClient, nurse_headers: dict):
    """Verify retrieving historical bedside telemetry entries."""
    beds_resp = await client.get("/api/v1/nurses/inpatient-beds", headers=nurse_headers)
    bed_id = beds_resp.json()[0]["bedId"]

    hist_resp = await client.get(
        f"/api/v1/nurses/inpatient-beds/{bed_id}/vitals-history",
        headers=nurse_headers,
    )
    assert hist_resp.status_code == 200
    history = hist_resp.json()
    assert isinstance(history, list)
    assert len(history) >= 1
    assert "pulse" in history[0]
    assert "spo2" in history[0]
    assert "recordedAt" in history[0]


@pytest.mark.asyncio
async def test_mark_medication_administered(client: AsyncClient, nurse_headers: dict):
    """Verify nurse can complete scheduled medication round on inpatient bed."""
    beds_resp = await client.get("/api/v1/nurses/inpatient-beds", headers=nurse_headers)
    bed_id = beds_resp.json()[0]["bedId"]

    med_resp = await client.post(
        f"/api/v1/nurses/inpatient-beds/{bed_id}/medication-administered",
        headers=nurse_headers,
    )
    assert med_resp.status_code == 200
    body = med_resp.json()
    assert "Completed" in body["bed"]["medicationDue"]


@pytest.mark.asyncio
async def test_shift_tasks_and_status_update(client: AsyncClient, nurse_headers: dict):
    """Verify fetching and transitioning shift medication and ward round tasks."""
    tasks_resp = await client.get("/api/v1/nurses/shift-tasks", headers=nurse_headers)
    assert tasks_resp.status_code == 200
    tasks_data = tasks_resp.json()

    assert "medTasks" in tasks_data
    assert "roundTasks" in tasks_data
    assert len(tasks_data["medTasks"]) >= 1

    first_task = tasks_data["medTasks"][0]
    task_id = first_task["id"]

    # Transition to administered
    patch_resp = await client.patch(
        f"/api/v1/nurses/shift-tasks/{task_id}/status",
        headers=nurse_headers,
        json={"status": "administered", "notes": "Dose administered via IV infusion."},
    )
    assert patch_resp.status_code == 200
    patched_data = patch_resp.json()
    assert patched_data["task"]["status"] == "administered"
    assert "IV infusion" in patched_data["task"]["notes"]


@pytest.mark.asyncio
async def test_assigned_patients_roster(client: AsyncClient, nurse_headers: dict):
    """Verify GET /api/v1/nurses/assigned-patients returns active patient roster with pending metrics."""
    roster_resp = await client.get("/api/v1/nurses/assigned-patients", headers=nurse_headers)
    assert roster_resp.status_code == 200
    roster = roster_resp.json()
    assert isinstance(roster, list)
    assert len(roster) >= 5

    first = roster[0]
    assert "patientName" in first
    assert "bedNumber" in first
    assert "ward" in first
    assert "pendingMeds" in first
    assert "pendingRounds" in first
    assert "lastVitals" in first
    assert "diet" in first
    assert "codeStatus" in first
