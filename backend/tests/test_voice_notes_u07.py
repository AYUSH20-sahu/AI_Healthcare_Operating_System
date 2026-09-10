"""Test suite for Milestone U-07: Consultation + Voice Note Full-Stack Workflow.

Validates:
1. Authorized doctor can upload audio recording with duration_seconds.
2. Voice note metadata (file size, duration, status) is stored in PostgreSQL.
3. Audio streaming endpoint GET /api/v1/voice-notes/{id}/audio works for in-browser playback.
4. Patient of the appointment can stream the recorded consultation audio.
5. Patient cannot upload voice notes (HTTP 403).
6. Doctor cannot upload voice note for another doctor's appointment (HTTP 403).
7. Invalid audio MIME type is rejected (HTTP 400).
8. Empty (0-byte) audio file is rejected (HTTP 400).
9. Upload action is recorded in immutable audit_logs.
"""

from io import BytesIO
from uuid import uuid4
import pytest
from sqlalchemy import select

from app.models import AuditLog, VoiceNote


@pytest.mark.asyncio
class TestMilestoneU07VoiceNoteWorkflow:
    """Full-stack integration tests for U-07."""

    async def test_doctor_upload_voice_note_with_duration(
        self, client, doctor_token, test_doctor, test_appointment, db_session
    ):
        """1 & 2. Doctor can upload voice note with duration_seconds and file metadata."""
        audio_content = b"RIFF....WAVEfmt ....data" + b"\x00" * 256
        files = {"file": ("consultation.webm", BytesIO(audio_content), "audio/webm")}
        data = {
            "appointment_id": str(test_appointment.appointment_id),
            "duration_seconds": "48",
        }
        headers = {"Authorization": f"Bearer {doctor_token}"}

        res = await client.post("/api/v1/voice-notes/upload/", files=files, data=data, headers=headers)
        assert res.status_code == 201
        res_data = res.json()
        assert "voice_note_id" in res_data
        vn_id = res_data["voice_note_id"]

        # Verify DB metadata
        db_res = await db_session.execute(select(VoiceNote).where(VoiceNote.voice_note_id == vn_id))
        vn = db_res.scalar_one_or_none()
        assert vn is not None
        assert vn.duration_seconds == 48
        assert vn.content_type == "audio/webm"
        assert vn.file_size == len(audio_content)
        assert vn.transcription_status == "pending"

    async def test_stream_voice_note_audio(
        self, client, doctor_token, test_doctor, test_appointment, db_session
    ):
        """3. GET /api/v1/voice-notes/{id}/audio streams audio file with correct media type."""
        audio_content = b"ID3\x03\x00\x00\x00" + b"\xff\xfb\x90" * 30
        files = {"file": ("consultation.mp3", BytesIO(audio_content), "audio/mp3")}
        data = {
            "appointment_id": str(test_appointment.appointment_id),
            "duration_seconds": "15",
        }
        headers = {"Authorization": f"Bearer {doctor_token}"}

        upload_res = await client.post("/api/v1/voice-notes/upload/", files=files, data=data, headers=headers)
        assert upload_res.status_code == 201
        vn_id = upload_res.json()["voice_note_id"]

        # Stream audio
        stream_res = await client.get(f"/api/v1/voice-notes/{vn_id}/audio", headers=headers)
        assert stream_res.status_code == 200
        assert "audio/mp3" in stream_res.headers.get("content-type", "")
        assert stream_res.content == audio_content

    async def test_patient_can_stream_own_consultation_audio(
        self, client, doctor_token, patient_token, test_doctor, test_patient, test_appointment
    ):
        """4. Patient associated with the appointment can stream the recorded consultation audio."""
        audio_content = b"OGG-STREAM-TEST-AUDIO-DATA"
        files = {"file": ("consultation.ogg", BytesIO(audio_content), "audio/ogg")}
        data = {"appointment_id": str(test_appointment.appointment_id)}
        doc_headers = {"Authorization": f"Bearer {doctor_token}"}

        upload_res = await client.post("/api/v1/voice-notes/upload/", files=files, data=data, headers=doc_headers)
        assert upload_res.status_code == 201
        vn_id = upload_res.json()["voice_note_id"]

        # Patient streams audio
        pat_headers = {"Authorization": f"Bearer {patient_token}"}
        pat_stream_res = await client.get(f"/api/v1/voice-notes/{vn_id}/audio", headers=pat_headers)
        assert pat_stream_res.status_code == 200
        assert pat_stream_res.content == audio_content

    async def test_patient_cannot_upload_voice_note(
        self, client, patient_token, test_appointment
    ):
        """5. Patient cannot upload a voice note (HTTP 403)."""
        files = {"file": ("test.webm", BytesIO(b"AUDIO"), "audio/webm")}
        data = {"appointment_id": str(test_appointment.appointment_id)}
        headers = {"Authorization": f"Bearer {patient_token}"}

        res = await client.post("/api/v1/voice-notes/upload/", files=files, data=data, headers=headers)
        assert res.status_code == 403

    async def test_doctor_cannot_upload_for_other_doctor_appointment(
        self, client, another_doctor_token, another_doctor, test_appointment
    ):
        """6. Doctor B cannot upload a voice note for Doctor A's appointment (HTTP 403)."""
        files = {"file": ("test.webm", BytesIO(b"AUDIO"), "audio/webm")}
        data = {"appointment_id": str(test_appointment.appointment_id)}
        headers = {"Authorization": f"Bearer {another_doctor_token}"}

        res = await client.post("/api/v1/voice-notes/upload/", files=files, data=data, headers=headers)
        assert res.status_code == 403

    async def test_invalid_audio_content_type_rejected(
        self, client, doctor_token, test_doctor, test_appointment
    ):
        """7. Disallowed non-audio MIME types are rejected with HTTP 400."""
        files = {"file": ("malicious.exe", BytesIO(b"EXE-DATA"), "application/octet-stream")}
        data = {"appointment_id": str(test_appointment.appointment_id)}
        headers = {"Authorization": f"Bearer {doctor_token}"}

        res = await client.post("/api/v1/voice-notes/upload/", files=files, data=data, headers=headers)
        assert res.status_code == 400
        assert "Invalid file type" in res.json()["detail"]

    async def test_empty_audio_file_rejected(
        self, client, doctor_token, test_doctor, test_appointment
    ):
        """8. Empty (0-byte) audio file is rejected with HTTP 400."""
        files = {"file": ("empty.webm", BytesIO(b""), "audio/webm")}
        data = {"appointment_id": str(test_appointment.appointment_id)}
        headers = {"Authorization": f"Bearer {doctor_token}"}

        res = await client.post("/api/v1/voice-notes/upload/", files=files, data=data, headers=headers)
        assert res.status_code == 400
        assert "Empty audio file" in res.json()["detail"]

    async def test_upload_logged_in_audit_logs(
        self, client, doctor_token, test_doctor, test_appointment, db_session
    ):
        """9. Upload action is recorded in immutable audit_logs table."""
        audio_content = b"WAVE-AUDIT-TEST"
        files = {"file": ("audit_test.wav", BytesIO(audio_content), "audio/wav")}
        data = {
            "appointment_id": str(test_appointment.appointment_id),
            "duration_seconds": "32",
        }
        headers = {"Authorization": f"Bearer {doctor_token}"}

        res = await client.post("/api/v1/voice-notes/upload/", files=files, data=data, headers=headers)
        assert res.status_code == 201

        # Check audit_logs table
        audit_res = await db_session.execute(
            select(AuditLog).where(AuditLog.action == "UPLOAD_VOICE_NOTE")
        )
        logs = audit_res.scalars().all()
        assert len(logs) > 0
        matched = any(
            l.details and l.details.get("file_name") == "audit_test.wav"
            for l in logs
        )
        assert matched is True
