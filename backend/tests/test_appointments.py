"""Tests for Appointments API."""

from datetime import date, datetime, timedelta
from uuid import uuid4

import pytest
import pytest_asyncio

from app.models import Appointment, AppointmentStatus, Doctor, Patient, User, UserRole
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


class TestAppointmentsAPI:
    """Test Appointments API endpoints."""

    @pytest.mark.asyncio
    async def test_create_appointment_admin(self, client, admin_user, admin_token, test_patient, test_doctor):
        """Test creating an appointment as admin."""
        scheduled_at = datetime.utcnow() + timedelta(days=2)
        response = await client.post(
            "/api/v1/appointments/",
            json={
                "patient_id": str(test_patient.patient_id),
                "doctor_id": str(test_doctor.doctor_id),
                "scheduled_at": scheduled_at.isoformat(),
                "duration_minutes": 30,
                "notes": "Admin created appointment",
            },
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["patient_id"] == str(test_patient.patient_id)
        assert data["doctor_id"] == str(test_doctor.doctor_id)
        assert data["status"] == "scheduled"

    @pytest.mark.asyncio
    async def test_create_appointment_patient(self, client, patient_user, patient_token, test_patient, test_doctor):
        """Test creating an appointment as patient."""
        scheduled_at = datetime.utcnow() + timedelta(days=2)
        response = await client.post(
            "/api/v1/appointments/",
            json={
                "patient_id": str(test_patient.patient_id),
                "doctor_id": str(test_doctor.doctor_id),
                "scheduled_at": scheduled_at.isoformat(),
                "duration_minutes": 30,
                "notes": "Patient created appointment",
            },
            headers={"Authorization": f"Bearer {patient_token}"},
        )
        assert response.status_code == 201

    @pytest.mark.asyncio
    async def test_create_appointment_doctor(self, client, doctor_user, doctor_token, test_patient, test_doctor):
        """Test creating an appointment as doctor."""
        scheduled_at = datetime.utcnow() + timedelta(days=2)
        response = await client.post(
            "/api/v1/appointments/",
            json={
                "patient_id": str(test_patient.patient_id),
                "doctor_id": str(test_doctor.doctor_id),
                "scheduled_at": scheduled_at.isoformat(),
                "duration_minutes": 30,
                "notes": "Doctor created appointment",
            },
            headers={"Authorization": f"Bearer {doctor_token}"},
        )
        assert response.status_code == 201

    @pytest.mark.asyncio
    async def test_create_appointment_invalid_patient(self, client, admin_user, admin_token, test_doctor):
        """Test creating appointment with invalid patient fails."""
        scheduled_at = datetime.utcnow() + timedelta(days=2)
        response = await client.post(
            "/api/v1/appointments/",
            json={
                "patient_id": str(uuid4()),
                "doctor_id": str(test_doctor.doctor_id),
                "scheduled_at": scheduled_at.isoformat(),
                "duration_minutes": 30,
            },
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_create_appointment_invalid_doctor(self, client, admin_user, admin_token, test_patient):
        """Test creating appointment with invalid doctor fails."""
        scheduled_at = datetime.utcnow() + timedelta(days=2)
        response = await client.post(
            "/api/v1/appointments/",
            json={
                "patient_id": str(test_patient.patient_id),
                "doctor_id": str(uuid4()),
                "scheduled_at": scheduled_at.isoformat(),
                "duration_minutes": 30,
            },
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_create_appointment_double_booking_rejected(self, client, admin_user, admin_token, test_patient, test_doctor, test_appointment):
        """Test double-booking a doctor is rejected."""
        # Try to book at the same time as existing appointment
        response = await client.post(
            "/api/v1/appointments/",
            json={
                "patient_id": str(test_patient.patient_id),
                "doctor_id": str(test_doctor.doctor_id),
                "scheduled_at": test_appointment.scheduled_at.isoformat(),
                "duration_minutes": 30,
            },
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 409
        error_data = response.json()
        assert "error" in error_data
        assert "conflicting" in error_data["error"]["message"].lower()

    @pytest.mark.asyncio
    async def test_create_appointment_overlapping_rejected(self, client, admin_user, admin_token, test_patient, test_doctor, test_appointment):
        """Test overlapping appointment is rejected."""
        # Try to book 15 minutes before existing appointment (30 min duration overlaps)
        overlapping_time = test_appointment.scheduled_at - timedelta(minutes=15)
        response = await client.post(
            "/api/v1/appointments/",
            json={
                "patient_id": str(test_patient.patient_id),
                "doctor_id": str(test_doctor.doctor_id),
                "scheduled_at": overlapping_time.isoformat(),
                "duration_minutes": 30,
            },
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 409

    @pytest.mark.asyncio
    async def test_create_appointment_back_to_back_allowed(self, client, admin_user, admin_token, test_patient, test_doctor, test_appointment):
        """Test back-to-back appointments are allowed (no overlap)."""
        # Book exactly when previous appointment ends
        back_to_back_time = test_appointment.scheduled_at + timedelta(minutes=30)
        response = await client.post(
            "/api/v1/appointments/",
            json={
                "patient_id": str(test_patient.patient_id),
                "doctor_id": str(test_doctor.doctor_id),
                "scheduled_at": back_to_back_time.isoformat(),
                "duration_minutes": 30,
            },
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 201

    @pytest.mark.asyncio
    async def test_get_appointment_admin(self, client, admin_user, admin_token, test_appointment):
        """Test admin can read any appointment."""
        response = await client.get(
            f"/api/v1/appointments/{test_appointment.appointment_id}/",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["appointment_id"] == str(test_appointment.appointment_id)

    @pytest.mark.asyncio
    async def test_get_appointment_patient_own(self, client, patient_user, patient_token, test_patient, test_appointment):
        """Test patient can read their own appointment."""
        response = await client.get(
            f"/api/v1/appointments/{test_appointment.appointment_id}/",
            headers={"Authorization": f"Bearer {patient_token}"},
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_get_appointment_doctor_own(self, client, doctor_user, doctor_token, test_doctor, test_appointment):
        """Test doctor can read their own appointment."""
        response = await client.get(
            f"/api/v1/appointments/{test_appointment.appointment_id}/",
            headers={"Authorization": f"Bearer {doctor_token}"},
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_get_appointment_patient_other_forbidden(self, client, admin_user, admin_token, test_patient, test_doctor, test_appointment, db_session):
        """Test patient cannot read another patient's appointment."""
        # Create another patient
        another_patient_user = User(
            user_id=uuid4(),
            email="patient2@test.com",
            hashed_password=get_password_hash("patientpassword123"),
            full_name="Test Patient 2",
            role=UserRole.PATIENT,
            is_active=True,
        )
        db_session.add(another_patient_user)
        await db_session.commit()
        await db_session.refresh(another_patient_user)
        
        another_patient = Patient(
            patient_id=uuid4(),
            user_id=another_patient_user.user_id,
            abha_address="patient2@abdm",
            full_name="Test Patient 2",
            date_of_birth=date(1990, 1, 1),
            gender="female",
            phone="+91-9876543210",
            email="patient2@test.com",
        )
        db_session.add(another_patient)
        await db_session.commit()
        await db_session.refresh(another_patient)
        
        another_patient_token = create_access_token(data={"sub": str(another_patient_user.user_id), "email": another_patient_user.email, "role": another_patient_user.role.value})
        
        response = await client.get(
            f"/api/v1/appointments/{test_appointment.appointment_id}/",
            headers={"Authorization": f"Bearer {another_patient_token}"},
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_get_appointment_not_found(self, client, admin_user, admin_token):
        """Test getting non-existent appointment returns 404."""
        response = await client.get(
            f"/api/v1/appointments/{uuid4()}/",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_appointment_admin(self, client, admin_user, admin_token, test_appointment):
        """Test admin can update any appointment."""
        new_time = datetime.utcnow() + timedelta(days=3)
        response = await client.put(
            f"/api/v1/appointments/{test_appointment.appointment_id}/",
            json={
                "scheduled_at": new_time.isoformat(),
                "duration_minutes": 45,
                "notes": "Updated by admin",
            },
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["duration_minutes"] == 45
        assert data["notes"] == "Updated by admin"

    @pytest.mark.asyncio
    async def test_update_appointment_patient_own(self, client, patient_user, patient_token, test_patient, test_appointment):
        """Test patient can update their own appointment."""
        new_time = datetime.utcnow() + timedelta(days=3)
        response = await client.put(
            f"/api/v1/appointments/{test_appointment.appointment_id}/",
            json={
                "scheduled_at": new_time.isoformat(),
                "notes": "Updated by patient",
            },
            headers={"Authorization": f"Bearer {patient_token}"},
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_update_appointment_doctor_own(self, client, doctor_user, doctor_token, test_doctor, test_appointment):
        """Test doctor can update their own appointment."""
        new_time = datetime.utcnow() + timedelta(days=3)
        response = await client.put(
            f"/api/v1/appointments/{test_appointment.appointment_id}/",
            json={
                "scheduled_at": new_time.isoformat(),
                "notes": "Updated by doctor",
            },
            headers={"Authorization": f"Bearer {doctor_token}"},
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_update_appointment_double_booking_rejected(self, client, admin_user, admin_token, test_patient, test_doctor, test_appointment, db_session):
        """Test updating appointment to conflicting time is rejected."""
        # Create another appointment for the same doctor at a different time
        another_appointment = Appointment(
            appointment_id=uuid4(),
            patient_id=test_patient.patient_id,
            doctor_id=test_doctor.doctor_id,
            scheduled_at=datetime.utcnow() + timedelta(days=5),
            duration_minutes=30,
            status=AppointmentStatus.SCHEDULED,
        )
        db_session.add(another_appointment)
        await db_session.commit()
        await db_session.refresh(another_appointment)
        
        # Try to update test_appointment to conflict with another_appointment
        conflicting_time = another_appointment.scheduled_at - timedelta(minutes=15)
        response = await client.put(
            f"/api/v1/appointments/{test_appointment.appointment_id}/",
            json={
                "scheduled_at": conflicting_time.isoformat(),
                "duration_minutes": 30,
            },
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 409

    @pytest.mark.asyncio
    async def test_delete_appointment_admin(self, client, admin_user, admin_token, test_appointment):
        """Test admin can delete any appointment."""
        response = await client.delete(
            f"/api/v1/appointments/{test_appointment.appointment_id}/",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 204
        
        # Verify it's cancelled
        get_response = await client.get(
            f"/api/v1/appointments/{test_appointment.appointment_id}/",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert get_response.status_code == 200
        assert get_response.json()["status"] == "cancelled"

    @pytest.mark.asyncio
    async def test_delete_appointment_patient_own(self, client, patient_user, patient_token, test_patient, test_appointment):
        """Test patient can delete their own appointment."""
        response = await client.delete(
            f"/api/v1/appointments/{test_appointment.appointment_id}/",
            headers={"Authorization": f"Bearer {patient_token}"},
        )
        assert response.status_code == 204

    @pytest.mark.asyncio
    async def test_delete_appointment_doctor_own(self, client, doctor_user, doctor_token, test_doctor, test_appointment):
        """Test doctor can delete their own appointment."""
        response = await client.delete(
            f"/api/v1/appointments/{test_appointment.appointment_id}/",
            headers={"Authorization": f"Bearer {doctor_token}"},
        )
        assert response.status_code == 204

    @pytest.mark.asyncio
    async def test_list_appointments_admin(self, client, admin_user, admin_token, test_appointment):
        """Test admin can list all appointments."""
        response = await client.get(
            "/api/v1/appointments/",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        assert len(data["appointments"]) >= 1

    @pytest.mark.asyncio
    async def test_list_appointments_patient(self, client, patient_user, patient_token, test_patient, test_appointment):
        """Test patient can list their own appointments."""
        response = await client.get(
            "/api/v1/appointments/",
            headers={"Authorization": f"Bearer {patient_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1

    @pytest.mark.asyncio
    async def test_list_appointments_doctor(self, client, doctor_user, doctor_token, test_doctor, test_appointment):
        """Test doctor can list their own appointments."""
        response = await client.get(
            "/api/v1/appointments/",
            headers={"Authorization": f"Bearer {doctor_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1

    @pytest.mark.asyncio
    async def test_list_appointments_pagination(self, client, admin_user, admin_token, test_appointment):
        """Test appointment list pagination."""
        response = await client.get(
            "/api/v1/appointments/?page=1&page_size=10",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 1
        assert data["page_size"] == 10

    @pytest.mark.asyncio
    async def test_list_appointments_filter_by_patient(self, client, admin_user, admin_token, test_patient, test_appointment):
        """Test appointment list filter by patient."""
        response = await client.get(
            f"/api/v1/appointments/?patient_id={test_patient.patient_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        for appt in data["appointments"]:
            assert appt["patient_id"] == str(test_patient.patient_id)

    @pytest.mark.asyncio
    async def test_list_appointments_filter_by_doctor(self, client, admin_user, admin_token, test_doctor, test_appointment):
        """Test appointment list filter by doctor."""
        response = await client.get(
            f"/api/v1/appointments/?doctor_id={test_doctor.doctor_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        for appt in data["appointments"]:
            assert appt["doctor_id"] == str(test_doctor.doctor_id)

    @pytest.mark.asyncio
    async def test_list_appointments_filter_by_status(self, client, admin_user, admin_token, test_appointment):
        """Test appointment list filter by status."""
        response = await client.get(
            "/api/v1/appointments/?status=scheduled",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        for appt in data["appointments"]:
            assert appt["status"] == "scheduled"

    @pytest.mark.asyncio
    async def test_list_appointments_filter_by_date_range(self, client, admin_user, admin_token, test_appointment):
        """Test appointment list filter by date range."""
        date_from = (datetime.utcnow() - timedelta(days=1)).isoformat()
        date_to = (datetime.utcnow() + timedelta(days=2)).isoformat()
        response = await client.get(
            f"/api/v1/appointments/?date_from={date_from}&date_to={date_to}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1