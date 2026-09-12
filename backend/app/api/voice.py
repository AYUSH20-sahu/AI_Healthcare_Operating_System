"""Multilingual Voice & Speech Services API (Milestone U-19).

Integrates Groq Whisper STT, ElevenLabs TTS (with browser Web Speech API fallback),
multilingual language configuration (Validated: EN, HI; Experimental: TA, TE, BN, ES),
and language-aware speech transcription & synthesis.
"""

import base64
import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Response, UploadFile, status
from pydantic import BaseModel, Field

from app.models import User
from app.services.auth.service import get_current_active_user
from app.services.providers import (
    SUPPORTED_LANGUAGES,
    get_stt_provider,
    get_tts_provider,
    registry,
)

logger = logging.getLogger("aihos.voice")

router = APIRouter(prefix="/voice", tags=["voice"])


# =============================================================================
# Schemas
# =============================================================================

class LanguageDetail(BaseModel):
    code: str
    name: str
    native_name: str
    status: str  # "validated" | "experimental"
    stt_supported: bool
    tts_supported: bool
    tts_voice_id: Optional[str] = None
    web_speech_lang: str


class LanguagesResponse(BaseModel):
    validated_languages: List[LanguageDetail]
    experimental_languages: List[LanguageDetail]
    default_language: str = "en"
    active_stt_provider: str
    active_tts_provider: str


class TranscriptionResponse(BaseModel):
    text: str
    language: Optional[str] = None
    provider: str
    confidence: float
    duration: Optional[float] = None
    latency_ms: float


class SynthesisRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=2000, description="Clinical text to synthesize into speech")
    language: str = Field("en", description="Target language code (en, hi, ta, te, bn, es)")
    voice: Optional[str] = Field(None, description="Optional custom voice ID")


class SynthesisResponse(BaseModel):
    audio_base64: str
    format: str
    duration: Optional[float] = None
    latency_ms: float
    provider: str
    language: str
    fallback_used: bool = False


# =============================================================================
# Endpoints
# =============================================================================

@router.get("/languages", response_model=LanguagesResponse)
async def get_supported_languages():
    """Retrieve supported multilingual configuration differentiating validated vs experimental tiers."""
    validated = []
    experimental = []

    for lang in SUPPORTED_LANGUAGES.values():
        detail = LanguageDetail(**lang)
        if detail.status == "validated":
            validated.append(detail)
        else:
            experimental.append(detail)

    try:
        stt_name = get_stt_provider().name
    except Exception:
        stt_name = "mock-stt"

    try:
        tts_name = get_tts_provider().name
    except Exception:
        tts_name = "mock-tts"

    return LanguagesResponse(
        validated_languages=validated,
        experimental_languages=experimental,
        default_language="en",
        active_stt_provider=stt_name,
        active_tts_provider=tts_name,
    )


@router.post("/transcribe", response_model=TranscriptionResponse)
async def transcribe_audio(
    file: UploadFile = File(..., description="Audio file (webm, mp3, wav, etc.)"),
    language: Optional[str] = Query(None, description="Language hint (en, hi, ta, te, etc.)"),
    current_user: User = Depends(get_current_active_user),
):
    """Transcribe audio input via the configured STT provider adapter (Groq Whisper / fallback)."""
    if not file:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No audio file provided",
        )

    content = await file.read()
    if len(content) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded audio file is empty (0 bytes)",
        )

    # Determine audio format
    filename = file.filename or "audio.webm"
    audio_format = filename.split(".")[-1].lower() if "." in filename else "webm"
    if audio_format not in ("webm", "mp3", "wav", "ogg", "m4a"):
        audio_format = "webm"

    # Default to English if language is unknown or unsupported
    lang_code = language if language in SUPPORTED_LANGUAGES else "en"

    try:
        stt_provider = get_stt_provider()
        res = await stt_provider.transcribe(
            audio_data=content,
            format=audio_format,
            language=lang_code,
        )
        return TranscriptionResponse(
            text=res.text or "",
            language=res.language or lang_code,
            provider=stt_provider.name,
            confidence=res.confidence or 0.9,
            duration=res.duration,
            latency_ms=res.latency_ms,
        )
    except Exception as exc:
        logger.error(f"STT transcription failure: {exc}")
        # Graceful fallback or error propagation
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Speech-to-text transcription service error: {str(exc)}",
        )


@router.post("/synthesize")
async def synthesize_speech(
    payload: SynthesisRequest,
    current_user: User = Depends(get_current_active_user),
):
    """Synthesize text into speech via the configured TTS provider adapter (ElevenLabs / fallback).
    
    Returns streaming audio bytes (audio/mpeg) with diagnostic headers.
    """
    if not payload.text.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Text content cannot be empty",
        )

    lang_config = SUPPORTED_LANGUAGES.get(payload.language, SUPPORTED_LANGUAGES["en"])
    voice_id = payload.voice or lang_config.get("tts_voice_id")

    tts_provider = get_tts_provider()
    try:
        res = await tts_provider.synthesize(
            text=payload.text.strip(),
            voice=voice_id,
            format="mp3",
        )
        return Response(
            content=res.audio_data,
            media_type="audio/mpeg",
            headers={
                "X-TTS-Provider": tts_provider.name,
                "X-Voice-Language": payload.language,
                "X-Latency-Ms": str(res.latency_ms),
                "Content-Disposition": "inline; filename=synthesized_speech.mp3",
            },
        )
    except Exception as exc:
        logger.warning(f"TTS synthesis failure on provider [{tts_provider.name}]: {exc}. Returning mock fallback audio.")
        # Return graceful mock audio with fallback header so client can either play or trigger Web Speech API
        from app.services.providers import MockTTSProvider
        fallback_mock = MockTTSProvider()
        fallback_res = await fallback_mock.synthesize(text=payload.text.strip())
        return Response(
            content=fallback_res.audio_data,
            media_type="audio/mpeg",
            headers={
                "X-TTS-Provider": "fallback-mock",
                "X-TTS-Fallback-Used": "true",
                "X-Voice-Language": payload.language,
                "X-Latency-Ms": str(fallback_res.latency_ms),
            },
        )
