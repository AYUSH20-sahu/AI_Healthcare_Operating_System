"""Tests for Prescriptions API."""

import pytest
import pytest_asyncio
from uuid import uuid4
from datetime import datetime, date, timedelta

from app.models import Prescription, Patient, Doctor, User, UserRole, PrescriptionStatus, MedicalRecord, Appointment, AppointmentStatus
from app.services.auth.service import get_password_hash, create_access_token


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
        status="DRAFT",
    )
    db_session.add(record)
    await db_session.commit()
    await db_session.refresh(record)
    return record


@pytest_asyncio.fixture
async def test_prescription(db_session, test_patient, test_doctor, test_medical_record):
    """Create a test prescription."""
    prescription = Prescription(
        prescription_id=uuid4(),
        medical_record_id=test_medical_record.record_id,
        patient_id=test_patient.patient_id,
        doctor_id=test_doctor.doctor_id,
        medications=[
            {
                "name": "Aspirin",
                "dosage": "81mg",
                "frequency": "once daily",
                "duration": "30 days",
                "route": "oral",
                "instructions": "Take with food",
                "quantity": 30,
                "refills": 2,
            }
        ],
        status=PrescriptionStatus.DRAFT,
    )
    db_session.add(prescription)
    await db_session.commit()
    await db_session.refresh(prescription)
    return prescription


class TestPrescriptionsAPI:
    """Test Prescriptions API endpoints."""

    @pytest.mark.asyncio
    async def test_create_prescription_doctor(self, client, doctor_user, doctor_token, test_patient, test_doctor, test_medical_record):
        """Test creating a prescription as doctor."""
        response = await client.post(
            "/api/v1/prescriptions/",
            json={
                "patient_id": str(test_patient.patient_id),
                "doctor_id": str(test_doctor.doctor_id),
                "medical_record_id": str(test_medical_record.record_id),
                "medications": [
                    {
                        "name": "Metoprolol",
                        "dosage": "50mg",
                        "frequency": "twice daily",
                        "duration": "30 days",
                        "route": "oral",
                        "instructions": "Take with meals",
                        "quantity": 60,
                        "refills": 1,
                    }
                ],
                "notes": "For hypertension management",
            },
            headers={"Authorization": f"Bearer {doctor_token}"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["medications"][0]["name"] == "Metoprolol"
        assert data["status"] == "DRAFT"
        assert data["doctor_id"] == str(test_doctor.doctor_id)
        assert data["patient_id"] == str(test_patient.patient_id)

    @pytest.mark.asyncio
    async def test_create_prescription_admin(self, client, admin_user, admin_token, test_patient, test_doctor):
        """Test creating a prescription as admin."""
        response = await client.post(
            "/api/v1/prescriptions/",
            json={
                "patient_id": str(test_patient.patient_id),
                "doctor_id": str(test_doctor.doctor_id),
                "medications": [
                    {
                        "name": "Lisinopril",
                        "dosage": "10mg",
                        "frequency": "once daily",
                        "duration": "90 days",
                        "route": "oral",
                    }
                ],
            },
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "DRAFT"

    @pytest.mark.asyncio
    async def test_create_prescription_patient_forbidden(self, client, patient_user, patient_token, test_patient, test_doctor):
        """Test creating a prescription as patient is forbidden."""
        response = await client.post(
            "/api/v1/prescriptions/",
            json={
                "patient_id": str(test_patient.patient_id),
                "doctor_id": str(test_doctor.doctor_id),
                "medications": [
                    {
                        "name": "Self prescribed",
                        "dosage": "10mg",
                        "frequency": "once daily",
                        "duration": "30 days",
                    }
                ],
            },
            headers={"Authorization": f"Bearer {patient_token}"},
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_create_prescription_invalid_patient(self, client, doctor_user, doctor_token, test_doctor):
        """Test creating prescription with invalid patient fails."""
        response = await client.post(
            "/api/v1/prescriptions/",
            json={
                "patient_id": str(uuid4()),
                "doctor_id": str(test_doctor.doctor_id),
                "medications": [
                    {
                        "name": "Test",
                        "dosage": "10mg",
                        "frequency": "once daily",
                        "duration": "30 days",
                    }
                ],
            },
            headers={"Authorization": f"Bearer {doctor_token}"},
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_create_prescription_invalid_doctor(self, client, doctor_user, doctor_token, test_patient):
        """Test creating prescription with invalid doctor fails."""
        response = await client.post(
            "/api/v1/prescriptions/",
            json={
                "patient_id": str(test_patient.patient_id),
                "doctor_id": str(uuid4()),
                "medications": [
                    {
                        "name": "Test",
                        "dosage": "10mg",
                        "frequency": "once daily",
                        "duration": "30 days",
                    }
                ],
            },
            headers={"Authorization": f"Bearer {doctor_token}"},
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_create_prescription_doctor_mismatch(self, client, another_doctor_user, another_doctor_token, test_patient, test_doctor):
        """Test doctor cannot create prescription for another doctor."""
        response = await client.post(
            "/api/v1/prescriptions/",
            json={
                "patient_id": str(test_patient.patient_id),
                "doctor_id": str(test_doctor.doctor_id),
                "medications": [
                    {
                        "name": "Test",
                        "dosage": "10mg",
                        "frequency": "once daily",
                        "duration": "30 days",
                    }
                ],
            },
            headers={"Authorization": f"Bearer {another_doctor_token}"},
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_create_prescription_invalid_medical_record(self, client, doctor_user, doctor_token, test_patient, test_doctor):
        """Test creating prescription with invalid medical record fails."""
        response = await client.post(
            "/api/v1/prescriptions/",
            json={
                "patient_id": str(test_patient.patient_id),
                "doctor_id": str(test_doctor.doctor_id),
                "medical_record_id": str(uuid4()),
                "medications": [
                    {
                        "name": "Test",
                        "dosage": "10mg",
                        "frequency": "once daily",
                        "duration": "30 days",
                    }
                ],
            },
            headers={"Authorization": f"Bearer {doctor_token}"},
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_create_prescription_medical_record_mismatch(self, client, doctor_user, doctor_token, test_patient, test_doctor, another_doctor, test_medical_record, db_session):
        """Test creating prescription with medical record for different doctor fails."""
        # Create a medical record for another_doctor
        another_appointment = Appointment(
            appointment_id=uuid4(),
            patient_id=test_patient.patient_id,
            doctor_id=another_doctor.doctor_id,
            scheduled_at=datetime.utcnow() + timedelta(days=2),
            duration_minutes=30,
            status=AppointmentStatus.SCHEDULED,
            notes="Another doctor appointment",
        )
        db_session.add(another_appointment)
        await db_session.commit()
        await db_session.refresh(another_appointment)
        
        another_medical_record = MedicalRecord(
            record_id=uuid4(),
            patient_id=test_patient.patient_id,
            doctor_id=another_doctor.doctor_id,
            appointment_id=another_appointment.appointment_id,
            content={
                "chief_complaint": "Headache",
                "assessment": "Tension headache",
            },
            status="DRAFT",
        )
        db_session.add(another_medical_record)
        await db_session.commit()
        await db_session.refresh(another_medical_record)
        
        # Try to create prescription with test_doctor but another_doctor's medical record
        response = await client.post(
            "/api/v1/prescriptions/",
            json={
                "patient_id": str(test_patient.patient_id),
                "doctor_id": str(test_doctor.doctor_id),
                "medical_record_id": str(another_medical_record.record_id),
                "medications": [
                    {
                        "name": "Test",
                        "dosage": "10mg",
                        "frequency": "once daily",
                        "duration": "30 days",
                    }
                ],
            },
            headers={"Authorization": f"Bearer {doctor_token}"},
        )
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_get_prescription_doctor_own(self, client, doctor_user, doctor_token, test_doctor, test_prescription):
        """Test doctor can read their own prescription."""
        response = await client.get(
            f"/api/v1/prescriptions/{test_prescription.prescription_id}/",
            headers={"Authorization": f"Bearer {doctor_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["prescription_id"] == str(test_prescription.prescription_id)
        assert data["medications"][0]["name"] == test_prescription.medications[0]["name"]

    @pytest.mark.asyncio
    async def test_get_prescription_patient_own(self, client, patient_user, patient_token, test_patient, test_prescription):
        """Test patient can read their own prescription."""
        response = await client.get(
            f"/api/v1/prescriptions/{test_prescription.prescription_id}/",
            headers={"Authorization": f"Bearer {patient_token}"},
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_get_prescription_admin(self, client, admin_user, admin_token, test_prescription):
        """Test admin can read any prescription."""
        response = await client.get(
            f"/api/v1/prescriptions/{test_prescription.prescription_id}/",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_get_prescription_doctor_other_forbidden(self, client, another_doctor_user, another_doctor_token, test_prescription):
        """Test doctor cannot read another doctor's prescription."""
        response = await client.get(
            f"/api/v1/prescriptions/{test_prescription.prescription_id}/",
            headers={"Authorization": f"Bearer {another_doctor_token}"},
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_get_prescription_patient_other_forbidden(self, client, another_patient_user, another_patient_token, another_patient, test_prescription):
        """Test patient cannot read another patient's prescription."""
        response = await client.get(
            f"/api/v1/prescriptions/{test_prescription.prescription_id}/",
            headers={"Authorization": f"Bearer {another_patient_token}"},
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_get_prescription_not_found(self, client, admin_user, admin_token):
        """Test getting non-existent prescription returns 404."""
        response = await client.get(
            f"/api/v1/prescriptions/{uuid4()}/",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_prescription_doctor_own(self, client, doctor_user, doctor_token, test_doctor, test_prescription):
        """Test doctor can update their own prescription."""
        response = await client.put(
            f"/api/v1/prescriptions/{test_prescription.prescription_id}/",
            json={
                "medications": [
                    {
                        "name": "Aspirin",
                        "dosage": "100mg",
                        "frequency": "once daily",
                        "duration": "30 days",
                        "route": "oral",
                        "instructions": "Updated instructions",
                    }
                ],
                "notes": "Updated notes",
            },
            headers={"Authorization": f"Bearer {doctor_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["medications"][0]["dosage"] == "100mg"
        assert data["notes"] == "Updated notes"

    @pytest.mark.asyncio
    async def test_update_prescription_admin(self, client, admin_user, admin_token, test_prescription):
        """Test admin can update any prescription."""
        response = await client.put(
            f"/api/v1/prescriptions/{test_prescription.prescription_id}/",
            json={
                "status": "FINALIZED",
            },
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "FINALIZED"

    @pytest.mark.asyncio
    async def test_update_prescription_doctor_cannot_finalize(self, client, doctor_user, doctor_token, test_doctor, test_prescription):
        """Test doctor cannot finalize a prescription."""
        response = await client.put(
            f"/api/v1/prescriptions/{test_prescription.prescription_id}/",
            json={"status": "FINALIZED"},
            headers={"Authorization": f"Bearer {doctor_token}"},
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_update_prescription_patient_forbidden(self, client, patient_user, patient_token, test_patient, test_prescription):
        """Test patient cannot update prescription."""
        response = await client.put(
            f"/api/v1/prescriptions/{test_prescription.prescription_id}/",
            json={"notes": "Patient trying to edit"},
            headers={"Authorization": f"Bearer {patient_token}"},
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_list_patient_prescriptions_patient(self, client, patient_user, patient_token, test_patient, test_prescription):
        """Test patient can list their own prescriptions."""
        response = await client.get(
            f"/api/v1/prescriptions/patient/{test_patient.patient_id}/",
            headers={"Authorization": f"Bearer {patient_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        assert len(data["prescriptions"]) >= 1

    @pytest.mark.asyncio
    async def test_list_patient_prescriptions_doctor(self, client, doctor_user, doctor_token, test_doctor, test_patient, test_prescription):
        """Test doctor can list their patient's prescriptions."""
        response = await client.get(
            f"/api/v1/prescriptions/patient/{test_patient.patient_id}/",
            headers={"Authorization": f"Bearer {doctor_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1

    @pytest.mark.asyncio
    async def test_list_patient_prescriptions_doctor_other_forbidden(self, client, another_doctor_user, another_doctor_token, another_doctor, test_patient, test_prescription):
        """Test doctor cannot list prescriptions for patient they don't treat."""
        response = await client.get(
            f"/api/v1/prescriptions/patient/{test_patient.patient_id}/",
            headers={"Authorization": f"Bearer {another_doctor_token}"},
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_list_patient_prescriptions_patient_other_forbidden(self, client, another_patient_user, another_patient_token, another_patient, test_patient, test_prescription):
        """Test patient cannot list another patient's prescriptions."""
        response = await client.get(
            f"/api/v1/prescriptions/patient/{test_patient.patient_id}/",
            headers={"Authorization": f"Bearer {another_patient_token}"},
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_list_patient_prescriptions_admin(self, client, admin_user, admin_token, test_patient, test_prescription):
        """Test admin can list any patient's prescriptions."""
        response = await client.get(
            f"/api/v1/prescriptions/patient/{test_patient.patient_id}/",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_list_patient_prescriptions_filter_status(self, client, admin_user, admin_token, test_patient, test_prescription):
        """Test filtering prescriptions by status."""
        response = await client.get(
            f"/api/v1/prescriptions/patient/{test_patient.patient_id}/?status=draft",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        for prescription in data["prescriptions"]:
            assert prescription["status"] == "DRAFT"

    @pytest.mark.asyncio
    async def test_list_patient_prescriptions_pagination(self, client, admin_user, admin_token, test_patient, test_prescription):
        """Test prescriptions pagination."""
        response = await client.get(
            f"/api/v1/prescriptions/patient/{test_patient.patient_id}/?page=1&page_size=10",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 1
        assert data["page_size"] == 10

    @pytest.mark.asyncio
    async def test_list_appointment_prescriptions(self, client, doctor_user, doctor_token, test_doctor, test_patient, test_appointment, test_prescription):
        """Test listing prescriptions for an appointment."""
        response = await client.get(
            f"/api/v1/prescriptions/appointment/{test_appointment.appointment_id}/",
            headers={"Authorization": f"Bearer {doctor_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1

    @pytest.mark.asyncio
    async def test_list_appointment_prescriptions_patient(self, client, patient_user, patient_token, test_patient, test_appointment, test_prescription):
        """Test patient can list prescriptions for their appointment."""
        response = await client.get(
            f"/api/v1/prescriptions/appointment/{test_appointment.appointment_id}/",
            headers={"Authorization": f"Bearer {patient_token}"},
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_list_appointment_prescriptions_doctor_other_forbidden(self, client, another_doctor_user, another_doctor_token, another_doctor, test_appointment, test_prescription):
        """Test doctor cannot list prescriptions for appointment they don't own."""
        response = await client.get(
            f"/api/v1/prescriptions/appointment/{test_appointment.appointment_id}/",
            headers={"Authorization": f"Bearer {another_doctor_token}"},
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_check_interactions_no_warnings(self, client, doctor_user, doctor_token, test_patient, test_appointment):
        """Test interaction check with no warnings."""
        response = await client.post(
            "/api/v1/prescriptions/check-interactions/",
            json={
                "patient_id": str(test_patient.patient_id),
                "medications": [
                    {"name": "Metoprolol", "dosage": "50mg", "frequency": "twice daily", "duration": "30 days"},
                    {"name": "Atorvastatin", "dosage": "20mg", "frequency": "once daily", "duration": "90 days"},
                ],
            },
            headers={"Authorization": f"Bearer {doctor_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "warnings" in data
        assert "has_warnings" in data

    @pytest.mark.asyncio
    async def test_check_interactions_warfarin_aspirin(self, client, doctor_user, doctor_token, test_patient, test_appointment):
        """Test interaction check detects warfarin-aspirin interaction."""
        response = await client.post(
            "/api/v1/prescriptions/check-interactions/",
            json={
                "patient_id": str(test_patient.patient_id),
                "medications": [
                    {"name": "Warfarin", "dosage": "5mg", "frequency": "once daily", "duration": "30 days"},
                    {"name": "Aspirin", "dosage": "81mg", "frequency": "once daily", "duration": "30 days"},
                ],
            },
            headers={"Authorization": f"Bearer {doctor_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["has_warnings"] is True
        assert len(data["warnings"]) >= 1
        # Check for the specific interaction
        interaction_warnings = [w for w in data["warnings"] if w["type"] == "interaction"]
        assert len(interaction_warnings) >= 1
        assert "warfarin" in interaction_warnings[0]["medication"].lower()
        assert "aspirin" in interaction_warnings[0]["medication"].lower()

    @pytest.mark.asyncio
    async def test_check_interactions_patient_forbidden(self, client, patient_user, patient_token, test_patient):
        """Test patient cannot check interactions."""
        response = await client.post(
            "/api/v1/prescriptions/check-interactions/",
            json={
                "patient_id": str(test_patient.patient_id),
                "medications": [
                    {"name": "Test", "dosage": "10mg", "frequency": "once daily", "duration": "30 days"},
                ],
            },
            headers={"Authorization": f"Bearer {patient_token}"},
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_check_interactions_doctor_other_forbidden(self, client, another_doctor_user, another_doctor_token, another_doctor, test_patient):
        """Test doctor cannot check interactions for patient they don't treat."""
        response = await client.post(
            "/api/v1/prescriptions/check-interactions/",
            json={
                "patient_id": str(test_patient.patient_id),
                "medications": [
                    {"name": "Test", "dosage": "10mg", "frequency": "once daily", "duration": "30 days"},
                ],
            },
            headers={"Authorization": f"Bearer {another_doctor_token}"},
        )
        assert response.status_code == 403