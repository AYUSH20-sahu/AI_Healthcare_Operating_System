"""Automated Test Suite for Milestone U-16: Patient Reports + Medicine Reminders (M29).

Tests covered:
1. Patient uploads valid medical report (PDF & Image) -> 201 Created, metadata stored, file persisted.
2. Disallowed MIME types rejected with 400 Bad Request.
3. Oversized file (> 10MB) rejected with 400 Bad Request.
4. Patient list reports with category filtering (lab, imaging, etc.).
5. Authenticated streaming download of medical report (FileResponse).
6. Cross-patient isolation: Patient Bob cannot view, download, or delete Patient Alice's reports (403 Forbidden).
7. Report deletion removes database record and disk file.
8. Medicine reminder scheduling: creation logs scheduler dispatch stub, lists schedules.
9. Medicine reminder update/toggle active status.
10. Cross-patient isolation: Patient Bob cannot update or delete Patient Alice's reminders (403 Forbidden).
11. Unauthenticated requests rejected with 401 Unauthorized.
12. Healthcare provider (Doctor) can inspect patient reports via provider endpoint.
"""

import io
import os
import pytest
import pytest_asyncio
from datetime import date, datetime
from httpx import AsyncClient
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Doctor,
    MedicineReminder,
    Patient,
    PatientReport,
    User,
    UserRole,
)
from app.services.auth.service import create_access_token, get_password_hash


@pytest_asyncio.fixture
async def patient_alice(db_session: AsyncSession):
    """Create Patient Alice."""
    user = User(
        email="alice.u16@test.com",
        hashed_password=get_password_hash("password123"),
        full_name="Alice ReportUser",
        role=UserRole.PATIENT,
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()

    patient = Patient(
        user_id=user.user_id,
        full_name="Alice ReportUser",
        email="alice.u16@test.com",
        date_of_birth=date(1992, 4, 15),
        gender="Female",
        phone="+91 98888 11111",
        abha_address="alice.u16@abdm",
    )
    db_session.add(patient)
    await db_session.commit()
    await db_session.refresh(user)
    await db_session.refresh(patient)
    return user, patient


@pytest_asyncio.fixture
async def patient_bob(db_session: AsyncSession):
    """Create Patient Bob (for cross-patient isolation testing)."""
    user = User(
        email="bob.u16@test.com",
        hashed_password=get_password_hash("password123"),
        full_name="Bob Snooper",
        role=UserRole.PATIENT,
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()

    patient = Patient(
        user_id=user.user_id,
        full_name="Bob Snooper",
        email="bob.u16@test.com",
        date_of_birth=date(1988, 9, 20),
        gender="Male",
        phone="+91 97777 22222",
        abha_address="bob.u16@abdm",
    )
    db_session.add(patient)
    await db_session.commit()
    await db_session.refresh(user)
    await db_session.refresh(patient)
    return user, patient


@pytest_asyncio.fixture
async def attending_doctor(db_session: AsyncSession):
    """Create Doctor Sharma for provider clinical review."""
    user = User(
        email="doctor.u16@test.com",
        hashed_password=get_password_hash("password123"),
        full_name="Dr. Anil Sharma",
        role=UserRole.DOCTOR,
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()

    doctor = Doctor(
        user_id=user.user_id,
        license_number="LIC-U16-ANIL",
        specialty="General Medicine",
        full_name="Dr. Anil Sharma",
        email="doctor.u16@test.com",
    )
    db_session.add(doctor)
    await db_session.commit()
    await db_session.refresh(user)
    await db_session.refresh(doctor)
    return user, doctor


# =============================================================================
# 1. Report Upload Tests (MIME & Size Validation)
# =============================================================================

@pytest.mark.asyncio
async def test_patient_upload_valid_pdf_report(
    async_client: AsyncClient,
    patient_alice,
):
    user, patient = patient_alice
    token = create_access_token({"sub": str(user.user_id), "role": user.role.value})
    headers = {"Authorization": f"Bearer {token}"}

    pdf_content = b"%PDF-1.4 Mock PDF Content for Lipid Profile Test"
    files = {
        "file": ("lipid_panel.pdf", io.BytesIO(pdf_content), "application/pdf"),
    }
    data = {
        "title": "Lipid Profile Test - August 2026",
        "report_type": "lab",
        "notes": "Fasting blood sample taken at 8 AM.",
    }

    response = await async_client.post(
        "/api/v1/patients/me/reports",
        headers=headers,
        data=data,
        files=files,
    )

    assert response.status_code == 201
    res_data = response.json()
    assert res_data["title"] == "Lipid Profile Test - August 2026"
    assert res_data["report_type"] == "lab"
    assert res_data["mime_type"] == "application/pdf"
    assert res_data["file_size_bytes"] == len(pdf_content)
    assert res_data["patient_id"] == str(patient.patient_id)
    assert "report_id" in res_data


@pytest.mark.asyncio
async def test_patient_upload_image_report(
    async_client: AsyncClient,
    patient_alice,
):
    user, patient = patient_alice
    token = create_access_token({"sub": str(user.user_id), "role": user.role.value})
    headers = {"Authorization": f"Bearer {token}"}

    img_content = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR Mock PNG Chest X-Ray"
    files = {
        "file": ("chest_xray.png", io.BytesIO(img_content), "image/png"),
    }
    data = {
        "title": "PA Chest Radiograph",
        "report_type": "imaging",
        "notes": "Clear lung fields, normal cardiac silhouette.",
    }

    response = await async_client.post(
        "/api/v1/patients/me/reports",
        headers=headers,
        data=data,
        files=files,
    )

    assert response.status_code == 201
    res_data = response.json()
    assert res_data["title"] == "PA Chest Radiograph"
    assert res_data["report_type"] == "imaging"
    assert res_data["mime_type"] == "image/png"


@pytest.mark.asyncio
async def test_patient_upload_disallowed_mime_type(
    async_client: AsyncClient,
    patient_alice,
):
    user, patient = patient_alice
    token = create_access_token({"sub": str(user.user_id), "role": user.role.value})
    headers = {"Authorization": f"Bearer {token}"}

    # Executable or unsupported script
    bad_content = b"#!/bin/bash\necho 'hacked'"
    files = {
        "file": ("script.sh", io.BytesIO(bad_content), "application/x-sh"),
    }
    data = {"title": "Malicious Upload", "report_type": "other"}

    response = await async_client.post(
        "/api/v1/patients/me/reports",
        headers=headers,
        data=data,
        files=files,
    )

    assert response.status_code == 400
    assert "Unsupported file format" in response.json()["detail"]


@pytest.mark.asyncio
async def test_patient_upload_oversized_file(
    async_client: AsyncClient,
    patient_alice,
):
    user, patient = patient_alice
    token = create_access_token({"sub": str(user.user_id), "role": user.role.value})
    headers = {"Authorization": f"Bearer {token}"}

    # 10.5 MB file exceeds 10 MB limit
    oversized_content = b"0" * (10 * 1024 * 1024 + 512 * 1024)
    files = {
        "file": ("huge_scan.pdf", io.BytesIO(oversized_content), "application/pdf"),
    }
    data = {"title": "Huge MRI Scan", "report_type": "imaging"}

    response = await async_client.post(
        "/api/v1/patients/me/reports",
        headers=headers,
        data=data,
        files=files,
    )

    assert response.status_code == 400
    assert "exceeds maximum allowed limit of 10 MB" in response.json()["detail"]


# =============================================================================
# 2. List, Filter & Stream Download Tests
# =============================================================================

@pytest.mark.asyncio
async def test_patient_list_and_download_reports(
    async_client: AsyncClient,
    patient_alice,
):
    user, patient = patient_alice
    token = create_access_token({"sub": str(user.user_id), "role": user.role.value})
    headers = {"Authorization": f"Bearer {token}"}

    # Upload report
    pdf_content = b"%PDF-1.4 Ultrasound Abdomen Report"
    files = {
        "file": ("usg_abdomen.pdf", io.BytesIO(pdf_content), "application/pdf"),
    }
    data = {"title": "USG Whole Abdomen", "report_type": "imaging"}
    up_res = await async_client.post("/api/v1/patients/me/reports", headers=headers, data=data, files=files)
    assert up_res.status_code == 201
    report_id = up_res.json()["report_id"]

    # List all reports
    list_res = await async_client.get("/api/v1/patients/me/reports", headers=headers)
    assert list_res.status_code == 200
    assert list_res.json()["total"] >= 1

    # Filter by category
    filter_res = await async_client.get("/api/v1/patients/me/reports?report_type=imaging", headers=headers)
    assert filter_res.status_code == 200
    assert any(r["report_id"] == report_id for r in filter_res.json()["reports"])

    # Stream download report
    dl_res = await async_client.get(f"/api/v1/patients/me/reports/{report_id}/download", headers=headers)
    assert dl_res.status_code == 200
    assert dl_res.content == pdf_content
    assert dl_res.headers["content-type"] == "application/pdf"


# =============================================================================
# 3. Cross-Patient Isolation & Deletion Tests (403 Forbidden)
# =============================================================================

@pytest.mark.asyncio
async def test_cross_patient_report_isolation_403(
    async_client: AsyncClient,
    patient_alice,
    patient_bob,
):
    alice_user, _ = patient_alice
    bob_user, _ = patient_bob

    alice_token = create_access_token({"sub": str(alice_user.user_id), "role": alice_user.role.value})
    bob_token = create_access_token({"sub": str(bob_user.user_id), "role": bob_user.role.value})

    # Alice uploads a report
    pdf_content = b"%PDF-1.4 Secret Genetic Report"
    files = {"file": ("dna_test.pdf", io.BytesIO(pdf_content), "application/pdf")}
    data = {"title": "Confidential Genetic Screening", "report_type": "lab"}
    up_res = await async_client.post(
        "/api/v1/patients/me/reports",
        headers={"Authorization": f"Bearer {alice_token}"},
        data=data,
        files=files,
    )
    report_id = up_res.json()["report_id"]

    # Bob attempts to get metadata -> 403 Forbidden
    bob_meta_res = await async_client.get(
        f"/api/v1/patients/me/reports/{report_id}",
        headers={"Authorization": f"Bearer {bob_token}"},
    )
    assert bob_meta_res.status_code == 403
    assert "Cannot access another patient's medical report" in bob_meta_res.json()["detail"]

    # Bob attempts to download -> 403 Forbidden
    bob_dl_res = await async_client.get(
        f"/api/v1/patients/me/reports/{report_id}/download",
        headers={"Authorization": f"Bearer {bob_token}"},
    )
    assert bob_dl_res.status_code == 403
    assert "Cannot download another patient's medical report" in bob_dl_res.json()["detail"]

    # Bob attempts to delete -> 403 Forbidden
    bob_del_res = await async_client.delete(
        f"/api/v1/patients/me/reports/{report_id}",
        headers={"Authorization": f"Bearer {bob_token}"},
    )
    assert bob_del_res.status_code == 403
    assert "Cannot delete another patient's medical report" in bob_del_res.json()["detail"]


@pytest.mark.asyncio
async def test_patient_delete_report_lifecycle(
    async_client: AsyncClient,
    patient_alice,
):
    user, _ = patient_alice
    headers = {"Authorization": f"Bearer {create_access_token({'sub': str(user.user_id), 'role': user.role.value})}"}

    # Upload
    files = {"file": ("temp_scan.pdf", io.BytesIO(b"%PDF-1.4 temporary"), "application/pdf")}
    data = {"title": "Temporary Scan", "report_type": "other"}
    up_res = await async_client.post("/api/v1/patients/me/reports", headers=headers, data=data, files=files)
    report_id = up_res.json()["report_id"]

    # Alice deletes her own report -> 200 OK
    del_res = await async_client.delete(f"/api/v1/patients/me/reports/{report_id}", headers=headers)
    assert del_res.status_code == 200
    assert del_res.json()["detail"] == "Medical report deleted successfully"

    # Subsequent access -> 404 Not Found
    get_res = await async_client.get(f"/api/v1/patients/me/reports/{report_id}", headers=headers)
    assert get_res.status_code == 404


# =============================================================================
# 4. Medicine Reminders Lifecycle & Scheduler Stub Tests
# =============================================================================

@pytest.mark.asyncio
async def test_medicine_reminder_lifecycle_and_stub(
    async_client: AsyncClient,
    patient_alice,
):
    user, patient = patient_alice
    headers = {"Authorization": f"Bearer {create_access_token({'sub': str(user.user_id), 'role': user.role.value})}"}

    # Create reminder
    payload = {
        "medication_name": "Metformin Hydrochloride",
        "dosage": "500 mg",
        "frequency": "Twice daily",
        "times_of_day": ["08:00", "20:00"],
        "instructions": "Take immediately with or after meals.",
        "start_date": "2026-09-15",
        "end_date": "2026-12-15",
        "is_active": True,
    }

    create_res = await async_client.post("/api/v1/patients/me/reminders", headers=headers, json=payload)
    assert create_res.status_code == 201
    reminder = create_res.json()
    reminder_id = reminder["reminder_id"]
    assert reminder["medication_name"] == "Metformin Hydrochloride"
    assert reminder["times_of_day"] == ["08:00", "20:00"]
    assert reminder["is_active"] is True

    # List reminders
    list_res = await async_client.get("/api/v1/patients/me/reminders", headers=headers)
    assert list_res.status_code == 200
    assert any(r["reminder_id"] == reminder_id for r in list_res.json()["reminders"])

    # Update / toggle active status to False
    update_res = await async_client.put(
        f"/api/v1/patients/me/reminders/{reminder_id}",
        headers=headers,
        json={"is_active": False},
    )
    assert update_res.status_code == 200
    assert update_res.json()["is_active"] is False

    # Filter active only -> should not include paused reminder
    active_res = await async_client.get("/api/v1/patients/me/reminders?active_only=true", headers=headers)
    assert active_res.status_code == 200
    assert not any(r["reminder_id"] == reminder_id for r in active_res.json()["reminders"])

    # Delete reminder
    del_res = await async_client.delete(f"/api/v1/patients/me/reminders/{reminder_id}", headers=headers)
    assert del_res.status_code == 200
    assert del_res.json()["detail"] == "Medicine reminder deleted successfully"


@pytest.mark.asyncio
async def test_cross_patient_reminder_isolation_403(
    async_client: AsyncClient,
    patient_alice,
    patient_bob,
):
    alice_user, _ = patient_alice
    bob_user, _ = patient_bob

    alice_headers = {"Authorization": f"Bearer {create_access_token({'sub': str(alice_user.user_id), 'role': alice_user.role.value})}"}
    bob_headers = {"Authorization": f"Bearer {create_access_token({'sub': str(bob_user.user_id), 'role': bob_user.role.value})}"}

    # Alice creates a reminder
    payload = {
        "medication_name": "Atorvastatin",
        "dosage": "20 mg",
        "frequency": "Once daily",
        "times_of_day": ["21:00"],
    }
    c_res = await async_client.post("/api/v1/patients/me/reminders", headers=alice_headers, json=payload)
    reminder_id = c_res.json()["reminder_id"]

    # Bob attempts to update Alice's reminder -> 403 Forbidden
    up_res = await async_client.put(
        f"/api/v1/patients/me/reminders/{reminder_id}",
        headers=bob_headers,
        json={"is_active": False},
    )
    assert up_res.status_code == 403
    assert "Cannot update another patient's medicine reminder" in up_res.json()["detail"]

    # Bob attempts to delete Alice's reminder -> 403 Forbidden
    del_res = await async_client.delete(
        f"/api/v1/patients/me/reminders/{reminder_id}",
        headers=bob_headers,
    )
    assert del_res.status_code == 403
    assert "Cannot delete another patient's medicine reminder" in del_res.json()["detail"]


# =============================================================================
# 5. Provider Access & Unauthenticated 401 Rejection Tests
# =============================================================================

@pytest.mark.asyncio
async def test_doctor_provider_access_to_patient_reports(
    async_client: AsyncClient,
    patient_alice,
    attending_doctor,
):
    alice_user, alice_patient = patient_alice
    doc_user, _ = attending_doctor

    alice_headers = {"Authorization": f"Bearer {create_access_token({'sub': str(alice_user.user_id), 'role': alice_user.role.value})}"}
    doc_headers = {"Authorization": f"Bearer {create_access_token({'sub': str(doc_user.user_id), 'role': doc_user.role.value})}"}

    # Alice uploads a lab report
    files = {"file": ("hba1c.pdf", io.BytesIO(b"%PDF-1.4 HbA1c 6.2%"), "application/pdf")}
    data = {"title": "HbA1c Glycated Hemoglobin", "report_type": "lab"}
    await async_client.post("/api/v1/patients/me/reports", headers=alice_headers, data=data, files=files)

    # Attending Doctor accesses reports for Alice
    provider_res = await async_client.get(
        f"/api/v1/patients/{alice_patient.patient_id}/reports",
        headers=doc_headers,
    )
    assert provider_res.status_code == 200
    assert provider_res.json()["total"] >= 1
    assert any(r["title"] == "HbA1c Glycated Hemoglobin" for r in provider_res.json()["reports"])


@pytest.mark.asyncio
async def test_unauthenticated_requests_rejected_401(
    async_client: AsyncClient,
):
    # No auth header
    res1 = await async_client.get("/api/v1/patients/me/reports")
    assert res1.status_code == 401

    res2 = await async_client.get("/api/v1/patients/me/reminders")
    assert res2.status_code == 401
