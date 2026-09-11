"""Comprehensive End-to-End Test Suite for Milestone U-11: Doctor Human Approval Gate.

Tests the 10 mandatory criteria specified in Milestone U-11:
1. Draft appears in approval queue.
2. Doctor reviews draft details.
3. Doctor edits draft content (request_changes).
4. Doctor approves draft.
5. Content becomes finalized with audit log.
6. Doctor rejects draft with explicit rejection_reason.
7. Rejected content remains non-final (AMENDED / CANCELLED).
8. Unauthorized user cannot approve (patient & unassigned doctor blocked with 403).
9. Duplicate approval is rejected safely (returns 400).
10. Refresh/re-query preserves correct finalized status in DB.
"""

import pytest
import pytest_asyncio
from datetime import datetime
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Doctor,
    MedicalRecord,
    MedicalRecordStatus,
    Patient,
    Prescription,
    PrescriptionStatus,
    User,
    UserRole,
    AuditLog,
)
from app.services.auth.service import create_access_token, get_password_hash


@pytest_asyncio.fixture
async def assigned_doctor(db_session: AsyncSession):
    """Create the primary assigned doctor."""
    user = User(
        email="assigned.doc@u11test.com",
        hashed_password=get_password_hash("pass123"),
        full_name="Dr. Assigned Physician",
        role=UserRole.DOCTOR,
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()

    doctor = Doctor(
        user_id=user.user_id,
        license_number="LIC-U11-001",
        specialty="Internal Medicine",
        full_name="Dr. Assigned Physician",
        email="assigned.doc@u11test.com",
    )
    db_session.add(doctor)
    await db_session.commit()
    await db_session.refresh(user)
    await db_session.refresh(doctor)
    return user, doctor


@pytest_asyncio.fixture
async def unassigned_doctor(db_session: AsyncSession):
    """Create an unassigned doctor who does not own the records."""
    user = User(
        email="unassigned.doc@u11test.com",
        hashed_password=get_password_hash("pass123"),
        full_name="Dr. Unassigned Physician",
        role=UserRole.DOCTOR,
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()

    doctor = Doctor(
        user_id=user.user_id,
        license_number="LIC-U11-002",
        specialty="Pediatrics",
        full_name="Dr. Unassigned Physician",
        email="unassigned.doc@u11test.com",
    )
    db_session.add(doctor)
    await db_session.commit()
    await db_session.refresh(user)
    await db_session.refresh(doctor)
    return user, doctor


@pytest_asyncio.fixture
async def patient_user(db_session: AsyncSession):
    """Create a patient user with patient profile."""
    user = User(
        email="patient@u11test.com",
        hashed_password=get_password_hash("pass123"),
        full_name="John Q. Patient",
        role=UserRole.PATIENT,
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()

    patient = Patient(
        user_id=user.user_id,
        first_name="John",
        last_name="Patient",
        email="patient@u11test.com",
    )
    db_session.add(patient)
    await db_session.commit()
    await db_session.refresh(user)
    await db_session.refresh(patient)
    return user, patient


@pytest_asyncio.fixture
async def draft_medical_record(db_session: AsyncSession, assigned_doctor, patient_user):
    """Create an AI-drafted medical record in DRAFT status."""
    _, doc = assigned_doctor
    _, pat = patient_user

    record = MedicalRecord(
        patient_id=pat.patient_id,
        doctor_id=doc.doctor_id,
        status=MedicalRecordStatus.DRAFT,
        content={
            "subjective": "Patient reports mild persistent cough for 4 days.",
            "objective": "BP 120/80, HR 72, lungs clear to auscultation bilaterally.",
            "assessment": "Acute viral bronchitis, early stage.",
            "plan": "Hydration, rest, symptomatic relief with honey and lozenges.",
            "chief_complaint": "Persistent cough",
            "confidence": 0.94,
            "basis": "Clinical transcript ambient acoustic capture",
        },
    )
    db_session.add(record)
    await db_session.commit()
    await db_session.refresh(record)
    return record


@pytest_asyncio.fixture
async def draft_prescription(db_session: AsyncSession, assigned_doctor, patient_user, draft_medical_record):
    """Create an AI-drafted prescription in DRAFT status."""
    _, doc = assigned_doctor
    _, pat = patient_user

    prescription = Prescription(
        patient_id=pat.patient_id,
        doctor_id=doc.doctor_id,
        medical_record_id=draft_medical_record.record_id,
        status=PrescriptionStatus.DRAFT,
        medications=[
            {
                "medication_name": "Amoxicillin",
                "dosage": "500mg",
                "frequency": "Three times daily",
                "duration": "7 days",
                "route": "Oral",
                "confidence": 0.91,
                "warnings": ["Take with food"],
            }
        ],
        notes="AI-assisted prescription draft. Clinical sign-off required.",
    )
    db_session.add(prescription)
    await db_session.commit()
    await db_session.refresh(prescription)
    return prescription


# ---------------------------------------------------------------------------
# Test 1: Draft Appears in Approval Queue
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_01_draft_appears_in_approval_queue(
    async_client: AsyncClient,
    assigned_doctor,
    draft_medical_record,
    draft_prescription,
):
    doc_user, _ = assigned_doctor
    token = create_access_token(data={"sub": str(doc_user.user_id), "role": doc_user.role.value})

    response = await async_client.get(
        "/api/v1/approval/drafts",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 2
    mr_ids = [mr["record_id"] for mr in data["medical_records"]]
    rx_ids = [rx["prescription_id"] for rx in data["prescriptions"]]
    assert str(draft_medical_record.record_id) in mr_ids
    assert str(draft_prescription.prescription_id) in rx_ids


# ---------------------------------------------------------------------------
# Test 2: Doctor Reviews Draft Details
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_02_doctor_reviews_draft_details(
    async_client: AsyncClient,
    assigned_doctor,
    draft_medical_record,
    draft_prescription,
):
    doc_user, _ = assigned_doctor
    token = create_access_token(data={"sub": str(doc_user.user_id), "role": doc_user.role.value})

    # Review medical record details
    mr_res = await async_client.get(
        f"/api/v1/approval/medical-records/{draft_medical_record.record_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert mr_res.status_code == 200
    mr_data = mr_res.json()
    assert mr_data["status"] == "draft"
    assert mr_data["content"]["confidence"] == 0.94
    assert "viral bronchitis" in mr_data["content"]["assessment"]

    # Review prescription details
    rx_res = await async_client.get(
        f"/api/v1/approval/prescriptions/{draft_prescription.prescription_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert rx_res.status_code == 200
    rx_data = rx_res.json()
    assert rx_data["status"] == "draft"
    assert rx_data["medications"][0]["medication_name"] == "Amoxicillin"


# ---------------------------------------------------------------------------
# Test 3: Doctor Edits Draft Content (request_changes)
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_03_doctor_edits_draft_content(
    async_client: AsyncClient,
    assigned_doctor,
    draft_medical_record,
    draft_prescription,
):
    doc_user, _ = assigned_doctor
    token = create_access_token(data={"sub": str(doc_user.user_id), "role": doc_user.role.value})

    # Edit medical record
    edit_payload = {
        "action": "request_changes",
        "edited_content": {
            "assessment": "Acute viral bronchitis - physician adjusted assessment.",
            "plan": "Supportive therapy, increased fluids, follow-up if fever > 38.5C.",
        },
        "reviewer_notes": "Refined diagnosis and home care guidance.",
    }
    mr_res = await async_client.post(
        f"/api/v1/approval/medical-records/{draft_medical_record.record_id}/review",
        json=edit_payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert mr_res.status_code == 200
    mr_data = mr_res.json()
    assert mr_data["status"] == "draft"  # Remains draft while requesting changes

    # Edit prescription medications
    rx_edit_payload = {
        "action": "request_changes",
        "edited_medications": [
            {
                "medication_name": "Amoxicillin",
                "dosage": "875mg",
                "frequency": "Twice daily",
                "duration": "10 days",
                "route": "Oral",
            }
        ],
        "reviewer_notes": "Upgraded dose to 875mg BID.",
    }
    rx_res = await async_client.post(
        f"/api/v1/approval/prescriptions/{draft_prescription.prescription_id}/review",
        json=rx_edit_payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert rx_res.status_code == 200
    rx_data = rx_res.json()
    assert rx_data["status"] == "draft"


# ---------------------------------------------------------------------------
# Test 4: Doctor Approves Draft
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_04_doctor_approves_draft(
    async_client: AsyncClient,
    db_session: AsyncSession,
    assigned_doctor,
    draft_medical_record,
    draft_prescription,
):
    doc_user, doc = assigned_doctor
    token = create_access_token(data={"sub": str(doc_user.user_id), "role": doc_user.role.value})

    # Approve medical record
    approve_mr = {
        "action": "approve",
        "reviewer_notes": "Reviewed and clinically attested by attending physician.",
    }
    mr_res = await async_client.post(
        f"/api/v1/approval/medical-records/{draft_medical_record.record_id}/review",
        json=approve_mr,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert mr_res.status_code == 200
    mr_data = mr_res.json()
    assert mr_data["status"] == "finalized"
    assert mr_data["action"] == "approve"
    assert mr_data["finalized_at"] is not None

    # Verify DB entity finalized_at
    await db_session.refresh(draft_medical_record)
    assert draft_medical_record.status == MedicalRecordStatus.FINALIZED
    assert draft_medical_record.finalized_at is not None

    # Approve prescription
    approve_rx = {
        "action": "approve",
        "reviewer_notes": "Signed and cleared for dispensary.",
    }
    rx_res = await async_client.post(
        f"/api/v1/approval/prescriptions/{draft_prescription.prescription_id}/review",
        json=approve_rx,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert rx_res.status_code == 200
    rx_data = rx_res.json()
    assert rx_data["status"] == "finalized"
    assert rx_data["action"] == "approve"
    assert rx_data["finalized_at"] is not None

    # Verify DB entity finalized_at
    await db_session.refresh(draft_prescription)
    assert draft_prescription.status == PrescriptionStatus.FINALIZED
    assert draft_prescription.finalized_at is not None


# ---------------------------------------------------------------------------
# Test 5: Content Becomes Finalized with Audit Log
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_05_content_finalized_with_audit_log(
    async_client: AsyncClient,
    db_session: AsyncSession,
    assigned_doctor,
    draft_medical_record,
    draft_prescription,
):
    doc_user, _ = assigned_doctor
    token = create_access_token(data={"sub": str(doc_user.user_id), "role": doc_user.role.value})

    await async_client.post(
        f"/api/v1/approval/medical-records/{draft_medical_record.record_id}/review",
        json={"action": "approve", "reviewer_notes": "Physician attestation signed."},
        headers={"Authorization": f"Bearer {token}"},
    )

    await async_client.post(
        f"/api/v1/approval/prescriptions/{draft_prescription.prescription_id}/review",
        json={"action": "approve", "reviewer_notes": "Prescription signed."},
        headers={"Authorization": f"Bearer {token}"},
    )

    # Check AuditLog table for both events
    audit_res = await db_session.execute(
        select(AuditLog).where(
            AuditLog.resource_id.in_([draft_medical_record.record_id, draft_prescription.prescription_id])
        )
    )
    logs = audit_res.scalars().all()
    actions = [log.action for log in logs]
    assert "MEDICAL_RECORD_APPROVED" in actions
    assert "PRESCRIPTION_APPROVED" in actions


# ---------------------------------------------------------------------------
# Test 6: Doctor Rejects Draft with Explicit Rejection Reason
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_06_doctor_rejects_draft_with_explicit_reason(
    async_client: AsyncClient,
    assigned_doctor,
    draft_medical_record,
    draft_prescription,
):
    doc_user, _ = assigned_doctor
    token = create_access_token(data={"sub": str(doc_user.user_id), "role": doc_user.role.value})

    mr_reject_payload = {
        "action": "reject",
        "rejection_reason": "Inaccurate symptom transcription; patient denied shortness of breath.",
        "reviewer_notes": "Please re-record ambient audio or enter manually.",
    }
    mr_res = await async_client.post(
        f"/api/v1/approval/medical-records/{draft_medical_record.record_id}/review",
        json=mr_reject_payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert mr_res.status_code == 200
    mr_data = mr_res.json()
    assert mr_data["status"] == "amended"
    assert mr_data["rejection_reason"] == mr_reject_payload["rejection_reason"]

    rx_reject_payload = {
        "action": "reject",
        "rejection_reason": "Severe reported penicillin allergy precludes amoxicillin.",
        "reviewer_notes": "Switching to azithromycin.",
    }
    rx_res = await async_client.post(
        f"/api/v1/approval/prescriptions/{draft_prescription.prescription_id}/review",
        json=rx_reject_payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert rx_res.status_code == 200
    rx_data = rx_res.json()
    assert rx_data["status"] == "cancelled"
    assert rx_data["rejection_reason"] == rx_reject_payload["rejection_reason"]


# ---------------------------------------------------------------------------
# Test 7: Rejected Content Remains Non-Final
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_07_rejected_content_remains_non_final(
    async_client: AsyncClient,
    db_session: AsyncSession,
    assigned_doctor,
    draft_medical_record,
    draft_prescription,
):
    doc_user, _ = assigned_doctor
    token = create_access_token(data={"sub": str(doc_user.user_id), "role": doc_user.role.value})

    # Reject both
    await async_client.post(
        f"/api/v1/approval/medical-records/{draft_medical_record.record_id}/review",
        json={"action": "reject", "rejection_reason": "Clinical discrepancy"},
        headers={"Authorization": f"Bearer {token}"},
    )
    await async_client.post(
        f"/api/v1/approval/prescriptions/{draft_prescription.prescription_id}/review",
        json={"action": "reject", "rejection_reason": "Dosage contraindication"},
        headers={"Authorization": f"Bearer {token}"},
    )

    # Re-fetch from DB
    await db_session.refresh(draft_medical_record)
    await db_session.refresh(draft_prescription)

    # Must NOT be finalized
    assert draft_medical_record.status != MedicalRecordStatus.FINALIZED
    assert draft_medical_record.status == MedicalRecordStatus.AMENDED
    assert draft_medical_record.content.get("rejection_reason") == "Clinical discrepancy"

    assert draft_prescription.status != PrescriptionStatus.FINALIZED
    assert draft_prescription.status == PrescriptionStatus.CANCELLED
    assert "[Rejection Reason]: Dosage contraindication" in (draft_prescription.notes or "")


# ---------------------------------------------------------------------------
# Test 8: Unauthorized User Cannot Approve (Patient & Unassigned Doctor)
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_08_unauthorized_user_cannot_approve(
    async_client: AsyncClient,
    patient_user,
    unassigned_doctor,
    draft_medical_record,
    draft_prescription,
):
    pat_user, _ = patient_user
    pat_token = create_access_token(data={"sub": str(pat_user.user_id), "role": pat_user.role.value})

    unassigned_user, _ = unassigned_doctor
    unassigned_token = create_access_token(
        data={"sub": str(unassigned_user.user_id), "role": unassigned_user.role.value}
    )

    # Patient cannot approve medical record
    pat_mr = await async_client.post(
        f"/api/v1/approval/medical-records/{draft_medical_record.record_id}/review",
        json={"action": "approve"},
        headers={"Authorization": f"Bearer {pat_token}"},
    )
    assert pat_mr.status_code == 403

    # Patient cannot approve prescription
    pat_rx = await async_client.post(
        f"/api/v1/approval/prescriptions/{draft_prescription.prescription_id}/review",
        json={"action": "approve"},
        headers={"Authorization": f"Bearer {pat_token}"},
    )
    assert pat_rx.status_code == 403

    # Unassigned doctor cannot approve medical record
    unassigned_mr = await async_client.post(
        f"/api/v1/approval/medical-records/{draft_medical_record.record_id}/review",
        json={"action": "approve"},
        headers={"Authorization": f"Bearer {unassigned_token}"},
    )
    assert unassigned_mr.status_code == 403

    # Unassigned doctor cannot approve prescription
    unassigned_rx = await async_client.post(
        f"/api/v1/approval/prescriptions/{draft_prescription.prescription_id}/review",
        json={"action": "approve"},
        headers={"Authorization": f"Bearer {unassigned_token}"},
    )
    assert unassigned_rx.status_code == 403


# ---------------------------------------------------------------------------
# Test 9: Duplicate Approval is Rejected Safely (Returns 400)
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_09_duplicate_approval_is_rejected_safely(
    async_client: AsyncClient,
    assigned_doctor,
    draft_medical_record,
    draft_prescription,
):
    doc_user, _ = assigned_doctor
    token = create_access_token(data={"sub": str(doc_user.user_id), "role": doc_user.role.value})

    # First approval succeeds
    mr_first = await async_client.post(
        f"/api/v1/approval/medical-records/{draft_medical_record.record_id}/review",
        json={"action": "approve"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert mr_first.status_code == 200

    rx_first = await async_client.post(
        f"/api/v1/approval/prescriptions/{draft_prescription.prescription_id}/review",
        json={"action": "approve"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert rx_first.status_code == 200

    # Duplicate approval attempt must fail with 400 Bad Request
    mr_duplicate = await async_client.post(
        f"/api/v1/approval/medical-records/{draft_medical_record.record_id}/review",
        json={"action": "approve"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert mr_duplicate.status_code == 400
    assert "Already finalized" in mr_duplicate.json()["detail"]

    rx_duplicate = await async_client.post(
        f"/api/v1/approval/prescriptions/{draft_prescription.prescription_id}/review",
        json={"action": "approve"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert rx_duplicate.status_code == 400
    assert "Already finalized" in rx_duplicate.json()["detail"]


# ---------------------------------------------------------------------------
# Test 10: Refresh Preserves Correct Finalized Status
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_10_refresh_preserves_correct_status(
    async_client: AsyncClient,
    assigned_doctor,
    draft_medical_record,
    draft_prescription,
):
    doc_user, _ = assigned_doctor
    token = create_access_token(data={"sub": str(doc_user.user_id), "role": doc_user.role.value})

    # Approve both
    await async_client.post(
        f"/api/v1/approval/medical-records/{draft_medical_record.record_id}/review",
        json={"action": "approve", "reviewer_notes": "Clinical sign-off completed."},
        headers={"Authorization": f"Bearer {token}"},
    )
    await async_client.post(
        f"/api/v1/approval/prescriptions/{draft_prescription.prescription_id}/review",
        json={"action": "approve", "reviewer_notes": "Approved for dispensing."},
        headers={"Authorization": f"Bearer {token}"},
    )

    # Refresh / re-fetch via approval detail endpoints
    mr_refreshed = await async_client.get(
        f"/api/v1/approval/medical-records/{draft_medical_record.record_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert mr_refreshed.status_code == 200
    assert mr_refreshed.json()["status"] == "finalized"
    assert mr_refreshed.json()["content"]["approved_at"] is not None

    rx_refreshed = await async_client.get(
        f"/api/v1/approval/prescriptions/{draft_prescription.prescription_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert rx_refreshed.status_code == 200
    assert rx_refreshed.json()["status"] == "finalized"
    assert rx_refreshed.json()["finalized_at"] is not None

    # Drafts queue must no longer list either finalized item
    drafts_list = await async_client.get(
        "/api/v1/approval/drafts",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert drafts_list.status_code == 200
    drafts_data = drafts_list.json()
    active_mr_ids = [mr["record_id"] for mr in drafts_data["medical_records"]]
    active_rx_ids = [rx["prescription_id"] for rx in drafts_data["prescriptions"]]
    assert str(draft_medical_record.record_id) not in active_mr_ids
    assert str(draft_prescription.prescription_id) not in active_rx_ids
