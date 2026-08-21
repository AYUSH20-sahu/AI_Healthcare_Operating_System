"""Tests for Voice Notes API."""

from datetime import date, datetime, timedelta
from io import BytesIO
from uuid import uuid4

import pytest
import pytest_asyncio

from app.models import (
    Appointment,
    AppointmentStatus,
    Doctor,
    Patient,
    User,
    UserRole,
    VoiceNote,
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
async def test_voice_note(db_session, test_appointment, test_doctor, test_patient):
    """Create a test voice note."""
    voice_note = VoiceNote(
        voice_note_id=uuid4(),
        appointment_id=test_appointment.appointment_id,
        doctor_id=test_doctor.doctor_id,
        patient_id=test_patient.patient_id,
        file_path="/storage/voice_notes/test.webm",
        file_name="test.webm",
        content_type="audio/webm",
        file_size=1024,
        duration_seconds=60,
        transcription="Test transcription",
        transcription_status="completed",
    )
    db_session.add(voice_note)
    await db_session.commit()
    await db_session.refresh(voice_note)
    return voice_note


class TestVoiceNotesAPI:
    """Test Voice Notes API endpoints."""

    @pytest.mark.asyncio
    async def test_upload_voice_note_doctor(self, client, doctor_user, doctor_token, test_doctor, test_appointment):
        """Test uploading a voice note as doctor."""
        # Create a mock audio file
        audio_content = b"fake audio content"
        audio_file = BytesIO(audio_content)
        
        response = await client.post(
            "/api/v1/voice-notes/upload/",
            data={"appointment_id": str(test_appointment.appointment_id)},
            files={"file": ("test.webm", audio_file, "audio/webm")},
            headers={"Authorization": f"Bearer {doctor_token}"},
        )
        assert response.status_code == 201
        data = response.json()
        assert "voice_note_id" in data
        assert data["message"] == "Voice note uploaded successfully"

    @pytest.mark.asyncio
    async def test_upload_voice_note_admin(self, client, admin_user, admin_token, test_doctor, test_appointment):
        """Test uploading a voice note as admin."""
        audio_content = b"fake audio content"
        audio_file = BytesIO(audio_content)
        
        response = await client.post(
            "/api/v1/voice-notes/upload/",
            data={"appointment_id": str(test_appointment.appointment_id)},
            files={"file": ("test.webm", audio_file, "audio/webm")},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 201

    @pytest.mark.asyncio
    async def test_upload_voice_note_patient_forbidden(self, client, patient_user, patient_token, test_appointment):
        """Test uploading a voice note as patient is forbidden."""
        audio_content = b"fake audio content"
        audio_file = BytesIO(audio_content)
        
        response = await client.post(
            "/api/v1/voice-notes/upload/",
            data={"appointment_id": str(test_appointment.appointment_id)},
            files={"file": ("test.webm", audio_file, "audio/webm")},
            headers={"Authorization": f"Bearer {patient_token}"},
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_upload_voice_note_invalid_appointment(self, client, doctor_user, doctor_token, test_doctor):
        """Test uploading voice note with invalid appointment fails."""
        audio_content = b"fake audio content"
        audio_file = BytesIO(audio_content)
        
        response = await client.post(
            "/api/v1/voice-notes/upload/",
            data={"appointment_id": str(uuid4())},
            files={"file": ("test.webm", audio_file, "audio/webm")},
            headers={"Authorization": f"Bearer {doctor_token}"},
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_upload_voice_note_doctor_mismatch(self, client, another_doctor_user, another_doctor_token, another_doctor, test_appointment):
        """Test doctor cannot upload voice note for another doctor's appointment."""
        audio_content = b"fake audio content"
        audio_file = BytesIO(audio_content)
        
        response = await client.post(
            "/api/v1/voice-notes/upload/",
            data={"appointment_id": str(test_appointment.appointment_id)},
            files={"file": ("test.webm", audio_file, "audio/webm")},
            headers={"Authorization": f"Bearer {another_doctor_token}"},
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_upload_voice_note_invalid_file_type(self, client, doctor_user, doctor_token, test_doctor, test_appointment):
        """Test uploading voice note with invalid file type fails."""
        audio_content = b"fake text content"
        audio_file = BytesIO(audio_content)
        
        response = await client.post(
            "/api/v1/voice-notes/upload/",
            data={"appointment_id": str(test_appointment.appointment_id)},
            files={"file": ("test.txt", audio_file, "text/plain")},
            headers={"Authorization": f"Bearer {doctor_token}"},
        )
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_get_voice_note_doctor_own(self, client, doctor_user, doctor_token, test_doctor, test_voice_note):
        """Test doctor can get their own voice note."""
        response = await client.get(
            f"/api/v1/voice-notes/{test_voice_note.voice_note_id}/",
            headers={"Authorization": f"Bearer {doctor_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["voice_note_id"] == str(test_voice_note.voice_note_id)
        assert data["file_name"] == test_voice_note.file_name

    @pytest.mark.asyncio
    async def test_get_voice_note_patient_own(self, client, patient_user, patient_token, test_patient, test_voice_note):
        """Test patient can get their own voice note."""
        response = await client.get(
            f"/api/v1/voice-notes/{test_voice_note.voice_note_id}/",
            headers={"Authorization": f"Bearer {patient_token}"},
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_get_voice_note_admin(self, client, admin_user, admin_token, test_voice_note):
        """Test admin can get any voice note."""
        response = await client.get(
            f"/api/v1/voice-notes/{test_voice_note.voice_note_id}/",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_get_voice_note_doctor_other_forbidden(self, client, another_doctor_user, another_doctor_token, test_voice_note):
        """Test doctor cannot get another doctor's voice note."""
        response = await client.get(
            f"/api/v1/voice-notes/{test_voice_note.voice_note_id}/",
            headers={"Authorization": f"Bearer {another_doctor_token}"},
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_get_voice_note_patient_other_forbidden(self, client, another_patient_user, another_patient_token, another_patient, test_voice_note):
        """Test patient cannot get another patient's voice note."""
        response = await client.get(
            f"/api/v1/voice-notes/{test_voice_note.voice_note_id}/",
            headers={"Authorization": f"Bearer {another_patient_token}"},
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_get_voice_note_not_found(self, client, admin_user, admin_token):
        """Test getting non-existent voice note returns 404."""
        response = await client.get(
            f"/api/v1/voice-notes/{uuid4()}/",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_list_appointment_voice_notes_doctor(self, client, doctor_user, doctor_token, test_doctor, test_appointment, test_voice_note):
        """Test doctor can list voice notes for their appointment."""
        response = await client.get(
            f"/api/v1/voice-notes/appointment/{test_appointment.appointment_id}/",
            headers={"Authorization": f"Bearer {doctor_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1

    @pytest.mark.asyncio
    async def test_list_appointment_voice_notes_patient(self, client, patient_user, patient_token, test_patient, test_appointment, test_voice_note):
        """Test patient can list voice notes for their appointment."""
        response = await client.get(
            f"/api/v1/voice-notes/appointment/{test_appointment.appointment_id}/",
            headers={"Authorization": f"Bearer {patient_token}"},
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_list_appointment_voice_notes_doctor_other_forbidden(self, client, another_doctor_user, another_doctor_token, another_doctor, test_appointment, test_voice_note):
        """Test doctor cannot list voice notes for appointment they don't own."""
        response = await client.get(
            f"/api/v1/voice-notes/appointment/{test_appointment.appointment_id}/",
            headers={"Authorization": f"Bearer {another_doctor_token}"},
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_update_voice_note_doctor_own(self, client, doctor_user, doctor_token, test_doctor, test_voice_note):
        """Test doctor can update their own voice note (add transcription)."""
        response = await client.put(
            f"/api/v1/voice-notes/{test_voice_note.voice_note_id}/",
            json={
                "transcription": "Updated transcription text",
                "transcription_status": "completed",
            },
            headers={"Authorization": f"Bearer {doctor_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["transcription"] == "Updated transcription text"
        assert data["transcription_status"] == "completed"

    @pytest.mark.asyncio
    async def test_update_voice_note_admin(self, client, admin_user, admin_token, test_voice_note):
        """Test admin can update any voice note."""
        response = await client.put(
            f"/api/v1/voice-notes/{test_voice_note.voice_note_id}/",
            json={
                "transcription": "Admin updated transcription",
                "transcription_status": "completed",
            },
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["transcription"] == "Admin updated transcription"

    @pytest.mark.asyncio
    async def test_update_voice_note_doctor_other_forbidden(self, client, another_doctor_user, another_doctor_token, test_voice_note):
        """Test doctor cannot update another doctor's voice note."""
        response = await client.put(
            f"/api/v1/voice-notes/{test_voice_note.voice_note_id}/",
            json={"transcription": "Trying to update"},
            headers={"Authorization": f"Bearer {another_doctor_token}"},
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_update_voice_note_patient_forbidden(self, client, patient_user, patient_token, test_patient, test_voice_note):
        """Test patient cannot update voice note."""
        response = await client.put(
            f"/api/v1/voice-notes/{test_voice_note.voice_note_id}/",
            json={"transcription": "Patient trying to update"},
            headers={"Authorization": f"Bearer {patient_token}"},
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_delete_voice_note_doctor_own(self, client, doctor_user, doctor_token, test_doctor, test_voice_note):
        """Test doctor can delete their own voice note."""
        response = await client.delete(
            f"/api/v1/voice-notes/{test_voice_note.voice_note_id}/",
            headers={"Authorization": f"Bearer {doctor_token}"},
        )
        assert response.status_code == 204

    @pytest.mark.asyncio
    async def test_delete_voice_note_admin(self, client, admin_user, admin_token, test_voice_note):
        """Test admin can delete any voice note."""
        response = await client.delete(
            f"/api/v1/voice-notes/{test_voice_note.voice_note_id}/",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 204

    @pytest.mark.asyncio
    async def test_delete_voice_note_doctor_other_forbidden(self, client, another_doctor_user, another_doctor_token, test_voice_note):
        """Test doctor cannot delete another doctor's voice note."""
        response = await client.delete(
            f"/api/v1/voice-notes/{test_voice_note.voice_note_id}/",
            headers={"Authorization": f"Bearer {another_doctor_token}"},
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_delete_voice_note_patient_forbidden(self, client, patient_user, patient_token, test_patient, test_voice_note):
        """Test patient cannot delete voice note."""
        response = await client.delete(
            f"/api/v1/voice-notes/{test_voice_note.voice_note_id}/",
            headers={"Authorization": f"Bearer {patient_token}"},
        )
        assert response.status_code == 403