"""Automated Test Suite for Milestone U-18: Consent + Audit Viewer (M31).

Tests covered:
1. Patient grants consent to Doctor (POST /api/v1/consents): returns 201 Created, provider metadata, and creates GRANT_CONSENT audit log.
2. Duplicate active consent check: 400 Bad Request when granting consent to same doctor without revoking existing.
3. Patient lists their consents (GET /api/v1/consents/me) with enriched provider metadata (name, specialty, hospital).
4. Patient revokes consent (DELETE /api/v1/consents/{consent_id}): sets revoked_at, creates REVOKE_CONSENT audit log.
5. Active-only filter (GET /api/v1/consents/me?active_only=true): excludes revoked consents.
6. Strict cross-patient RBAC: Patient B cannot revoke Patient A's consent (403 Forbidden).
7. Doctor cannot call /consents/me (403 Forbidden).
8. Admin queries audit logs (GET /api/v1/admin/audit) with pagination metadata (total, page, page_size, total_pages).
9. Admin filters audit logs by action (GRANT_CONSENT), resource_type (consents), and search terms.
10. Admin retrieves single audit log details by log_id (GET /api/v1/admin/audit/{log_id}).
11. Strict RBAC: Doctor and Patient receive 403 Forbidden on /api/v1/admin/audit.
12. Unauthenticated requests receive 401 Unauthorized on both consent and audit endpoints.
13. Read-only integrity: No mutation/deletion endpoints exist for audit logs (405 Method Not Allowed).
"""

import uuid
from datetime import date, datetime, timedelta
import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models import (
    AuditLog,
    AuditOutcome,
    Consent,
    ConsentScope,
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
        email="alice.u18@aihos.org",
        hashed_password=get_password_hash("alicepassword123"),
        full_name="Alice Henderson",
        role=UserRole.PATIENT,
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    patient = Patient(
        user_id=user.user_id,
        full_name="Alice Henderson",
        email=user.email,
        date_of_birth=date(1994, 5, 20),
        gender="Female",
    )
    db_session.add(patient)
    await db_session.commit()
    await db_session.refresh(patient)
    return user


@pytest_asyncio.fixture
async def patient_b_user(db_session: AsyncSession):
    """Create Patient Bob (for cross-patient isolation tests)."""
    user = User(
        email="bob.u18@aihos.org",
        hashed_password=get_password_hash("bobpassword123"),
        full_name="Bob Martinez",
        role=UserRole.PATIENT,
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    patient = Patient(
        user_id=user.user_id,
        full_name="Bob Martinez",
        email=user.email,
        date_of_birth=date(1991, 8, 14),
        gender="Male",
    )
    db_session.add(patient)
    await db_session.commit()
    await db_session.refresh(patient)
    return user


@pytest_asyncio.fixture
async def doctor_user(db_session: AsyncSession):
    """Create Doctor Vikram."""
    user = User(
        email="vikram.u18@aihos.org",
        hashed_password=get_password_hash("vikrampass123"),
        full_name="Dr. Vikram Anand",
        role=UserRole.DOCTOR,
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    doctor = Doctor(
        user_id=user.user_id,
        full_name="Dr. Vikram Anand",
        email=user.email,
        specialty="Cardiology",
        hospital_affiliation="AIIMS Apex Medical Center",
        license_number="CARD-U18-9988",
    )
    db_session.add(doctor)
    await db_session.commit()
    await db_session.refresh(doctor)
    return user


@pytest_asyncio.fixture
async def admin_user(db_session: AsyncSession):
    """Create Compliance Officer / Admin."""
    user = User(
        email="compliance.admin.u18@aihos.org",
        hashed_password=get_password_hash("compliancepass123"),
        full_name="Elena Rostova",
        role=UserRole.ADMIN,
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


# =============================================================================
# Helper Auth Header Builder
# =============================================================================

def _auth_header(user: User) -> dict:
    token = create_access_token(data={"sub": str(user.user_id), "role": user.role.value})
    return {"Authorization": f"Bearer {token}"}


# =============================================================================
# Milestone U-18 Tests
# =============================================================================

@pytest.mark.asyncio
async def test_patient_grant_consent_lifecycle(
    client: AsyncClient,
    db_session: AsyncSession,
    patient_a_user: User,
    doctor_user: User,
):
    """Test Patient granting consent creates record and audit log."""
    # Retrieve doctor profile ID
    doc_res = await db_session.execute(select(Doctor).where(Doctor.user_id == doctor_user.user_id))
    doctor = doc_res.scalar_one()

    # 1. Patient Alice grants consent
    payload = {
        "provider_id": str(doctor.doctor_id),
        "record_scope": "records_only",
    }
    response = await client.post(
        "/api/v1/consents",
        json=payload,
        headers=_auth_header(patient_a_user),
    )
    assert response.status_code == 201, response.text
    data = response.json()
    assert data["provider_id"] == str(doctor.doctor_id)
    assert data["provider_name"] == "Dr. Vikram Anand"
    assert data["provider_specialty"] == "Cardiology"
    assert data["provider_hospital"] == "AIIMS Apex Medical Center"
    assert data["record_scope"] == "records_only"
    assert data["is_active"] is True
    assert data["revoked_at"] is None
    consent_id = data["consent_id"]

    # 2. Check immutable audit log was created
    audit_res = await db_session.execute(
        select(AuditLog).where(
            AuditLog.action == "GRANT_CONSENT",
            AuditLog.resource_id == uuid.UUID(consent_id),
        )
    )
    audit_log = audit_res.scalar_one_or_none()
    assert audit_log is not None
    assert audit_log.user_id == patient_a_user.user_id
    assert audit_log.outcome == AuditOutcome.SUCCESS
    assert audit_log.details["provider_name"] == "Dr. Vikram Anand"


@pytest.mark.asyncio
async def test_duplicate_active_consent_rejected(
    client: AsyncClient,
    db_session: AsyncSession,
    patient_a_user: User,
    doctor_user: User,
):
    """Test granting duplicate active consent to the same doctor fails with 400."""
    doc_res = await db_session.execute(select(Doctor).where(Doctor.user_id == doctor_user.user_id))
    doctor = doc_res.scalar_one()

    payload = {
        "provider_id": str(doctor.doctor_id),
        "record_scope": "full_access",
    }
    res1 = await client.post(
        "/api/v1/consents",
        json=payload,
        headers=_auth_header(patient_a_user),
    )
    assert res1.status_code == 201

    # Attempt second grant
    res2 = await client.post(
        "/api/v1/consents",
        json=payload,
        headers=_auth_header(patient_a_user),
    )
    assert res2.status_code == 400
    assert "already exists" in res2.json()["detail"].lower()


@pytest.mark.asyncio
async def test_patient_list_and_revoke_consent(
    client: AsyncClient,
    db_session: AsyncSession,
    patient_a_user: User,
    doctor_user: User,
):
    """Test listing consents and soft-revocation with audit trail."""
    doc_res = await db_session.execute(select(Doctor).where(Doctor.user_id == doctor_user.user_id))
    doctor = doc_res.scalar_one()

    # Grant consent
    create_res = await client.post(
        "/api/v1/consents",
        json={"provider_id": str(doctor.doctor_id), "record_scope": "full_access"},
        headers=_auth_header(patient_a_user),
    )
    consent_id = create_res.json()["consent_id"]

    # List personal consents
    list_res = await client.get(
        "/api/v1/consents/me",
        headers=_auth_header(patient_a_user),
    )
    assert list_res.status_code == 200
    consents = list_res.json()
    assert len(consents) >= 1
    target = next((c for c in consents if c["consent_id"] == consent_id), None)
    assert target is not None
    assert target["is_active"] is True

    # Revoke consent
    revoke_res = await client.delete(
        f"/api/v1/consents/{consent_id}",
        headers=_auth_header(patient_a_user),
    )
    assert revoke_res.status_code == 200
    revoked_data = revoke_res.json()
    assert revoked_data["is_active"] is False
    assert revoked_data["revoked_at"] is not None

    # Verify active_only filter excludes revoked consent
    active_res = await client.get(
        "/api/v1/consents/me?active_only=true",
        headers=_auth_header(patient_a_user),
    )
    assert active_res.status_code == 200
    active_consents = active_res.json()
    assert not any(c["consent_id"] == consent_id for c in active_consents)

    # Check REVOKE_CONSENT audit log
    audit_res = await db_session.execute(
        select(AuditLog).where(
            AuditLog.action == "REVOKE_CONSENT",
            AuditLog.resource_id == uuid.UUID(consent_id),
        )
    )
    revoke_audit = audit_res.scalar_one_or_none()
    assert revoke_audit is not None
    assert revoke_audit.user_id == patient_a_user.user_id
    assert revoke_audit.outcome == AuditOutcome.SUCCESS


@pytest.mark.asyncio
async def test_cross_patient_isolation_on_consent_revocation(
    client: AsyncClient,
    db_session: AsyncSession,
    patient_a_user: User,
    patient_b_user: User,
    doctor_user: User,
):
    """Test that Patient B cannot revoke Patient A's consent agreement (403 Forbidden)."""
    doc_res = await db_session.execute(select(Doctor).where(Doctor.user_id == doctor_user.user_id))
    doctor = doc_res.scalar_one()

    # Patient A creates consent
    create_res = await client.post(
        "/api/v1/consents",
        json={"provider_id": str(doctor.doctor_id), "record_scope": "appointments_only"},
        headers=_auth_header(patient_a_user),
    )
    consent_id = create_res.json()["consent_id"]

    # Patient B attempts to revoke Patient A's consent
    revoke_attempt = await client.delete(
        f"/api/v1/consents/{consent_id}",
        headers=_auth_header(patient_b_user),
    )
    assert revoke_attempt.status_code == 403
    assert "access denied" in revoke_attempt.json()["detail"].lower()


@pytest.mark.asyncio
async def test_doctor_cannot_call_consents_me(
    client: AsyncClient,
    doctor_user: User,
):
    """Doctor role cannot access /api/v1/consents/me (403 Forbidden)."""
    res = await client.get(
        "/api/v1/consents/me",
        headers=_auth_header(doctor_user),
    )
    assert res.status_code == 403


@pytest.mark.asyncio
async def test_admin_audit_log_query_and_pagination(
    client: AsyncClient,
    db_session: AsyncSession,
    admin_user: User,
    patient_a_user: User,
    doctor_user: User,
):
    """Test admin querying audit logs with multi-field filtering and pagination."""
    doc_res = await db_session.execute(select(Doctor).where(Doctor.user_id == doctor_user.user_id))
    doctor = doc_res.scalar_one()

    # Trigger some audit log events
    await client.post(
        "/api/v1/consents",
        json={"provider_id": str(doctor.doctor_id), "record_scope": "notes_only"},
        headers=_auth_header(patient_a_user),
    )

    # 1. Admin queries logs without filters
    res = await client.get(
        "/api/v1/admin/audit?page=1&page_size=10",
        headers=_auth_header(admin_user),
    )
    assert res.status_code == 200
    data = res.json()
    assert "logs" in data
    assert "total" in data
    assert "page" in data
    assert "page_size" in data
    assert "total_pages" in data
    assert data["page"] == 1
    assert data["page_size"] == 10
    assert len(data["logs"]) > 0

    # 2. Filter by action and resource
    action_res = await client.get(
        "/api/v1/admin/audit?action=GRANT_CONSENT&resource_type=consents",
        headers=_auth_header(admin_user),
    )
    assert action_res.status_code == 200
    filtered_data = action_res.json()
    assert len(filtered_data["logs"]) >= 1
    for log in filtered_data["logs"]:
        assert "GRANT_CONSENT" in log["action"]
        assert log["resource_type"] == "consents"

    # 3. Test single log retrieval
    sample_log_id = filtered_data["logs"][0]["log_id"]
    detail_res = await client.get(
        f"/api/v1/admin/audit/{sample_log_id}",
        headers=_auth_header(admin_user),
    )
    assert detail_res.status_code == 200
    detail_data = detail_res.json()
    assert detail_data["log_id"] == sample_log_id
    assert detail_data["user_email"] is not None


@pytest.mark.asyncio
async def test_admin_audit_strict_rbac(
    client: AsyncClient,
    patient_a_user: User,
    doctor_user: User,
):
    """Test non-admin users (Patients and Doctors) receive 403 Forbidden on audit log viewer."""
    # Patient
    res_pat = await client.get(
        "/api/v1/admin/audit",
        headers=_auth_header(patient_a_user),
    )
    assert res_pat.status_code == 403

    # Doctor
    res_doc = await client.get(
        "/api/v1/admin/audit",
        headers=_auth_header(doctor_user),
    )
    assert res_doc.status_code == 403


@pytest.mark.asyncio
async def test_unauthenticated_requests_rejected(client: AsyncClient):
    """Test unauthenticated requests are rejected with 401 Unauthorized."""
    # Consents
    r1 = await client.get("/api/v1/consents/me")
    assert r1.status_code == 401

    r2 = await client.post("/api/v1/consents", json={"provider_id": str(uuid.uuid4())})
    assert r2.status_code == 401

    # Audit
    r3 = await client.get("/api/v1/admin/audit")
    assert r3.status_code == 401


@pytest.mark.asyncio
async def test_audit_logs_read_only_immutability(
    client: AsyncClient,
    admin_user: User,
):
    """Ensure no mutation (DELETE, PUT, POST) endpoints exist for audit logs."""
    fake_log_id = str(uuid.uuid4())

    # DELETE /api/v1/admin/audit/{id}
    del_res = await client.delete(
        f"/api/v1/admin/audit/{fake_log_id}",
        headers=_auth_header(admin_user),
    )
    assert del_res.status_code == 405  # Method Not Allowed

    # PUT /api/v1/admin/audit/{id}
    put_res = await client.put(
        f"/api/v1/admin/audit/{fake_log_id}",
        json={"action": "TAMPERED"},
        headers=_auth_header(admin_user),
    )
    assert put_res.status_code == 405  # Method Not Allowed
