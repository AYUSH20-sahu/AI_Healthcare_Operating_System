"""Automated Test Suite for Milestone U-21: ABDM Integration Foundations (M34).

Tests covered:
1. ABDM Gateway Status: GET /api/v1/abdm/status returns sandbox mode, HFR profile, and never leaks client_secret.
2. ABHA Linking Init: POST /api/v1/abdm/abha/init returns transaction_id and OTP dispatch notice.
3. ABHA Address Validation: Malformed ABHA addresses return 400 Bad Request.
4. ABHA OTP Verification: POST /api/v1/abdm/abha/verify with test OTP (123456) links ABHA and writes audit log.
5. ABHA OTP Verification Failure: Incorrect OTP returns 400 Bad Request.
6. ABHA Unlinking: DELETE /api/v1/abdm/abha/unlink clears abha_address and writes audit log.
7. ABDM Consent Request: POST /api/v1/abdm/consent/request generates HIU consent artifact.
8. Consent Notification Webhook: POST /api/v1/abdm/consent/notification processes callback acknowledgment.
9. HFR Facility Profile: GET /api/v1/abdm/hfr returns facility metadata.
10. HPR Professional Registry: GET /api/v1/abdm/hpr/{doctor_id} returns verified clinician registration stub.
11. Strict RBAC: Doctor cannot call personal ABHA linking routes (403 Forbidden).
12. Unauthenticated Requests: 401 Unauthorized when missing authorization token.
"""

import uuid
from datetime import date, datetime
import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models import (
    AuditLog,
    AuditOutcome,
    Doctor,
    Patient,
    User,
    UserRole,
)
from app.services.auth.service import create_access_token, get_password_hash


@pytest_asyncio.fixture
async def patient_a_user(db_session: AsyncSession):
    """Create Patient Alice."""
    user = User(
        email="alice.abdm.u21@aihos.org",
        hashed_password=get_password_hash("alicepass123"),
        full_name="Alice ABDM Patient",
        role=UserRole.PATIENT,
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    patient = Patient(
        user_id=user.user_id,
        full_name="Alice ABDM Patient",
        email=user.email,
        phone="+91-9876543210",
        date_of_birth=date(1993, 7, 21),
        gender="Female",
        abha_address=None,
    )
    db_session.add(patient)
    await db_session.commit()
    await db_session.refresh(patient)
    return user, patient


@pytest_asyncio.fixture
async def doctor_user(db_session: AsyncSession):
    """Create Doctor Vikram."""
    user = User(
        email="vikram.abdm.u21@aihos.org",
        hashed_password=get_password_hash("vikrampass123"),
        full_name="Dr. Vikram Sen",
        role=UserRole.DOCTOR,
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    doctor = Doctor(
        user_id=user.user_id,
        full_name="Dr. Vikram Sen",
        email=user.email,
        specialty="Cardiology",
        hospital_affiliation="AI-HOS Apex Center",
        license_number="HPR-IN-4455",
    )
    db_session.add(doctor)
    await db_session.commit()
    await db_session.refresh(doctor)
    return user, doctor


def _auth_header(user: User) -> dict:
    token = create_access_token(data={"sub": str(user.user_id), "role": user.role.value})
    return {"Authorization": f"Bearer {token}"}


# =============================================================================
# Milestone U-21 Tests
# =============================================================================

@pytest.mark.asyncio
async def test_abdm_gateway_status_and_security(client: AsyncClient):
    """Test GET /api/v1/abdm/status returns sanitized information and never leaks secrets."""
    res = await client.get("/api/v1/abdm/status")
    assert res.status_code == 200, res.text
    data = res.json()

    assert "gateway_status" in data
    assert data["environment"] == "sandbox"
    assert data["hfr_facility_id"] == "IN-DL-AIHOS-001"
    assert "MOBILE_OTP" in data["supported_auth_modes"]

    # CRITICAL SECURITY RULE: Zero credential exposure
    assert "client_secret" not in data
    assert "ABDM_CLIENT_SECRET" not in data
    assert "api_key" not in data
    assert "token" not in data


@pytest.mark.asyncio
async def test_abha_link_initiation_and_format_validation(
    client: AsyncClient,
    patient_a_user,
):
    """Test initiating ABHA linking with valid and invalid address formats."""
    user, _ = patient_a_user

    # 1. Valid ABHA address
    res = await client.post(
        "/api/v1/abdm/abha/init",
        json={"abha_address": "alice.patient@abdm", "auth_mode": "MOBILE_OTP"},
        headers=_auth_header(user),
    )
    assert res.status_code == 200, res.text
    data = res.json()
    assert "transaction_id" in data
    assert data["abha_address"] == "alice.patient@abdm"
    assert data["sandbox_test_otp"] == "123456"

    # 2. Invalid ABHA address format
    bad_res = await client.post(
        "/api/v1/abdm/abha/init",
        json={"abha_address": "invalid address with spaces!", "auth_mode": "MOBILE_OTP"},
        headers=_auth_header(user),
    )
    assert bad_res.status_code == 400
    assert "invalid" in bad_res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_abha_otp_verification_success_and_audit_trail(
    client: AsyncClient,
    db_session: AsyncSession,
    patient_a_user,
):
    """Test OTP verification updates patient abha_address and records audit log."""
    user, patient = patient_a_user

    # Step 1: Initiate
    init_res = await client.post(
        "/api/v1/abdm/abha/init",
        json={"abha_address": "alice.verified@abdm"},
        headers=_auth_header(user),
    )
    tx_id = init_res.json()["transaction_id"]

    # Step 2: Verify with sandbox test OTP
    verify_res = await client.post(
        "/api/v1/abdm/abha/verify",
        json={"transaction_id": tx_id, "otp": "123456"},
        headers=_auth_header(user),
    )
    assert verify_res.status_code == 200, verify_res.text
    data = verify_res.json()
    assert data["status"] == "LINKED"
    assert data["abha_address"] == "alice.verified@abdm"

    # Check database persistence
    refreshed_patient = await db_session.get(Patient, patient.patient_id)
    assert refreshed_patient.abha_address == "alice.verified@abdm"

    # Check audit log
    audit_res = await db_session.execute(
        select(AuditLog).where(
            AuditLog.action == "ABDM_LINK_ABHA",
            AuditLog.resource_id == patient.patient_id,
        )
    )
    audit = audit_res.scalar_one_or_none()
    assert audit is not None
    assert audit.outcome == AuditOutcome.SUCCESS
    assert audit.details["abha_address"] == "alice.verified@abdm"


@pytest.mark.asyncio
async def test_abha_otp_verification_failure(
    client: AsyncClient,
    patient_a_user,
):
    """Test incorrect OTP returns 400 Bad Request."""
    user, _ = patient_a_user

    init_res = await client.post(
        "/api/v1/abdm/abha/init",
        json={"abha_address": "alice.fail@abdm"},
        headers=_auth_header(user),
    )
    tx_id = init_res.json()["transaction_id"]

    # Submit invalid OTP
    bad_otp_res = await client.post(
        "/api/v1/abdm/abha/verify",
        json={"transaction_id": tx_id, "otp": "000000"},
        headers=_auth_header(user),
    )
    assert bad_otp_res.status_code == 400
    assert "invalid otp" in bad_otp_res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_abha_unlinking_lifecycle(
    client: AsyncClient,
    db_session: AsyncSession,
    patient_a_user,
):
    """Test unlinking ABHA address sets field to null and writes audit log."""
    user, patient = patient_a_user

    # Set address
    patient.abha_address = "alice.unlink@abdm"
    await db_session.commit()

    # Unlink
    unlink_res = await client.delete(
        "/api/v1/abdm/abha/unlink",
        headers=_auth_header(user),
    )
    assert unlink_res.status_code == 200, unlink_res.text
    assert unlink_res.json()["status"] == "UNLINKED"

    # Verify database
    refreshed = await db_session.get(Patient, patient.patient_id)
    assert refreshed.abha_address is None

    # Verify audit event
    audit_res = await db_session.execute(
        select(AuditLog).where(
            AuditLog.action == "ABDM_UNLINK_ABHA",
            AuditLog.resource_id == patient.patient_id,
        )
    )
    audit = audit_res.scalar_one_or_none()
    assert audit is not None


@pytest.mark.asyncio
async def test_abdm_consent_request_and_notification(
    client: AsyncClient,
    patient_a_user,
    doctor_user,
):
    """Test creating ABDM Consent Request and handling Consent Notification callback."""
    user_p, _ = patient_a_user
    _, doctor = doctor_user

    # 1. Create Consent Request
    req_res = await client.post(
        "/api/v1/abdm/consent/request",
        json={
            "provider_id": str(doctor.doctor_id),
            "record_scope": "full_access",
            "purpose": "Clinical Evaluation",
        },
        headers=_auth_header(user_p),
    )
    assert req_res.status_code == 200, req_res.text
    req_data = req_res.json()
    assert req_data["status"] == "REQUESTED"
    request_id = req_data["request_id"]

    # 2. Consent Notification Webhook
    notif_res = await client.post(
        "/api/v1/abdm/consent/notification",
        json={
            "request_id": request_id,
            "status": "GRANTED",
            "consent_artefact_id": "artefact-sample-123",
        },
    )
    assert notif_res.status_code == 200
    assert notif_res.json()["status"] == "ACKNOWLEDGED"

    # 3. Check status
    stat_res = await client.get(
        f"/api/v1/abdm/consent/{request_id}",
        headers=_auth_header(user_p),
    )
    assert stat_res.status_code == 200
    assert stat_res.json()["status"] == "GRANTED"


@pytest.mark.asyncio
async def test_hfr_and_hpr_registry_stubs(
    client: AsyncClient,
    patient_a_user,
    doctor_user,
):
    """Test HFR facility and HPR doctor lookup endpoints."""
    user_p, _ = patient_a_user
    _, doctor = doctor_user

    # HFR Facility profile
    hfr_res = await client.get("/api/v1/abdm/hfr")
    assert hfr_res.status_code == 200
    assert hfr_res.json()["facility_id"] == "IN-DL-AIHOS-001"
    assert hfr_res.json()["abdm_registered"] is True

    # HPR Doctor profile
    hpr_res = await client.get(
        f"/api/v1/abdm/hpr/{doctor.doctor_id}",
        headers=_auth_header(user_p),
    )
    assert hpr_res.status_code == 200
    assert hpr_res.json()["doctor_id"] == str(doctor.doctor_id)
    assert "vikramsen@hpr" in hpr_res.json()["hpr_id"]
    assert hpr_res.json()["telehealth_authorized"] is True


@pytest.mark.asyncio
async def test_doctor_cannot_manage_personal_abha(
    client: AsyncClient,
    doctor_user,
):
    """Doctor role cannot call personal ABHA linking endpoint (403 Forbidden)."""
    doc_user, _ = doctor_user

    res = await client.post(
        "/api/v1/abdm/abha/init",
        json={"abha_address": "doc@abdm"},
        headers=_auth_header(doc_user),
    )
    assert res.status_code == 403


@pytest.mark.asyncio
async def test_unauthenticated_requests_rejected(client: AsyncClient):
    """Unauthenticated requests are rejected with 401 Unauthorized."""
    r1 = await client.post("/api/v1/abdm/abha/init", json={"abha_address": "anon@abdm"})
    assert r1.status_code == 401

    r2 = await client.delete("/api/v1/abdm/abha/unlink")
    assert r2.status_code == 401
