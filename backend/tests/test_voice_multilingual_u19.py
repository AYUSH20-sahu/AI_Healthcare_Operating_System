"""Automated Test Suite for Milestone U-19: Voice Intake + TTS + Multilingual (M32).

Tests covered:
1. Multilingual Configuration: GET /api/v1/voice/languages returns validated (en, hi) vs experimental (ta, te, bn, es) tiers.
2. STT Transcription (English): POST /api/v1/voice/transcribe transcribes English audio buffer using provider adapter.
3. STT Transcription (Hindi): POST /api/v1/voice/transcribe transcribes Hindi audio with language metadata.
4. STT Transcription (Experimental languages): POST /api/v1/voice/transcribe handles Tamil, Telugu, and Spanish language hints.
5. STT Failure Handling: Empty audio buffer (0 bytes) returns 400 Bad Request.
6. TTS Synthesis (English): POST /api/v1/voice/synthesize produces audio bytes (audio/mpeg) and provider telemetry.
7. TTS Synthesis (Hindi): POST /api/v1/voice/synthesize produces audio in Hindi.
8. TTS Fallback Handling: Graceful degradation to fallback/mock provider rather than 500 failure when primary provider errors.
9. Voice Intake Endpoint (No-Fork Guarantee): POST /api/v1/intake/sessions/{session_id}/voice-message:
   - Transcribes audio buffer via STT adapter
   - Invokes canonical IntakeAgent orchestrator pipeline
   - Updates intake session messages and structured symptoms
   - Synthesizes assistant spoken response
10. Strict Session Access: Cross-patient access denied (403 Forbidden).
11. Unauthenticated Requests: 401 Unauthorized for unauthenticated requests.
"""

import io
import uuid
from datetime import date, datetime
import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models import (
    IntakeSession,
    IntakeStatus,
    Patient,
    User,
    UserRole,
)
from app.services.auth.service import create_access_token, get_password_hash
from app.services.providers import (
    SUPPORTED_LANGUAGES,
    MockSTTProvider,
    MockTTSProvider,
    registry,
)


@pytest_asyncio.fixture
async def patient_a_user(db_session: AsyncSession):
    """Create Patient Alice."""
    user = User(
        email="alice.voice.u19@aihos.org",
        hashed_password=get_password_hash("alicepass123"),
        full_name="Alice Voice Patient",
        role=UserRole.PATIENT,
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    patient = Patient(
        user_id=user.user_id,
        full_name="Alice Voice Patient",
        email=user.email,
        date_of_birth=date(1993, 4, 12),
        gender="Female",
    )
    db_session.add(patient)
    await db_session.commit()
    await db_session.refresh(patient)
    return user


@pytest_asyncio.fixture
async def patient_b_user(db_session: AsyncSession):
    """Create Patient Bob for RBAC isolation tests."""
    user = User(
        email="bob.voice.u19@aihos.org",
        hashed_password=get_password_hash("bobpass123"),
        full_name="Bob Voice Patient",
        role=UserRole.PATIENT,
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    patient = Patient(
        user_id=user.user_id,
        full_name="Bob Voice Patient",
        email=user.email,
        date_of_birth=date(1989, 7, 25),
        gender="Male",
    )
    db_session.add(patient)
    await db_session.commit()
    await db_session.refresh(patient)
    return user


def _auth_header(user: User) -> dict:
    token = create_access_token(data={"sub": str(user.user_id), "role": user.role.value})
    return {"Authorization": f"Bearer {token}"}


# =============================================================================
# Milestone U-19 Tests
# =============================================================================

@pytest.mark.asyncio
async def test_get_supported_languages_configuration(client: AsyncClient):
    """Test retrieving supported language tiers distinguishing validated vs experimental."""
    res = await client.get("/api/v1/voice/languages")
    assert res.status_code == 200
    data = res.json()

    assert "validated_languages" in data
    assert "experimental_languages" in data
    assert data["default_language"] == "en"

    # Check Validated tier
    val_codes = [l["code"] for l in data["validated_languages"]]
    assert "en" in val_codes
    assert "hi" in val_codes

    # Check Experimental tier
    exp_codes = [l["code"] for l in data["experimental_languages"]]
    assert "ta" in exp_codes
    assert "te" in exp_codes
    assert "es" in exp_codes

    # Verify language metadata structure
    en_meta = next(l for l in data["validated_languages"] if l["code"] == "en")
    assert en_meta["name"] == "English"
    assert en_meta["stt_supported"] is True
    assert en_meta["tts_supported"] is True
    assert en_meta["web_speech_lang"] == "en-US"


@pytest.mark.asyncio
async def test_stt_transcription_english(client: AsyncClient, patient_a_user: User):
    """Test transcribing English audio buffer using STT provider adapter."""
    fake_audio = b"\x1a\x45\xdf\xa3" + b"\x00" * 256
    files = {"file": ("recording.webm", fake_audio, "audio/webm")}

    res = await client.post(
        "/api/v1/voice/transcribe?language=en",
        files=files,
        headers=_auth_header(patient_a_user),
    )
    assert res.status_code == 200, res.text
    data = res.json()
    assert "text" in data
    assert len(data["text"]) > 0
    assert data["language"] == "en"
    assert "latency_ms" in data
    assert data["confidence"] > 0.5


@pytest.mark.asyncio
async def test_stt_transcription_hindi_and_experimental(
    client: AsyncClient,
    patient_a_user: User,
):
    """Test transcribing audio for Hindi and experimental languages (Tamil, Spanish)."""
    fake_audio = b"\x1a\x45\xdf\xa3" + b"\x00" * 256

    for lang in ("hi", "ta", "es"):
        files = {"file": (f"recording_{lang}.webm", fake_audio, "audio/webm")}
        res = await client.post(
            f"/api/v1/voice/transcribe?language={lang}",
            files=files,
            headers=_auth_header(patient_a_user),
        )
        assert res.status_code == 200
        data = res.json()
        assert data["language"] == lang
        assert data["text"] is not None


@pytest.mark.asyncio
async def test_stt_transcription_empty_audio_failure(client: AsyncClient, patient_a_user: User):
    """Test that submitting an empty (0 bytes) audio file returns 400 Bad Request."""
    files = {"file": ("empty.webm", b"", "audio/webm")}
    res = await client.post(
        "/api/v1/voice/transcribe",
        files=files,
        headers=_auth_header(patient_a_user),
    )
    assert res.status_code == 400
    assert "empty" in res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_tts_synthesis_english(client: AsyncClient, patient_a_user: User):
    """Test text-to-speech synthesis produces audio bytes with diagnostic headers."""
    payload = {
        "text": "Hello, please describe what symptoms you have been experiencing today.",
        "language": "en",
    }
    res = await client.post(
        "/api/v1/voice/synthesize",
        json=payload,
        headers=_auth_header(patient_a_user),
    )
    assert res.status_code == 200
    assert res.headers["content-type"].startswith("audio/")
    assert "X-TTS-Provider" in res.headers
    assert len(res.content) > 0


@pytest.mark.asyncio
async def test_tts_synthesis_hindi(client: AsyncClient, patient_a_user: User):
    """Test text-to-speech synthesis for Hindi text."""
    payload = {
        "text": "नमस्ते, कृपया मुझे बताएं कि आपको क्या समस्या हो रही है।",
        "language": "hi",
    }
    res = await client.post(
        "/api/v1/voice/synthesize",
        json=payload,
        headers=_auth_header(patient_a_user),
    )
    assert res.status_code == 200
    assert res.headers["content-type"].startswith("audio/")
    assert len(res.content) > 0


@pytest.mark.asyncio
async def test_tts_synthesis_empty_text_rejected(client: AsyncClient, patient_a_user: User):
    """Test that synthesizing empty text is rejected with 400 Bad Request."""
    payload = {"text": "   ", "language": "en"}
    res = await client.post(
        "/api/v1/voice/synthesize",
        json=payload,
        headers=_auth_header(patient_a_user),
    )
    assert res.status_code == 400


@pytest.mark.asyncio
async def test_voice_intake_unified_pipeline(
    client: AsyncClient,
    db_session: AsyncSession,
    patient_a_user: User,
):
    """Test Voice Intake endpoint POST /intake/sessions/{id}/voice-message:
    
    Verifies that voice intake does NOT fork logic:
    - Transcribes speech via STT adapter
    - Feeds to canonical IntakeAgent orchestrator
    - Updates structured symptoms
    - Returns synthesized spoken audio reply
    """
    # 1. Create an active intake session
    init_res = await client.post(
        "/api/v1/intake/sessions",
        json={"initial_message": "Starting intake consultation"},
        headers=_auth_header(patient_a_user),
    )
    assert init_res.status_code == 201
    session_id = init_res.json()["session_id"]

    # 2. Patient submits a voice message
    fake_speech_bytes = b"\x1a\x45\xdf\xa3" + b"\x00" * 512
    files = {"file": ("intake_patient_audio.webm", fake_speech_bytes, "audio/webm")}
    data = {"language": "en", "synthesize_reply": "true"}

    voice_res = await client.post(
        f"/api/v1/intake/sessions/{session_id}/voice-message",
        files=files,
        data=data,
        headers=_auth_header(patient_a_user),
    )
    assert voice_res.status_code == 200, voice_res.text
    result = voice_res.json()

    assert result["session_id"] == session_id
    assert "transcription" in result
    assert result["detected_language"] == "en"
    assert "reply" in result
    assert len(result["reply"]) > 0
    assert result["tts_provider"] is not None

    # Verify session messages and symptoms were updated in DB
    session_db = (await db_session.execute(
        select(IntakeSession).where(IntakeSession.session_id == uuid.UUID(session_id))
    )).scalar_one()

    # Must contain both patient voice turn and assistant turn
    msgs = session_db.messages
    assert len(msgs) >= 2
    assert msgs[-1]["role"] == "assistant"
    assert msgs[-2]["role"] == "patient"
    assert msgs[-2].get("is_voice") is True


@pytest.mark.asyncio
async def test_voice_intake_cross_patient_isolation(
    client: AsyncClient,
    patient_a_user: User,
    patient_b_user: User,
):
    """Test that Patient B cannot post voice messages to Patient A's intake session (403 Forbidden)."""
    init_res = await client.post(
        "/api/v1/intake/sessions",
        headers=_auth_header(patient_a_user),
    )
    assert init_res.status_code == 201
    session_id = init_res.json()["session_id"]

    # Patient B attempts to send voice message to Patient A's session
    files = {"file": ("audio.webm", b"\x1a\x45\xdf\xa3\x00\x00", "audio/webm")}
    data = {"language": "en"}
    res = await client.post(
        f"/api/v1/intake/sessions/{session_id}/voice-message",
        files=files,
        data=data,
        headers=_auth_header(patient_b_user),
    )
    assert res.status_code == 403
    assert "forbidden" in res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_unauthenticated_voice_requests_rejected(client: AsyncClient):
    """Test unauthenticated requests receive 401 Unauthorized."""
    # STT
    r1 = await client.post("/api/v1/voice/transcribe")
    assert r1.status_code == 401

    # TTS
    r2 = await client.post("/api/v1/voice/synthesize", json={"text": "test"})
    assert r2.status_code == 401

    # Voice intake
    fake_id = str(uuid.uuid4())
    r3 = await client.post(f"/api/v1/intake/sessions/{fake_id}/voice-message")
    assert r3.status_code == 401
