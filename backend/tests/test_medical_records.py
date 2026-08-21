"""Tests for Medical Records API."""

from datetime import date, datetime, timedelta
from uuid import uuid4

import pytest
import pytest_asyncio

from app.models import (
    Appointment,
    AppointmentStatus,
    Doctor,
    MedicalRecord,
    MedicalRecordStatus,
    Patient,
    User,
    UserRole,
)
from app.services.auth.service import create_access_token, get_password_hash


@pytest_asyncio.fixture
async def admin_user(db_session):
    """Create an admin user."""
    user = User(
        user_id=uuid4(),
        email="admin@test.com",
        hashed_password=get_password_hash("adminpassword123"),
        full_name="Admin User",
        role=UserRole.ADMIN,
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def admin_token(admin_user):
    """Create an admin access token."""
    return create_access_token(data={"sub": str(admin_user.user_id), "email": admin_user.email, "role": admin_user.role.value})


@pytest_asyncio.fixture
async def doctor_user(db_session):
    """Create a doctor user."""
    user = User(
        user_id=uuid4(),
        email="doctor@test.com",
        hashed_password=get_password_hash("doctorpassword123"),
        full_name="Dr. Test",
        role=UserRole.DOCTOR,
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def doctor_token(doctor_user):
    """Create a doctor access token."""
    return create_access_token(data={"sub": str(doctor_user.user_id), "email": doctor_user.email, "role": doctor_user.role.value})


@pytest_asyncio.fixture
async def test_doctor(db_session, doctor_user):
    """Create a test doctor."""
    doctor = Doctor(
        doctor_id=uuid4(),
        user_id=doctor_user.user_id,
        specialty="Cardiology",
        license_number="MED12345",
        hospital_affiliation="Test Hospital",
        email="doctor@test.com",
        full_name="Dr. Test",
        phone="+91-9876543210",
    )
    db_session.add(doctor)
    await db_session.commit()
    await db_session.refresh(doctor)
    return doctor


@pytest_asyncio.fixture
async def another_doctor_user(db_session):
    """Create another doctor user."""
    user = User(
        user_id=uuid4(),
        email="doctor2@test.com",
        hashed_password=get_password_hash("doctorpassword123"),
        full_name="Dr. Test 2",
        role=UserRole.DOCTOR,
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def another_doctor_token(another_doctor_user):
    """Create another doctor access token."""
    return create_access_token(data={"sub": str(another_doctor_user.user_id), "email": another_doctor_user.email, "role": another_doctor_user.role.value})


@pytest_asyncio.fixture
async def another_doctor(db_session, another_doctor_user):
    """Create another test doctor."""
    doctor = Doctor(
        doctor_id=uuid4(),
        user_id=another_doctor_user.user_id,
        specialty="Neurology",
        license_number="MED67890",
        hospital_affiliation="Brain Hospital",
        email="doctor2@test.com",
        full_name="Dr. Test 2",
        phone="+91-9876543211",
    )
    db_session.add(doctor)
    await db_session.commit()
    await db_session.refresh(doctor)
    return doctor


@pytest_asyncio.fixture
async def patient_user(db_session):
    """Create a patient user."""
    user = User(
        user_id=uuid4(),
        email="patient@test.com",
        hashed_password=get_password_hash("patientpassword123"),
        full_name="Test Patient",
        role=UserRole.PATIENT,
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def patient_token(patient_user):
    """Create a patient access token."""
    return create_access_token(data={"sub": str(patient_user.user_id), "email": patient_user.email, "role": patient_user.role.value})


@pytest_asyncio.fixture
async def test_patient(db_session, patient_user):
    """Create a test patient."""
    patient = Patient(
        patient_id=uuid4(),
        user_id=patient_user.user_id,
        abha_address="patient@abdm",
        full_name="Test Patient",
        date_of_birth=date(1990, 1, 1),
        gender="female",
        phone="+91-9876543210",
        email="patient@test.com",
    )
    db_session.add(patient)
    await db_session.commit()
    await db_session.refresh(patient)
    return patient


@pytest_asyncio.fixture
async def another_patient_user(db_session):
    """Create another patient user."""
    user = User(
        user_id=uuid4(),
        email="patient2@test.com",
        hashed_password=get_password_hash("patientpassword123"),
        full_name="Test Patient 2",
        role=UserRole.PATIENT,
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def another_patient_token(another_patient_user):
    """Create another patient access token."""
    return create_access_token(data={"sub": str(another_patient_user.user_id), "email": another_patient_user.email, "role": another_patient_user.role.value})


@pytest_asyncio.fixture
async def another_patient(db_session, another_patient_user):
    """Create another test patient."""
    patient = Patient(
        patient_id=uuid4(),
        user_id=another_patient_user.user_id,
        abha_address="patient2@abdm",
        full_name="Test Patient 2",
        date_of_birth=date(1990, 1, 1),
        gender="male",
        phone="+91-9876543211",
        email="patient2@test.com",
    )
    db_session.add(patient)
    await db_session.commit()
    await db_session.refresh(patient)
    return patient


@pytest_asyncio.fixture
async def test_appointment(db_session, test_patient, test_doctor):
    """Create a test appointment."""
    appointment = Appointment(
        appointment_id=uuid4(),
        patient_id=test_patient.patient_id,
        doctor_id=test_doctor.doctor_id,
        scheduled_at=datetime.utcnow() + timedelta(days=1),
        duration_minutes=30,
        status=AppointmentStatus.SCHEDULED,
        notes="Test appointment",
    )
    db_session.add(appointment)
    await db_session.commit()
    await db_session.refresh(appointment)
    return appointment


@pytest_asyncio.fixture
async def test_medical_record(db_session, test_patient, test_doctor, test_appointment):
    """Create a test medical record."""
    record = MedicalRecord(
        record_id=uuid4(),
        patient_id=test_patient.patient_id,
        doctor_id=test_doctor.doctor_id,
        appointment_id=test_appointment.appointment_id,
        content={
            "chief_complaint": "Chest pain",
            "history_present_illness": "Patient reports chest pain for 2 hours",
            "physical_examination": "BP 140/90, HR 88",
            "assessment": "Possible angina",
            "plan": "ECG, troponin, cardiology referral",
            "diagnosis_codes": ["I20.9"],
        },
        status=MedicalRecordStatus.DRAFT,
    )
    db_session.add(record)
    await db_session.commit()
    await db_session.refresh(record)
    return record


class TestMedicalRecordsAPI:
    """Test Medical Records API endpoints."""

    @pytest.mark.asyncio
    async def test_create_medical_record_doctor(self, client, doctor_user, doctor_token, test_patient, test_doctor, test_appointment):
        """Test creating a medical record as doctor."""
        response = await client.post(
            "/api/v1/medical-records/",
            json={
                "patient_id": str(test_patient.patient_id),
                "doctor_id": str(test_doctor.doctor_id),
                "appointment_id": str(test_appointment.appointment_id),
                "content": {
                    "chief_complaint": "Headache",
                    "history_present_illness": "Patient reports headache for 3 days",
                    "physical_examination": "Normal neuro exam",
                    "assessment": "Tension headache",
                    "plan": "NSAIDs, follow up in 1 week",
                    "diagnosis_codes": ["G44.2"],
                },
            },
            headers={"Authorization": f"Bearer {doctor_token}"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["content"]["chief_complaint"] == "Headache"
        assert data["status"] == "DRAFT"
        assert data["doctor_id"] == str(test_doctor.doctor_id)

    @pytest.mark.asyncio
    async def test_create_medical_record_admin(self, client, admin_user, admin_token, test_patient, test_doctor):
        """Test creating a medical record as admin."""
        response = await client.post(
            "/api/v1/medical-records/",
            json={
                "patient_id": str(test_patient.patient_id),
                "doctor_id": str(test_doctor.doctor_id),
                "content": {
                    "chief_complaint": "Abdominal pain",
                    "history_present_illness": "Patient reports abdominal pain",
                    "assessment": "Gastritis",
                    "plan": "PPI, diet modification",
                },
            },
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "DRAFT"

    @pytest.mark.asyncio
    async def test_create_medical_record_patient_forbidden(self, client, patient_user, patient_token, test_patient, test_doctor):
        """Test creating a medical record as patient is forbidden."""
        response = await client.post(
            "/api/v1/medical-records/",
            json={
                "patient_id": str(test_patient.patient_id),
                "doctor_id": str(test_doctor.doctor_id),
                "content": {
                    "chief_complaint": "Self diagnosis",
                },
            },
            headers={"Authorization": f"Bearer {patient_token}"},
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_create_medical_record_invalid_patient(self, client, doctor_user, doctor_token, test_doctor):
        """Test creating medical record with invalid patient fails."""
        response = await client.post(
            "/api/v1/medical-records/",
            json={
                "patient_id": str(uuid4()),
                "doctor_id": str(test_doctor.doctor_id),
                "content": {
                    "chief_complaint": "Test",
                },
            },
            headers={"Authorization": f"Bearer {doctor_token}"},
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_create_medical_record_invalid_doctor(self, client, doctor_user, doctor_token, test_patient):
        """Test creating medical record with invalid doctor fails."""
        response = await client.post(
            "/api/v1/medical-records/",
            json={
                "patient_id": str(test_patient.patient_id),
                "doctor_id": str(uuid4()),
                "content": {
                    "chief_complaint": "Test",
                },
            },
            headers={"Authorization": f"Bearer {doctor_token}"},
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_create_medical_record_doctor_mismatch(self, client, another_doctor_user, another_doctor_token, test_patient, test_doctor):
        """Test doctor cannot create record for another doctor."""
        response = await client.post(
            "/api/v1/medical-records/",
            json={
                "patient_id": str(test_patient.patient_id),
                "doctor_id": str(test_doctor.doctor_id),
                "content": {
                    "chief_complaint": "Test",
                },
            },
            headers={"Authorization": f"Bearer {another_doctor_token}"},
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_create_medical_record_invalid_appointment(self, client, doctor_user, doctor_token, test_patient, test_doctor):
        """Test creating medical record with invalid appointment fails."""
        response = await client.post(
            "/api/v1/medical-records/",
            json={
                "patient_id": str(test_patient.patient_id),
                "doctor_id": str(test_doctor.doctor_id),
                "appointment_id": str(uuid4()),
                "content": {
                    "chief_complaint": "Test",
                },
            },
            headers={"Authorization": f"Bearer {doctor_token}"},
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_create_medical_record_appointment_mismatch(self, client, doctor_user, doctor_token, test_patient, test_doctor, another_doctor, test_appointment, db_session):
        """Test creating medical record with appointment for different doctor fails."""
        # Create an appointment for another_doctor
        another_appointment = Appointment(
            appointment_id=uuid4(),
            patient_id=test_patient.patient_id,
            doctor_id=another_doctor.doctor_id,
            scheduled_at=datetime.utcnow() + timedelta(days=2),
            duration_minutes=30,
            status=AppointmentStatus.SCHEDULED,
        )
        db_session.add(another_appointment)
        await db_session.commit()
        await db_session.refresh(another_appointment)
        
        # Try to create a medical record with test_doctor but another_doctor's appointment
        response = await client.post(
            "/api/v1/medical-records/",
            json={
                "patient_id": str(test_patient.patient_id),
                "doctor_id": str(test_doctor.doctor_id),
                "appointment_id": str(another_appointment.appointment_id),
                "content": {
                    "chief_complaint": "Test",
                },
            },
            headers={"Authorization": f"Bearer {doctor_token}"},
        )
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_get_medical_record_doctor_own(self, client, doctor_user, doctor_token, test_doctor, test_medical_record):
        """Test doctor can read their own medical record."""
        response = await client.get(
            f"/api/v1/medical-records/{test_medical_record.record_id}/",
            headers={"Authorization": f"Bearer {doctor_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["record_id"] == str(test_medical_record.record_id)
        assert data["content"]["chief_complaint"] == test_medical_record.content["chief_complaint"]

    @pytest.mark.asyncio
    async def test_get_medical_record_patient_own(self, client, patient_user, patient_token, test_patient, test_medical_record):
        """Test patient can read their own medical record."""
        response = await client.get(
            f"/api/v1/medical-records/{test_medical_record.record_id}/",
            headers={"Authorization": f"Bearer {patient_token}"},
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_get_medical_record_admin(self, client, admin_user, admin_token, test_medical_record):
        """Test admin can read any medical record."""
        response = await client.get(
            f"/api/v1/medical-records/{test_medical_record.record_id}/",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_get_medical_record_doctor_other_forbidden(self, client, another_doctor_user, another_doctor_token, test_medical_record):
        """Test doctor cannot read another doctor's medical record."""
        response = await client.get(
            f"/api/v1/medical-records/{test_medical_record.record_id}/",
            headers={"Authorization": f"Bearer {another_doctor_token}"},
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_get_medical_record_patient_other_forbidden(self, client, another_patient_user, another_patient_token, another_patient, test_medical_record):
        """Test patient cannot read another patient's medical record."""
        response = await client.get(
            f"/api/v1/medical-records/{test_medical_record.record_id}/",
            headers={"Authorization": f"Bearer {another_patient_token}"},
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_get_medical_record_not_found(self, client, admin_user, admin_token):
        """Test getting non-existent medical record returns 404."""
        response = await client.get(
            f"/api/v1/medical-records/{uuid4()}/",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_medical_record_doctor_own(self, client, doctor_user, doctor_token, test_doctor, test_medical_record):
        """Test doctor can update their own medical record."""
        response = await client.put(
            f"/api/v1/medical-records/{test_medical_record.record_id}/",
            json={
                "content": {
                    "physical_examination": "Updated exam findings",
                    "plan": "Updated plan",
                },
            },
            headers={"Authorization": f"Bearer {doctor_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["content"]["physical_examination"] == "Updated exam findings"
        assert data["content"]["plan"] == "Updated plan"

    @pytest.mark.asyncio
    async def test_update_medical_record_admin(self, client, admin_user, admin_token, test_medical_record):
        """Test admin can update any medical record."""
        response = await client.put(
            f"/api/v1/medical-records/{test_medical_record.record_id}/",
            json={
                "content": {
                    "assessment": "Updated by admin",
                },
                "status": "FINALIZED",
            },
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["content"]["assessment"] == "Updated by admin"
        assert data["status"] == "FINALIZED"

    @pytest.mark.asyncio
    async def test_update_medical_record_doctor_cannot_finalize(self, client, doctor_user, doctor_token, test_doctor, test_medical_record):
        """Test doctor cannot finalize a medical record."""
        response = await client.put(
            f"/api/v1/medical-records/{test_medical_record.record_id}/",
            json={"status": "FINALIZED"},
            headers={"Authorization": f"Bearer {doctor_token}"},
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_update_medical_record_patient_forbidden(self, client, patient_user, patient_token, test_patient, test_medical_record):
        """Test patient cannot update medical record."""
        response = await client.put(
            f"/api/v1/medical-records/{test_medical_record.record_id}/",
            json={"content": {"chief_complaint": "Patient trying to edit"}},
            headers={"Authorization": f"Bearer {patient_token}"},
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_list_patient_medical_records_patient(self, client, patient_user, patient_token, test_patient, test_medical_record):
        """Test patient can list their own medical records."""
        response = await client.get(
            f"/api/v1/medical-records/patient/{test_patient.patient_id}/",
            headers={"Authorization": f"Bearer {patient_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        assert len(data["records"]) >= 1

    @pytest.mark.asyncio
    async def test_list_patient_medical_records_doctor(self, client, doctor_user, doctor_token, test_doctor, test_patient, test_medical_record):
        """Test doctor can list their patient's medical records."""
        response = await client.get(
            f"/api/v1/medical-records/patient/{test_patient.patient_id}/",
            headers={"Authorization": f"Bearer {doctor_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1

    @pytest.mark.asyncio
    async def test_list_patient_medical_records_doctor_other_forbidden(self, client, another_doctor_user, another_doctor_token, another_doctor, test_patient, test_medical_record):
        """Test doctor cannot list records for patient they don't treat."""
        response = await client.get(
            f"/api/v1/medical-records/patient/{test_patient.patient_id}/",
            headers={"Authorization": f"Bearer {another_doctor_token}"},
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_list_patient_medical_records_patient_other_forbidden(self, client, another_patient_user, another_patient_token, another_patient, test_patient, test_medical_record):
        """Test patient cannot list another patient's medical records."""
        response = await client.get(
            f"/api/v1/medical-records/patient/{test_patient.patient_id}/",
            headers={"Authorization": f"Bearer {another_patient_token}"},
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_list_patient_medical_records_admin(self, client, admin_user, admin_token, test_patient, test_medical_record):
        """Test admin can list any patient's medical records."""
        response = await client.get(
            f"/api/v1/medical-records/patient/{test_patient.patient_id}/",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_list_patient_medical_records_filter_status(self, client, admin_user, admin_token, test_patient, test_medical_record):
        """Test filtering medical records by status."""
        response = await client.get(
            f"/api/v1/medical-records/patient/{test_patient.patient_id}/?status=draft",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        for record in data["records"]:
            assert record["status"] == "DRAFT"

    @pytest.mark.asyncio
    async def test_list_patient_medical_records_pagination(self, client, admin_user, admin_token, test_patient, test_medical_record):
        """Test medical records pagination."""
        response = await client.get(
            f"/api/v1/medical-records/patient/{test_patient.patient_id}/?page=1&page_size=10",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 1
        assert data["page_size"] == 10

    @pytest.mark.asyncio
    async def test_list_all_medical_records_admin(self, client, admin_user, admin_token, test_medical_record):
        """Test admin can list all medical records."""
        response = await client.get(
            "/api/v1/medical-records/",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1

    @pytest.mark.asyncio
    async def test_list_all_medical_records_doctor_forbidden(self, client, doctor_user, doctor_token, test_medical_record):
        """Test doctor cannot list all medical records."""
        response = await client.get(
            "/api/v1/medical-records/",
            headers={"Authorization": f"Bearer {doctor_token}"},
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_list_all_medical_records_filter_patient(self, client, admin_user, admin_token, test_patient, test_medical_record):
        """Test filtering all medical records by patient."""
        response = await client.get(
            f"/api/v1/medical-records/?patient_id={test_patient.patient_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        for record in data["records"]:
            assert record["patient_id"] == str(test_patient.patient_id)

    @pytest.mark.asyncio
    async def test_list_all_medical_records_filter_doctor(self, client, admin_user, admin_token, test_doctor, test_medical_record):
        """Test filtering all medical records by doctor."""
        response = await client.get(
            f"/api/v1/medical-records/?doctor_id={test_doctor.doctor_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        for record in data["records"]:
            assert record["doctor_id"] == str(test_doctor.doctor_id)