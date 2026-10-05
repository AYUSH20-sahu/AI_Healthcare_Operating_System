"""Automated Test Suite for Horizon C: WebRTC Media Engine, Coturn ICE, and Ambient Audio Scribe Pipe.

Validates:
1. Coturn REST API authentication & HMAC-SHA1 ICE credential generation.
2. ICE credential verification and anti-tamper / expiration checks.
3. API Endpoint: GET /api/v1/telehealth/ice-servers.
4. Telehealth room token returning authenticated Coturn ICE servers.
5. Server-side AES-256-GCM authenticated encryption for consultation recordings.
6. Recording upload, status check, and on-the-fly decrypted download.
7. Real-time audio chunk stream ingestion (POST /api/v1/voice-notes/stream/appointment/{id}).
"""

import io
import pytest
import pytest_asyncio
from datetime import datetime
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models import (
    Appointment,
    AppointmentStatus,
    Doctor,
    Patient,
    User,
    UserRole,
)
from app.services.auth.service import create_access_token, get_password_hash
from app.services.telehealth_media import TelehealthMediaService


@pytest_asyncio.fixture
async def horizon_c_test_data(db_session: AsyncSession):
    """Seed test doctor, patient, and appointment for Horizon C test suite."""
    # 1. Doctor
    doc_user = User(
        email="doctor.horizon_c@test.com",
        hashed_password=get_password_hash("password123"),
        full_name="Dr. Elena Rostova",
        role=UserRole.DOCTOR,
        is_active=True,
    )
    db_session.add(doc_user)
    await db_session.flush()

    doctor = Doctor(
        user_id=doc_user.user_id,
        license_number="LIC-HORIZON-C-001",
        specialty="Telehealth Cardiology",
        full_name="Dr. Elena Rostova",
        email="doctor.horizon_c@test.com",
    )
    db_session.add(doctor)

    # 2. Patient
    pat_user = User(
        email="patient.horizon_c@test.com",
        hashed_password=get_password_hash("password123"),
        full_name="Vikram Seth",
        role=UserRole.PATIENT,
        is_active=True,
    )
    db_session.add(pat_user)
    await db_session.flush()

    patient = Patient(
        user_id=pat_user.user_id,
        full_name="Vikram Seth",
        date_of_birth=datetime(1985, 4, 12).date(),
        phone="+919876543299",
    )
    db_session.add(patient)
    await db_session.flush()

    # 3. Appointment
    appointment = Appointment(
        patient_id=patient.patient_id,
        doctor_id=doctor.doctor_id,
        scheduled_at=datetime.utcnow(),
        duration_minutes=30,
        status=AppointmentStatus.IN_PROGRESS,
    )
    db_session.add(appointment)
    await db_session.commit()

    await db_session.refresh(doc_user)
    await db_session.refresh(pat_user)
    await db_session.refresh(appointment)

    doc_token = create_access_token({"sub": str(doc_user.user_id), "email": doc_user.email, "role": "DOCTOR"})
    pat_token = create_access_token({"sub": str(pat_user.user_id), "email": pat_user.email, "role": "PATIENT"})

    return {
        "doctor_user": doc_user,
        "patient_user": pat_user,
        "doctor": doctor,
        "patient": patient,
        "appointment": appointment,
        "doc_token": doc_token,
        "pat_token": pat_token,
    }


# ─── 1. Coturn ICE Credential Engine Tests ────────────────────────────────────

def test_coturn_ice_credential_generation():
    """Verify standard Coturn REST API HMAC-SHA1 credential format and calculation."""
    user_id = "dr.elena.rostova@ai-hos.hospital"
    ice_config = TelehealthMediaService.generate_ice_servers(user_identifier=user_id, ttl_seconds=3600)

    assert "ice_servers" in ice_config
    assert len(ice_config["ice_servers"]) >= 2
    assert ice_config["ttl"] == 3600
    assert ice_config["realm"] == settings.COTURN_REALM

    turn_cfg = next((s for s in ice_config["ice_servers"] if "turn:" in str(s.get("urls"))), None)
    assert turn_cfg is not None
    assert "username" in turn_cfg
    assert "credential" in turn_cfg

    # Username format must be <timestamp>:<user_identifier>
    parts = turn_cfg["username"].split(":", 1)
    assert len(parts) == 2
    assert parts[1] == user_id

    # Verify signature
    assert TelehealthMediaService.verify_ice_credential(turn_cfg["username"], turn_cfg["credential"]) is True


def test_coturn_ice_credential_anti_tamper_and_expiration():
    """Verify tampered and expired credentials fail authentication."""
    user_id = "doctor@test.com"
    # Generate expired credential (TTL = -10 seconds)
    ice_config = TelehealthMediaService.generate_ice_servers(user_identifier=user_id, ttl_seconds=-10)
    turn_cfg = ice_config["ice_servers"][1]

    # Expired must be rejected
    assert TelehealthMediaService.verify_ice_credential(turn_cfg["username"], turn_cfg["credential"]) is False

    # Valid credential with forged signature must be rejected
    valid_config = TelehealthMediaService.generate_ice_servers(user_identifier=user_id, ttl_seconds=3600)
    valid_turn = valid_config["ice_servers"][1]
    assert TelehealthMediaService.verify_ice_credential(valid_turn["username"], "forged_invalid_credential_base64==") is False


# ─── 2. Telehealth API Endpoints Tests ────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_ice_servers_endpoint(async_client: AsyncClient, horizon_c_test_data):
    """Verify GET /api/v1/telehealth/ice-servers delivers authenticated TURN/STUN servers."""
    doc_token = horizon_c_test_data["doc_token"]

    response = await async_client.get(
        "/api/v1/telehealth/ice-servers",
        headers={"Authorization": f"Bearer {doc_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "ice_servers" in data
    assert "ttl" in data
    assert any("turn:" in str(s.get("urls")) for s in data["ice_servers"])


@pytest.mark.asyncio
async def test_room_token_returns_ice_servers(async_client: AsyncClient, horizon_c_test_data):
    """Verify GET /api/v1/telehealth/room/{appointment_id}/token includes Coturn ICE servers."""
    doc_token = horizon_c_test_data["doc_token"]
    appt_id = horizon_c_test_data["appointment"].appointment_id

    response = await async_client.get(
        f"/api/v1/telehealth/room/{appt_id}/token",
        headers={"Authorization": f"Bearer {doc_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["appointment_id"] == str(appt_id)
    assert data["peer_role"] == "doctor"
    assert "ice_servers" in data
    assert len(data["ice_servers"]) >= 2


# ─── 3. AES-256-GCM Encrypted Consultation Recording Storage Tests ───────────

def test_aes_256_gcm_storage_roundtrip():
    """Verify TelehealthMediaService encrypts on disk with AES-256-GCM and decrypts with integrity verification."""
    appointment_id = "test-appt-horizon-c-001"
    raw_video_bytes = b"RIFF....WEBM-MOCK-CLINICAL-CONSULTATION-VIDEO-STREAM-BYTES-1234567890"

    # Store recording
    meta = TelehealthMediaService.store_recording(
        appointment_id=appointment_id,
        file_bytes=raw_video_bytes,
        filename="test_consultation.webm",
        duration_seconds=125,
    )
    assert meta["encryption_algorithm"] == "AES-256-GCM"
    assert meta["duration_seconds"] == 125
    assert meta["plaintext_bytes"] == len(raw_video_bytes)

    # Check on-disk file is NOT plaintext
    storage_path = meta["storage_path"]
    with open(storage_path, "rb") as f:
        stored_bytes = f.read()
    assert raw_video_bytes not in stored_bytes

    # Retrieve and decrypt
    decrypted, retrieved_meta = TelehealthMediaService.retrieve_recording(appointment_id)
    assert decrypted == raw_video_bytes
    assert retrieved_meta["plaintext_sha256"] == meta["plaintext_sha256"]


@pytest.mark.asyncio
async def test_consultation_recording_upload_status_and_download(async_client: AsyncClient, horizon_c_test_data):
    """Verify recording upload, metadata status inspection, and decrypted streaming download."""
    doc_token = horizon_c_test_data["doc_token"]
    appt_id = horizon_c_test_data["appointment"].appointment_id
    video_content = b"SIMULATED-WEBM-TELEHEALTH-ENCOUNTER-VIDEO-AUDIO-DATA"

    # 1. Upload recording
    files = {"file": ("consultation_call.webm", io.BytesIO(video_content), "video/webm")}
    data = {"duration_seconds": "95"}
    upload_res = await async_client.post(
        f"/api/v1/telehealth/room/{appt_id}/recording",
        headers={"Authorization": f"Bearer {doc_token}"},
        files=files,
        data=data,
    )
    assert upload_res.status_code == 200
    upload_data = upload_res.json()
    assert upload_data["success"] is True
    assert upload_data["metadata"]["encryption_algorithm"] == "AES-256-GCM"
    assert upload_data["metadata"]["duration_seconds"] == 95

    # 2. Check recording status
    status_res = await async_client.get(
        f"/api/v1/telehealth/room/{appt_id}/recording/status",
        headers={"Authorization": f"Bearer {doc_token}"},
    )
    assert status_res.status_code == 200
    status_data = status_res.json()
    assert status_data["has_recording"] is True
    assert status_data["metadata"]["encryption_algorithm"] == "AES-256-GCM"

    # 3. Download and verify on-the-fly decryption
    download_res = await async_client.get(
        f"/api/v1/telehealth/room/{appt_id}/recording/download",
        headers={"Authorization": f"Bearer {doc_token}"},
    )
    assert download_res.status_code == 200
    assert download_res.headers.get("X-Encryption-Verified") == "AES-256-GCM"
    assert download_res.content == video_content


# ─── 4. Ambient Scribe Live Audio Chunk Streaming Tests ───────────────────────

@pytest.mark.asyncio
async def test_audio_chunk_streaming_pipe(async_client: AsyncClient, horizon_c_test_data):
    """Verify 5-second WebM audio chunks stream into voice notes and aggregate incremental transcripts."""
    doc_token = horizon_c_test_data["doc_token"]
    appt_id = horizon_c_test_data["appointment"].appointment_id

    # Chunk 0
    chunk0_data = b"AUDIO-CHUNK-0-PATIENT-FEVER-AND-COUGH"
    files0 = {"chunk": ("chunk_0.webm", io.BytesIO(chunk0_data), "audio/webm")}
    data0 = {"sequence_number": "0", "is_final": "false"}

    res0 = await async_client.post(
        f"/api/v1/voice-notes/stream/appointment/{appt_id}",
        headers={"Authorization": f"Bearer {doc_token}"},
        files=files0,
        data=data0,
    )
    assert res0.status_code == 200
    resp0 = res0.json()
    assert resp0["sequence_number"] == 0
    assert resp0["status"] == "in_progress"
    v_id = resp0["voice_note_id"]
    assert v_id is not None

    # Chunk 1 (final)
    chunk1_data = b"AUDIO-CHUNK-1-DOCTOR-PRESCRIBING-PARACETAMOL"
    files1 = {"chunk": ("chunk_1.webm", io.BytesIO(chunk1_data), "audio/webm")}
    data1 = {"sequence_number": "1", "is_final": "true"}

    res1 = await async_client.post(
        f"/api/v1/voice-notes/{v_id}/stream",
        headers={"Authorization": f"Bearer {doc_token}"},
        files=files1,
        data=data1,
    )
    assert res1.status_code == 200
    resp1 = res1.json()
    assert resp1["sequence_number"] == 1
    assert resp1["is_final"] is True
    assert resp1["status"] == "completed"


def test_s3_sync_fallback():
    """Verify S3/MinIO sync fallback behaves gracefully when bucket or credentials are not configured."""
    meta = {"original_filename": "recording.webm", "content_type": "video/webm"}
    # When no S3 bucket configured, returns False without crashing, preserving local AES-256 vault
    synced = TelehealthMediaService.sync_to_s3_storage("test-appt-001", b"dummy-data", meta)
    assert synced is False
    assert meta.get("s3_synced") is False or "s3_synced" not in meta

