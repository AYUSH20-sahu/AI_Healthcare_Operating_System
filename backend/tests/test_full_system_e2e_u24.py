"""Full System End-to-End (E2E) Test Suite for Milestone U-24.

Validates the three mandatory clinical and administrative workflows required by
AI-HOS Unified Master Prompt v6 (Milestone U-24):

1. Patient Journey:
   Login -> Identity -> Intake Session -> Symptom Dialogue -> Active Session Recovery
   -> Complete Intake -> Doctor Availability -> Book Appointment -> Isolation Check.

2. Doctor Journey:
   Login -> Identity -> Schedule Inspection -> Voice Transcription -> Copilot SOAP Drafting
   -> Approval Queue -> Human Clinical Approval Gate (DRAFT -> FINALIZED)
   -> Duplicate Approval Protection -> Role Authorization Boundary (Patient blocked).

3. Admin Journey:
   Login -> Identity -> Operational Health -> User Management -> Clinician Provisioning
   (Mandatory License & Specialty) -> Consent Registry Governance -> Immutable Audit Trail
   -> Privilege Boundary Defense.
"""

from datetime import date, datetime, timedelta
import io
import uuid
import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Appointment,
    AppointmentStatus,
    Consent,
    ConsentScope,
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


# =============================================================================
# Test Personas & Environment Setup Fixtures
# =============================================================================

@pytest_asyncio.fixture
async def e2e_environment(db_session: AsyncSession):
    """Seed baseline test personas (Patient, Doctor, Admin) in the isolated test DB."""
    # 1. Admin User
    admin_user = User(
        user_id=uuid.uuid4(),
        email="admin@test.com",
        hashed_password=get_password_hash("adminpassword123"),
        full_name="System Administrator",
        role=UserRole.ADMIN,
        is_active=True,
    )
    db_session.add(admin_user)

    # 2. Doctor User & Profile
    doc_user_id = uuid.uuid4()
    doctor_user = User(
        user_id=doc_user_id,
        email="doctor@test.com",
        hashed_password=get_password_hash("doctorpassword123"),
        full_name="Dr. Rajesh Sharma",
        role=UserRole.DOCTOR,
        is_active=True,
    )
    db_session.add(doctor_user)
    await db_session.flush()

    doctor = Doctor(
        doctor_id=uuid.uuid4(),
        user_id=doc_user_id,
        license_number="MD-E2E-CARD-100",
        specialty="Cardiology",
        hospital_affiliation="City General Hospital",
        full_name="Dr. Rajesh Sharma",
        email="doctor@test.com",
        phone="+91-98765-43210",
    )
    db_session.add(doctor)

    # 3. Patient User & Profile
    pat_user_id = uuid.uuid4()
    patient_user = User(
        user_id=pat_user_id,
        email="patient@test.com",
        hashed_password=get_password_hash("patientpassword123"),
        full_name="Amit Kumar",
        role=UserRole.PATIENT,
        is_active=True,
    )
    db_session.add(patient_user)
    await db_session.flush()

    patient = Patient(
        patient_id=uuid.uuid4(),
        user_id=pat_user_id,
        abha_address="amit.kumar@abdm",
        full_name="Amit Kumar",
        date_of_birth=date(1985, 3, 15),
        gender="male",
        email="patient@test.com",
        phone="+91-98765-11111",
    )
    db_session.add(patient)

    # 4. Secondary Foreign Patient (for isolation tests)
    other_pat_user_id = uuid.uuid4()
    other_patient_user = User(
        user_id=other_pat_user_id,
        email="foreign.patient@test.com",
        hashed_password=get_password_hash("patientpassword123"),
        full_name="Foreign Patient",
        role=UserRole.PATIENT,
        is_active=True,
    )
    db_session.add(other_patient_user)
    await db_session.flush()

    other_patient = Patient(
        patient_id=uuid.uuid4(),
        user_id=other_pat_user_id,
        abha_address="foreign@abdm",
        full_name="Foreign Patient",
        date_of_birth=date(1990, 7, 22),
        gender="female",
        email="foreign.patient@test.com",
        phone="+91-98765-22222",
    )
    db_session.add(other_patient)

    await db_session.commit()

    return {
        "admin": admin_user,
        "doctor_user": doctor_user,
        "doctor": doctor,
        "patient_user": patient_user,
        "patient": patient,
        "other_patient_user": other_patient_user,
        "other_patient": other_patient,
    }


# =============================================================================
# 1. Patient E2E Workflow
# Login -> Intake -> Dialogue -> Complete -> Availability -> Book Appointment
# =============================================================================

class TestPatientE2EWorkflow:
    """Comprehensive E2E validation for the Patient journey."""

    @pytest.mark.asyncio
    async def test_patient_complete_journey(self, client: AsyncClient, e2e_environment):
        env = e2e_environment
        doctor = env["doctor"]

        # Step 1: Patient Login
        login_res = await client.post(
            "/api/v1/auth/login",
            json={"email": "patient@test.com", "password": "patientpassword123"},
        )
        assert login_res.status_code == 200, f"Login failed: {login_res.text}"
        login_data = login_res.json()
        assert "access_token" in login_data
        pat_token = login_data["access_token"]
        pat_headers = {"Authorization": f"Bearer {pat_token}"}

        # Step 2: Verify Identity
        me_res = await client.get("/api/v1/auth/me", headers=pat_headers)
        assert me_res.status_code == 200
        me_data = me_res.json()
        assert me_data["role"] == "patient"
        assert me_data["email"] == "patient@test.com"

        # Step 3: Initiate Conversational AI Intake Session
        intake_init_res = await client.post(
            "/api/v1/intake/sessions",
            json={"initial_message": "I have been experiencing a mild headache and fever for two days."},
            headers=pat_headers,
        )
        assert intake_init_res.status_code == 201, f"Intake session creation failed: {intake_init_res.text}"
        session_data = intake_init_res.json()
        session_id = session_data["session_id"]
        assert session_id is not None
        assert session_data["status"] == "in_progress"
        assert len(session_data["messages"]) >= 2  # assistant greeting + patient opening message

        # Step 4: Continue Dialogue Turn
        turn_res = await client.post(
            f"/api/v1/intake/sessions/{session_id}/messages",
            json={"content": "The temperature peaked at 100.5 F yesterday evening."},
            headers=pat_headers,
        )
        assert turn_res.status_code == 200, f"Intake dialogue turn failed: {turn_res.text}"
        turn_data = turn_res.json()
        assert "reply" in turn_data or "messages" in turn_data

        # Step 5: Active Session Recovery
        active_res = await client.get("/api/v1/intake/sessions/active", headers=pat_headers)
        assert active_res.status_code == 200
        active_data = active_res.json()
        assert active_data["session_id"] == session_id
        assert active_data["status"] == "in_progress"

        # Step 6: Complete Intake Session
        complete_res = await client.post(
            f"/api/v1/intake/sessions/{session_id}/complete",
            json={},
            headers=pat_headers,
        )
        assert complete_res.status_code == 200
        completed_data = complete_res.json()
        assert completed_data["status"] == "completed"

        # Step 7: Query Doctor Availability
        target_date = (date.today() + timedelta(days=2)).isoformat()
        avail_res = await client.get(
            f"/api/v1/appointments/availability?doctor_id={doctor.doctor_id}&date_str={target_date}&duration_minutes=30",
            headers=pat_headers,
        )
        assert avail_res.status_code == 200, f"Availability query failed: {avail_res.text}"
        avail_data = avail_res.json()
        assert avail_data["available_slots_count"] > 0
        first_slot = next(s for s in avail_data["slots"] if s["is_available"])
        slot_time = first_slot["start_time"]

        # Step 8: Book Appointment Linking the Intake Session
        book_res = await client.post(
            "/api/v1/appointments/book",
            json={
                "doctor_id": str(doctor.doctor_id),
                "scheduled_at": slot_time,
                "duration_minutes": 30,
                "reason": "Follow-up consultation for fever and headache",
                "intake_session_id": session_id,
            },
            headers=pat_headers,
        )
        assert book_res.status_code == 201, f"Appointment booking failed: {book_res.text}"
        appt_data = book_res.json()
        assert appt_data["doctor_id"] == str(doctor.doctor_id)
        assert appt_data["status"] in ("scheduled", "SCHEDULED")

        # Step 9: Verify Appointment Exists in Patient's Appointments
        list_res = await client.get("/api/v1/appointments", headers=pat_headers)
        assert list_res.status_code == 200
        appointments = list_res.json()
        appt_items = appointments if isinstance(appointments, list) else appointments.get("appointments", [])
        assert any(a["appointment_id"] == appt_data["appointment_id"] for a in appt_items)

        # Step 10: Patient Isolation Verification
        # Foreign patient must not access this intake session
        other_token = create_access_token(
            data={"sub": str(env["other_patient_user"].user_id), "email": env["other_patient_user"].email, "role": "patient"}
        )
        forbidden_res = await client.get(
            f"/api/v1/intake/sessions/{session_id}",
            headers={"Authorization": f"Bearer {other_token}"},
        )
        assert forbidden_res.status_code == 403, "Cross-patient isolation breached: foreign patient accessed session"


# =============================================================================
# 2. Doctor E2E Workflow
# Login -> Schedule -> Voice Transcribe -> Copilot SOAP -> Approval Gate
# =============================================================================

class TestDoctorE2EWorkflow:
    """Comprehensive E2E validation for the Doctor journey and Clinical Approval Gate."""

    @pytest.mark.asyncio
    async def test_doctor_complete_journey(self, client: AsyncClient, db_session: AsyncSession, e2e_environment):
        env = e2e_environment
        doctor = env["doctor"]
        patient = env["patient"]

        # Step 1: Doctor Login
        login_res = await client.post(
            "/api/v1/auth/login",
            json={"email": "doctor@test.com", "password": "doctorpassword123"},
        )
        assert login_res.status_code == 200, f"Doctor login failed: {login_res.text}"
        doc_token = login_res.json()["access_token"]
        doc_headers = {"Authorization": f"Bearer {doc_token}"}

        # Step 2: Verify Identity
        me_res = await client.get("/api/v1/auth/me", headers=doc_headers)
        assert me_res.status_code == 200
        assert me_res.json()["role"] == "doctor"

        # Step 3: Inspect Appointments Schedule
        appts_res = await client.get(
            f"/api/v1/appointments?doctor_id={doctor.doctor_id}",
            headers=doc_headers,
        )
        assert appts_res.status_code == 200

        # Step 4: Voice Note Speech-to-Text Transcription
        fake_audio = b"\x1a\x45\xdf\xa3" + b"\x00" * 256
        stt_res = await client.post(
            "/api/v1/voice/transcribe?language=en",
            files={"file": ("consultation.webm", fake_audio, "audio/webm")},
            headers=doc_headers,
        )
        assert stt_res.status_code == 200, f"STT transcription failed: {stt_res.text}"
        stt_data = stt_res.json()
        assert "text" in stt_data
        assert "provider" in stt_data

        # Step 5: AI Copilot Consultation Analysis & SOAP Synthesis
        copilot_res = await client.post(
            "/api/v1/copilot/analyze",
            json={
                "transcription": (
                    "Patient reports persistent throbbing headache for two weeks, worse in mornings. "
                    "Vitals: BP 138/88, Pulse 76. No visual disturbances. Suspected tension headache."
                ),
                "patient_id": str(patient.patient_id),
                "patient_name": patient.full_name,
                "chief_complaint": "Persistent headache",
                "vitals": {"blood_pressure": "138/88", "heart_rate": 76},
                "allergies": ["Penicillin"],
            },
            headers=doc_headers,
        )
        assert copilot_res.status_code == 200, f"Copilot analysis failed: {copilot_res.text}"
        copilot_data = copilot_res.json()
        assert copilot_data["success"] is True
        assert copilot_data["data"] is not None

        # Step 6: Create Draft Medical Record and Draft Prescription in Database
        draft_record = MedicalRecord(
            record_id=uuid.uuid4(),
            patient_id=patient.patient_id,
            doctor_id=doctor.doctor_id,
            status=MedicalRecordStatus.DRAFT,
            content={
                "chief_complaint": "Persistent headache",
                "assessment": "Tension-type headache, mild hypertension",
                "plan": "Stress reduction, sleep hygiene, PRN analgesic",
                "confidence": 0.92,
                "basis": "Clinical interview and vital signs correlation",
            },
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db_session.add(draft_record)

        draft_rx = Prescription(
            prescription_id=uuid.uuid4(),
            medical_record_id=draft_record.record_id,
            patient_id=patient.patient_id,
            doctor_id=doctor.doctor_id,
            status=PrescriptionStatus.DRAFT,
            medications=[
                {
                    "name": "Ibuprofen",
                    "dosage": "400mg",
                    "frequency": "PRN as needed",
                    "duration": "5 days",
                    "instructions": "Take with food",
                }
            ],
            notes="Avoid taking on an empty stomach",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db_session.add(draft_rx)
        await db_session.commit()

        # Step 7: Doctor Queries the Approval Queue
        queue_res = await client.get("/api/v1/approval/drafts", headers=doc_headers)
        assert queue_res.status_code == 200, f"Approval queue query failed: {queue_res.text}"
        queue_data = queue_res.json()
        record_ids = [r["record_id"] for r in queue_data["medical_records"]]
        rx_ids = [rx["prescription_id"] for rx in queue_data["prescriptions"]]
        assert str(draft_record.record_id) in record_ids
        assert str(draft_rx.prescription_id) in rx_ids

        # Step 8: Human-in-the-Loop Clinical Gate: Doctor Approves Medical Record
        rec_approve_res = await client.post(
            f"/api/v1/approval/medical-records/{draft_record.record_id}/review",
            json={"action": "approve", "reviewer_notes": "Reviewed and clinically validated."},
            headers=doc_headers,
        )
        assert rec_approve_res.status_code == 200, f"Medical record approval failed: {rec_approve_res.text}"
        assert rec_approve_res.json()["status"] == "finalized"

        # Step 9: Human-in-the-Loop Clinical Gate: Doctor Approves Prescription
        rx_approve_res = await client.post(
            f"/api/v1/approval/prescriptions/{draft_rx.prescription_id}/review",
            json={"action": "approve", "reviewer_notes": "Prescription verified with allergy checks."},
            headers=doc_headers,
        )
        assert rx_approve_res.status_code == 200, f"Prescription approval failed: {rx_approve_res.text}"
        assert rx_approve_res.json()["status"] == "finalized"

        # Step 10: Duplicate Approval Protection (Safety Check)
        duplicate_res = await client.post(
            f"/api/v1/approval/medical-records/{draft_record.record_id}/review",
            json={"action": "approve"},
            headers=doc_headers,
        )
        assert duplicate_res.status_code == 400, "Duplicate approval safety gate failed: expected 400 Bad Request"

        # Step 11: RBAC Boundary Check: Patient cannot approve clinical records
        pat_token = create_access_token(
            data={"sub": str(env["patient_user"].user_id), "email": env["patient_user"].email, "role": "patient"}
        )
        unauthorized_res = await client.post(
            f"/api/v1/approval/medical-records/{draft_record.record_id}/review",
            json={"action": "approve"},
            headers={"Authorization": f"Bearer {pat_token}"},
        )
        assert unauthorized_res.status_code == 403, "RBAC breach: patient was able to call review endpoint"


# =============================================================================
# 3. Admin E2E Workflow
# Login -> Health -> Users -> Provisioning -> Consent Governance -> Audit Trail
# =============================================================================

class TestAdminE2EWorkflow:
    """Comprehensive E2E validation for the Administrator journey and governance controls."""

    @pytest.mark.asyncio
    async def test_admin_complete_journey(self, client: AsyncClient, e2e_environment):
        env = e2e_environment
        doctor = env["doctor"]
        patient = env["patient"]

        # Step 1: Admin Login
        login_res = await client.post(
            "/api/v1/auth/login",
            json={"email": "admin@test.com", "password": "adminpassword123"},
        )
        assert login_res.status_code == 200, f"Admin login failed: {login_res.text}"
        admin_token = login_res.json()["access_token"]
        admin_headers = {"Authorization": f"Bearer {admin_token}"}

        # Step 2: Verify Identity
        me_res = await client.get("/api/v1/auth/me", headers=admin_headers)
        assert me_res.status_code == 200
        assert me_res.json()["role"] == "admin"

        # Step 3: Operational Health Check
        health_res = await client.get("/health")
        assert health_res.status_code == 200
        health_data = health_res.json()
        assert health_data["status"] == "ok"

        # Step 4: Admin Queries Registered Users List
        users_res = await client.get("/api/v1/admin/users/", headers=admin_headers)
        assert users_res.status_code == 200
        users_data = users_res.json()
        assert users_data["total"] >= 3

        # Step 5: Provision a New Clinician Account (Mandatory license & specialty check)
        new_doc_email = f"dr.neurologist.{uuid.uuid4().hex[:6]}@hospital.org"
        prov_res = await client.post(
            "/api/v1/admin/users/",
            json={
                "full_name": "Dr. Priya Patel",
                "email": new_doc_email,
                "password": "secureClinicianPass123",
                "role": "doctor",
                "specialty": "Neurology",
                "license_number": f"MD-NEURO-{uuid.uuid4().hex[:6].upper()}",
                "hospital_affiliation": "Metropolitan Health Institute",
                "phone": "+91-98765-54321",
            },
            headers=admin_headers,
        )
        assert prov_res.status_code == 201, f"Doctor provisioning failed: {prov_res.text}"
        prov_data = prov_res.json()
        assert prov_data["role"] == "doctor"
        assert prov_data["doctor_profile"]["specialty"] == "Neurology"

        # Step 6: Security Check - Provisioning Clinician without license is strictly rejected
        invalid_prov_res = await client.post(
            "/api/v1/admin/users/",
            json={
                "full_name": "Dr. Incomplete Clinician",
                "email": f"dr.invalid.{uuid.uuid4().hex[:6]}@hospital.org",
                "password": "secureClinicianPass123",
                "role": "doctor",
                # missing specialty & license_number
            },
            headers=admin_headers,
        )
        assert invalid_prov_res.status_code == 400, "Security failure: clinician provisioned without valid license"

        # Step 7: Consent Governance - Grant and Query Consent Scope
        consent_grant_res = await client.post(
            "/api/v1/consents",
            json={
                "patient_id": str(patient.patient_id),
                "provider_id": str(doctor.doctor_id),
                "record_scope": "FULL_ACCESS",
            },
            headers=admin_headers,
        )
        assert consent_grant_res.status_code == 201, f"Consent grant failed: {consent_grant_res.text}"
        consent_id = consent_grant_res.json()["consent_id"]

        consents_query_res = await client.get(
            f"/api/v1/consents?patient_id={patient.patient_id}",
            headers=admin_headers,
        )
        assert consents_query_res.status_code == 200
        consent_list = consents_query_res.json()
        assert any(c["consent_id"] == consent_id for c in consent_list)

        # Step 8: Immutable Audit Trail Inspection
        audit_res = await client.get("/api/v1/admin/audit/logs", headers=admin_headers)
        assert audit_res.status_code == 200, f"Audit query failed: {audit_res.text}"
        audit_data = audit_res.json()
        assert "logs" in audit_data or "items" in audit_data or isinstance(audit_data, list)

        # Step 9: Privilege Boundary Defense - Doctor cannot access Admin provisioning
        doc_token = create_access_token(
            data={"sub": str(env["doctor_user"].user_id), "email": env["doctor_user"].email, "role": "doctor"}
        )
        unauth_prov_res = await client.post(
            "/api/v1/admin/users/",
            json={"full_name": "Hacker", "email": "hacker@test.com", "password": "pass", "role": "admin"},
            headers={"Authorization": f"Bearer {doc_token}"},
        )
        assert unauth_prov_res.status_code == 403, "Privilege escalation: doctor accessed admin user provisioning"
