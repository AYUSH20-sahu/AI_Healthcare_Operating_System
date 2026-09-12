"""AI Provider Adapter Interface for LLM, STT, and TTS services.

Enforces provider-independent abstraction across the application.
Supports NVIDIA NIM (primary), Gemini (fallback), and Groq (STT).
Never call provider SDKs directly outside this adapter architecture.
"""

import asyncio
import json
import logging
import os
import time
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    import google.generativeai as genai
    from groq import AsyncGroq
    from openai import AsyncOpenAI

logger = logging.getLogger("ai_providers")


class ProviderType(str, Enum):
    """Supported provider types."""
    LLM = "llm"
    STT = "stt"
    TTS = "tts"


class LLMProviderName(str, Enum):
    """Supported LLM provider identifiers."""
    NVIDIA = "nvidia"
    GEMINI = "gemini"
    OPENAI = "openai"
    FALLBACK = "fallback"
    MOCK = "mock"


class STTProviderName(str, Enum):
    """Supported STT provider identifiers."""
    GROQ = "groq"
    WHISPER = "whisper"
    MOCK = "mock"


@dataclass
class LLMMessage:
    """Standard message format for LLM conversations."""
    role: str  # system, user, assistant
    content: str


@dataclass
class LLMResponse:
    """Unified response object returned by all LLM providers."""
    content: str
    model: str
    provider: str = "mock"
    fallback_used: bool = False
    latency_ms: float = 0.0
    usage: dict[str, int] | None = None
    finish_reason: str | None = None


@dataclass
class TranscriptionResult:
    """Standard result returned by STT providers."""
    text: str
    provider: str = "mock"
    language: str | None = "en"
    duration: float | None = None
    confidence: float | None = 0.95
    latency_ms: float = 0.0


@dataclass
class SynthesisResult:
    """Standard result returned by TTS providers."""
    audio_data: bytes
    format: str  # mp3, wav, etc.
    sample_rate: int = 22050
    duration: float | None = None
    latency_ms: float = 0.0


class BaseProvider(ABC):
    """Base abstract provider."""

    @property
    @abstractmethod
    def provider_type(self) -> ProviderType:
        """Return the provider type."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the provider name."""

    @abstractmethod
    async def health_check(self) -> bool:
        """Verify provider availability."""


class LLMProviderBase(BaseProvider):
    """Base class for all LLM providers."""

    @property
    def provider_type(self) -> ProviderType:
        return ProviderType.LLM

    @abstractmethod
    async def generate(
        self,
        messages: list[LLMMessage],
        model: str | None = None,
        temperature: float = 0.3,
        max_tokens: int | None = 2000,
        **kwargs: Any,
    ) -> LLMResponse:
        """Generate a complete text response."""

    @abstractmethod
    async def stream_generate(
        self,
        messages: list[LLMMessage],
        model: str | None = None,
        temperature: float = 0.3,
        max_tokens: int | None = 2000,
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        """Stream generated text chunks."""


class STTProviderBase(BaseProvider):
    """Base class for Speech-To-Text providers."""

    @property
    def provider_type(self) -> ProviderType:
        return ProviderType.STT

    @abstractmethod
    async def transcribe(
        self,
        audio_data: bytes,
        format: str = "webm",
        language: str | None = "en",
        **kwargs: Any,
    ) -> TranscriptionResult:
        """Transcribe audio into text."""


class TTSProviderBase(BaseProvider):
    """Base class for Text-To-Speech providers."""

    @property
    def provider_type(self) -> ProviderType:
        return ProviderType.TTS

    @abstractmethod
    async def synthesize(
        self,
        text: str,
        voice: str | None = None,
        format: str = "mp3",
        sample_rate: int = 22050,
        **kwargs: Any,
    ) -> SynthesisResult:
        """Synthesize text into speech."""


class MockLLMProvider(LLMProviderBase):
    """Deterministic Mock LLM provider for tests and offline development."""

    def __init__(self, name: str = "mock", simulate_failure: bool = False, delay: float = 0.0):
        self._name = name
        self.simulate_failure = simulate_failure
        self.delay = delay

    @property
    def name(self) -> str:
        return self._name

    async def health_check(self) -> bool:
        return not self.simulate_failure

    async def generate(
        self,
        messages: list[LLMMessage],
        model: str | None = None,
        temperature: float = 0.3,
        max_tokens: int | None = 2000,
        **kwargs: Any,
    ) -> LLMResponse:
        start_time = time.perf_counter()
        if self.delay > 0:
            await asyncio.sleep(self.delay)

        if self.simulate_failure:
            raise RuntimeError(f"Mock provider [{self._name}] simulated failure")

        last_user_msg = next((m.content for m in reversed(messages) if m.role == "user"), "")
        lower_msg = last_user_msg.lower()

        # Clinical synthesis default
        if "chest pain" in lower_msg or "angina" in lower_msg or "clinical" in lower_msg or "transcription" in lower_msg:
            payload = {
                "chief_complaint": "Substernal exertional chest pain radiating to left arm",
                "history_present_illness": "Patient reports squeezing chest pain of 2 days duration on stair climbing, lasting 5 minutes and relieved by rest. Accompanied by diaphoresis.",
                "physical_examination": "BP 138/88 mmHg, HR 94 bpm, regular rhythm. Bilateral lungs clear to auscultation. No peripheral edema.",
                "assessment": "Angina Pectoris, unspecified / Exertional Angina",
                "plan": "Immediate 12-lead ECG and cardiac enzymes. Prescribe sublingual nitrates PRN and high-intensity statin therapy.",
                "diagnosis_codes": ["I20.9", "I24.9"],
                "medications": [
                    {
                        "name": "Isosorbide Dinitrate",
                        "dosage": "5mg",
                        "frequency": "Sublingually PRN for acute chest pain",
                        "duration": "30 days",
                    },
                    {
                        "name": "Atorvastatin",
                        "dosage": "40mg",
                        "frequency": "Once daily at bedtime",
                        "duration": "90 days",
                    },
                ],
                "diagnostics_ordered": [
                    "12-lead Electrocardiogram (ECG)",
                    "High-sensitivity Troponin I",
                    "Lipid Profile & HbA1c",
                ],
                "confidence": 0.95,
                "basis": "Clinical presentation matches exertional angina with characteristic relief on rest and diaphoresis.",
            }
            content = json.dumps(payload)
        else:
            content = json.dumps({
                "chief_complaint": "General consultation",
                "history_present_illness": last_user_msg[:200] if last_user_msg else "Patient presents for evaluation.",
                "physical_examination": "Vital signs stable. Physical exam normal.",
                "assessment": "Routine health maintenance",
                "plan": "Continue current regimen and follow up in 6 months.",
                "diagnosis_codes": ["Z00.00"],
                "medications": [],
                "diagnostics_ordered": [],
                "confidence": 0.90,
                "basis": "Routine assessment based on input history.",
            })

        latency = (time.perf_counter() - start_time) * 1000.0

        return LLMResponse(
            content=content,
            model=model or "mock-clinical-nemotron",
            provider=self._name,
            fallback_used=False,
            latency_ms=round(latency, 2),
            usage={"prompt_tokens": 120, "completion_tokens": 180, "total_tokens": 300},
            finish_reason="stop",
        )

    async def stream_generate(
        self,
        messages: list[LLMMessage],
        model: str | None = None,
        temperature: float = 0.3,
        max_tokens: int | None = 2000,
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        res = await self.generate(messages, model, temperature, max_tokens, **kwargs)
        for chunk in [res.content[i:i+20] for i in range(0, len(res.content), 20)]:
            yield chunk


class MockSTTProvider(STTProviderBase):
    """Deterministic Mock Speech-to-Text provider."""

    def __init__(self, name: str = "mock-groq"):
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    async def health_check(self) -> bool:
        return True

    async def transcribe(
        self,
        audio_data: bytes,
        format: str = "webm",
        language: str | None = "en",
        **kwargs: Any,
    ) -> TranscriptionResult:
        start = time.perf_counter()
        simulated_transcript = (
            "Good morning. The patient presents with substernal exertional chest pain "
            "radiating to left shoulder for two days. Blood pressure is 138/88 mmHg, heart rate is 94 bpm. "
            "Severe allergy to penicillin confirmed. Ordering 12-lead ECG and cardiac enzymes. Prescribing Sorbitrate and Atorvastatin."
        )
        latency = (time.perf_counter() - start) * 1000.0
        return TranscriptionResult(
            text=simulated_transcript,
            provider=self._name,
            language=language or "en",
            duration=32.5,
            confidence=0.96,
            latency_ms=round(latency, 2),
        )


class MockTTSProvider(TTSProviderBase):
    """Deterministic Mock Text-to-Speech provider."""

    @property
    def name(self) -> str:
        return "mock-tts"

    async def health_check(self) -> bool:
        return True

    async def synthesize(
        self,
        text: str,
        voice: str | None = None,
        format: str = "mp3",
        sample_rate: int = 22050,
        **kwargs: Any,
    ) -> SynthesisResult:
        return SynthesisResult(
            audio_data=b"\x00" * 1024,
            format=format,
            sample_rate=sample_rate,
            duration=len(text) * 0.05,
            latency_ms=10.0,
        )


class NVIDIALLMProvider(LLMProviderBase):
    """NVIDIA NIM LLM provider (Primary LLM).
    
    Default Model: nvidia/nemotron-3-ultra-550b-a55b (OpenAI API compliant).
    """

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        default_model: str | None = None,
        timeout: float = 30.0,
    ):
        self._api_key = api_key or os.getenv("NVIDIA_API_KEY") or os.getenv("LLM_API_KEY")
        self._base_url = base_url or os.getenv("NVIDIA_BASE_URL") or os.getenv("LLM_BASE_URL", "https://integrate.api.nvidia.com/v1")
        self._default_model = default_model or os.getenv("NVIDIA_MODEL") or os.getenv("LLM_MODEL", "nvidia/nemotron-3-ultra-550b-a55b")
        self._timeout = timeout
        self._client = None

    @property
    def name(self) -> str:
        return "nvidia"

    async def _get_client(self):
        if self._client is None:
            if not self._api_key:
                raise ValueError("NVIDIA_API_KEY is not configured")
            from openai import AsyncOpenAI
            self._client = AsyncOpenAI(
                api_key=self._api_key,
                base_url=self._base_url,
                timeout=self._timeout,
            )
        return self._client

    async def health_check(self) -> bool:
        try:
            if not self._api_key:
                return False
            client = await self._get_client()
            await client.chat.completions.create(
                model=self._default_model,
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=5,
            )
            return True
        except Exception as err:
            logger.warning(f"NVIDIA NIM health check failed: {err}")
            return False

    async def generate(
        self,
        messages: list[LLMMessage],
        model: str | None = None,
        temperature: float = 0.3,
        max_tokens: int | None = 2000,
        **kwargs: Any,
    ) -> LLMResponse:
        client = await self._get_client()
        model_name = model or self._default_model
        payload_messages = [{"role": m.role, "content": m.content} for m in messages]

        start_time = time.perf_counter()
        response = await client.chat.completions.create(
            model=model_name,
            messages=payload_messages,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs,
        )
        latency = (time.perf_counter() - start_time) * 1000.0

        content = response.choices[0].message.content or ""
        return LLMResponse(
            content=content,
            model=response.model or model_name,
            provider="nvidia",
            fallback_used=False,
            latency_ms=round(latency, 2),
            usage={
                "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                "total_tokens": response.usage.total_tokens if response.usage else 0,
            } if response.usage else None,
            finish_reason=response.choices[0].finish_reason,
        )

    async def stream_generate(
        self,
        messages: list[LLMMessage],
        model: str | None = None,
        temperature: float = 0.3,
        max_tokens: int | None = 2000,
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        client = await self._get_client()
        model_name = model or self._default_model
        payload_messages = [{"role": m.role, "content": m.content} for m in messages]

        stream = await client.chat.completions.create(
            model=model_name,
            messages=payload_messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
            **kwargs,
        )
        async for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content


class GeminiLLMProvider(LLMProviderBase):
    """Google Gemini LLM provider (Fallback LLM)."""

    def __init__(
        self,
        api_key: str | None = None,
        default_model: str | None = None,
    ):
        self._api_key = api_key or os.getenv("GEMINI_API_KEY")
        self._default_model = default_model or os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
        self._model = None

    @property
    def name(self) -> str:
        return "gemini"

    async def _get_model(self):
        if self._model is None:
            if not self._api_key:
                raise ValueError("GEMINI_API_KEY is not configured")
            import google.generativeai as genai
            genai.configure(api_key=self._api_key)
            self._model = genai.GenerativeModel(self._default_model)
        return self._model

    async def health_check(self) -> bool:
        try:
            if not self._api_key:
                return False
            model = await self._get_model()
            await model.generate_content_async("ping")
            return True
        except Exception as err:
            logger.warning(f"Gemini health check failed: {err}")
            return False

    async def generate(
        self,
        messages: list[LLMMessage],
        model: str | None = None,
        temperature: float = 0.3,
        max_tokens: int | None = 2000,
        **kwargs: Any,
    ) -> LLMResponse:
        model_instance = await self._get_model()
        model_name = model or self._default_model

        prompt_parts = []
        for m in messages:
            if m.role == "system":
                prompt_parts.append(f"System: {m.content}")
            elif m.role == "user":
                prompt_parts.append(f"User: {m.content}")
            elif m.role == "assistant":
                prompt_parts.append(f"Assistant: {m.content}")
        prompt = "\n\n".join(prompt_parts)

        generation_config = {
            "temperature": temperature,
            "max_output_tokens": max_tokens,
        }

        start_time = time.perf_counter()
        response = await model_instance.generate_content_async(
            prompt,
            generation_config=generation_config,
        )
        latency = (time.perf_counter() - start_time) * 1000.0

        return LLMResponse(
            content=response.text or "",
            model=model_name,
            provider="gemini",
            fallback_used=True,
            latency_ms=round(latency, 2),
            usage=None,
            finish_reason="stop",
        )

    async def stream_generate(
        self,
        messages: list[LLMMessage],
        model: str | None = None,
        temperature: float = 0.3,
        max_tokens: int | None = 2000,
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        model_instance = await self._get_model()
        prompt_parts = [f"{m.role.capitalize()}: {m.content}" for m in messages]
        prompt = "\n\n".join(prompt_parts)

        response = await model_instance.generate_content_async(
            prompt,
            generation_config={"temperature": temperature, "max_output_tokens": max_tokens},
            stream=True,
        )
        async for chunk in response:
            if chunk.text:
                yield chunk.text


class FallbackLLMProvider(LLMProviderBase):
    """Resilient LLM Provider executing Primary with automatic fallback to Secondary.
    
    Primary: NVIDIA NIM
    Secondary (Fallback): Google Gemini
    """

    def __init__(
        self,
        primary: LLMProviderBase,
        fallback: LLMProviderBase,
    ):
        self._primary = primary
        self._fallback = fallback

    @property
    def name(self) -> str:
        return f"{self._primary.name}->{self._fallback.name}"

    @property
    def primary_name(self) -> str:
        return self._primary.name

    @property
    def fallback_name(self) -> str:
        return self._fallback.name

    async def health_check(self) -> bool:
        p_ok = await self._primary.health_check()
        f_ok = await self._fallback.health_check()
        return p_ok or f_ok

    async def generate(
        self,
        messages: list[LLMMessage],
        model: str | None = None,
        temperature: float = 0.3,
        max_tokens: int | None = 2000,
        **kwargs: Any,
    ) -> LLMResponse:
        start_time = time.perf_counter()
        try:
            logger.info(f"Invoking primary LLM provider: {self._primary.name}")
            response = await self._primary.generate(messages, model, temperature, max_tokens, **kwargs)
            response.provider = self._primary.name
            response.fallback_used = False
            return response
        except Exception as primary_error:
            logger.warning(
                f"Primary provider [{self._primary.name}] failed: {primary_error}. "
                f"Escalating to fallback provider [{self._fallback.name}]..."
            )
            try:
                response = await self._fallback.generate(messages, model, temperature, max_tokens, **kwargs)
                response.provider = self._fallback.name
                response.fallback_used = True
                response.latency_ms = round((time.perf_counter() - start_time) * 1000.0, 2)
                logger.info(f"Fallback provider [{self._fallback.name}] successfully completed generation.")
                return response
            except Exception as fallback_error:
                total_latency = (time.perf_counter() - start_time) * 1000.0
                logger.error(
                    f"All LLM providers exhausted! Primary error: {primary_error}; "
                    f"Fallback error: {fallback_error}; Total latency: {total_latency:.2f}ms"
                )
                raise RuntimeError(
                    f"LLM failover mesh exhausted. Primary [{self._primary.name}] and Fallback [{self._fallback.name}] failed. "
                    f"Errors: (1) {primary_error} | (2) {fallback_error}"
                )

    async def stream_generate(
        self,
        messages: list[LLMMessage],
        model: str | None = None,
        temperature: float = 0.3,
        max_tokens: int | None = 2000,
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        try:
            async for chunk in self._primary.stream_generate(messages, model, temperature, max_tokens, **kwargs):
                yield chunk
        except Exception as primary_error:
            logger.warning(f"Primary stream [{self._primary.name}] failed: {primary_error}. Switching stream to fallback.")
            async for chunk in self._fallback.stream_generate(messages, model, temperature, max_tokens, **kwargs):
                yield chunk


class GroqSTTProvider(STTProviderBase):
    """Groq STT provider using Whisper."""

    def __init__(
        self,
        api_key: str | None = None,
        default_model: str | None = None,
    ):
        self._api_key = api_key or os.getenv("GROQ_API_KEY")
        self._default_model = default_model or "whisper-large-v3-turbo"
        self._client = None

    @property
    def name(self) -> str:
        return "groq"

    async def _get_client(self):
        if self._client is None:
            if not self._api_key:
                raise ValueError("GROQ_API_KEY is not configured")
            from groq import AsyncGroq
            self._client = AsyncGroq(api_key=self._api_key)
        return self._client

    async def health_check(self) -> bool:
        return bool(self._api_key)

    async def transcribe(
        self,
        audio_data: bytes,
        format: str = "webm",
        language: str | None = "en",
        **kwargs: Any,
    ) -> TranscriptionResult:
        import io
        client = await self._get_client()
        model = kwargs.get("model", self._default_model)

        audio_file = io.BytesIO(audio_data)
        audio_file.name = f"consultation_audio.{format}"

        start_time = time.perf_counter()
        response = await client.audio.transcriptions.create(
            file=audio_file,
            model=model,
            language=language,
            response_format="verbose_json",
        )
        latency = (time.perf_counter() - start_time) * 1000.0

        return TranscriptionResult(
            text=response.text,
            provider="groq",
            language=getattr(response, "language", language),
            duration=getattr(response, "duration", None),
            confidence=0.95,
            latency_ms=round(latency, 2),
        )


class ElevenLabsTTSProvider(TTSProviderBase):
    """ElevenLabs TTS provider supporting multilingual speech synthesis."""

    DEFAULT_VOICE_ID = "21m00Tcm4TlvDq8ikWAM"  # Rachel (Clear clinical tone)
    DEFAULT_MODEL = "eleven_multilingual_v2"

    def __init__(
        self,
        api_key: str | None = None,
        default_voice_id: str | None = None,
        default_model: str | None = None,
    ):
        self._api_key = api_key or os.getenv("ELEVENLABS_API_KEY")
        self._default_voice_id = default_voice_id or os.getenv("ELEVENLABS_VOICE_ID", self.DEFAULT_VOICE_ID)
        self._default_model = default_model or os.getenv("ELEVENLABS_MODEL_ID", self.DEFAULT_MODEL)

    @property
    def name(self) -> str:
        return "elevenlabs"

    async def health_check(self) -> bool:
        return bool(self._api_key)

    async def synthesize(
        self,
        text: str,
        voice: str | None = None,
        format: str = "mp3",
        sample_rate: int = 22050,
        **kwargs: Any,
    ) -> SynthesisResult:
        if not self._api_key:
            raise ValueError("ELEVENLABS_API_KEY is not configured")

        voice_id = voice or self._default_voice_id
        model_id = kwargs.get("model_id", self._default_model)
        start_time = time.perf_counter()

        import httpx

        url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
        headers = {
            "xi-api-key": self._api_key,
            "Content-Type": "application/json",
            "Accept": "audio/mpeg",
        }
        payload = {
            "text": text,
            "model_id": model_id,
            "voice_settings": {
                "stability": kwargs.get("stability", 0.5),
                "similarity_boost": kwargs.get("similarity_boost", 0.75),
            },
        }

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(url, headers=headers, json=payload)
            if resp.status_code != 200:
                raise RuntimeError(f"ElevenLabs synthesis error {resp.status_code}: {resp.text}")
            audio_bytes = resp.content

        latency = (time.perf_counter() - start_time) * 1000.0
        duration = max(1.0, len(text) * 0.06)

        return SynthesisResult(
            audio_data=audio_bytes,
            format=format,
            sample_rate=sample_rate,
            duration=round(duration, 2),
            latency_ms=round(latency, 2),
        )


class FallbackTTSProvider(TTSProviderBase):
    """Resilient TTS Provider with automatic fallback to secondary provider."""

    def __init__(self, primary: TTSProviderBase, fallback: TTSProviderBase):
        self._primary = primary
        self._fallback = fallback

    @property
    def name(self) -> str:
        return f"fallback({self._primary.name}->{self._fallback.name})"

    async def health_check(self) -> bool:
        return await self._primary.health_check() or await self._fallback.health_check()

    async def synthesize(
        self,
        text: str,
        voice: str | None = None,
        format: str = "mp3",
        sample_rate: int = 22050,
        **kwargs: Any,
    ) -> SynthesisResult:
        start_time = time.perf_counter()
        try:
            res = await self._primary.synthesize(text, voice=voice, format=format, sample_rate=sample_rate, **kwargs)
            return res
        except Exception as primary_error:
            logger.warning(
                f"Primary TTS provider [{self._primary.name}] failed: {primary_error}. "
                f"Switching to fallback TTS provider [{self._fallback.name}]..."
            )
            try:
                res = await self._fallback.synthesize(text, voice=voice, format=format, sample_rate=sample_rate, **kwargs)
                res.latency_ms = round((time.perf_counter() - start_time) * 1000.0, 2)
                return res
            except Exception as fallback_error:
                logger.error(f"Fallback TTS failed: {fallback_error}")
                raise RuntimeError(f"All TTS providers failed: {primary_error} | {fallback_error}")


# Supported Multilingual Voice & Speech Configuration
SUPPORTED_LANGUAGES = {
    "en": {
        "code": "en",
        "name": "English",
        "native_name": "English",
        "status": "validated",
        "stt_supported": True,
        "tts_supported": True,
        "tts_voice_id": "21m00Tcm4TlvDq8ikWAM",
        "web_speech_lang": "en-US",
    },
    "hi": {
        "code": "hi",
        "name": "Hindi",
        "native_name": "हिन्दी",
        "status": "validated",
        "stt_supported": True,
        "tts_supported": True,
        "tts_voice_id": "pNInz6obpgDQGcFmaJgB",
        "web_speech_lang": "hi-IN",
    },
    "ta": {
        "code": "ta",
        "name": "Tamil",
        "native_name": "தமிழ்",
        "status": "experimental",
        "stt_supported": True,
        "tts_supported": True,
        "tts_voice_id": "pNInz6obpgDQGcFmaJgB",
        "web_speech_lang": "ta-IN",
    },
    "te": {
        "code": "te",
        "name": "Telugu",
        "native_name": "తెలుగు",
        "status": "experimental",
        "stt_supported": True,
        "tts_supported": True,
        "tts_voice_id": "pNInz6obpgDQGcFmaJgB",
        "web_speech_lang": "te-IN",
    },
    "bn": {
        "code": "bn",
        "name": "Bengali",
        "native_name": "বাংলা",
        "status": "experimental",
        "stt_supported": True,
        "tts_supported": True,
        "tts_voice_id": "pNInz6obpgDQGcFmaJgB",
        "web_speech_lang": "bn-IN",
    },
    "es": {
        "code": "es",
        "name": "Spanish",
        "native_name": "Español",
        "status": "experimental",
        "stt_supported": True,
        "tts_supported": True,
        "tts_voice_id": "EXAVITQu4vr4xnSDxMaL",
        "web_speech_lang": "es-ES",
    },
}


class ProviderRegistry:
    """Registry coordinating available AI providers."""

    def __init__(self):
        self._llm_providers: dict[str, LLMProviderBase] = {}
        self._stt_providers: dict[str, STTProviderBase] = {}
        self._tts_providers: dict[str, TTSProviderBase] = {}
        self._default_llm: str | None = None
        self._default_stt: str | None = None
        self._default_tts: str | None = None

    def register_llm(self, name: str, provider: LLMProviderBase, default: bool = False) -> None:
        self._llm_providers[name] = provider
        if default or self._default_llm is None:
            self._default_llm = name

    def register_stt(self, name: str, provider: STTProviderBase, default: bool = False) -> None:
        self._stt_providers[name] = provider
        if default or self._default_stt is None:
            self._default_stt = name

    def register_tts(self, name: str, provider: TTSProviderBase, default: bool = False) -> None:
        self._tts_providers[name] = provider
        if default or self._default_tts is None:
            self._default_tts = name

    def get_llm(self, name: str | None = None) -> LLMProviderBase:
        target = name or self._default_llm
        if target not in self._llm_providers:
            raise KeyError(f"LLM provider '{target}' is not registered.")
        return self._llm_providers[target]

    def get_stt(self, name: str | None = None) -> STTProviderBase:
        target = name or self._default_stt
        if target not in self._stt_providers:
            raise KeyError(f"STT provider '{target}' is not registered.")
        return self._stt_providers[target]

    def get_tts(self, name: str | None = None) -> TTSProviderBase:
        target = name or self._default_tts
        if target not in self._tts_providers:
            raise KeyError(f"TTS provider '{target}' is not registered.")
        return self._tts_providers[target]

    def list_llm_providers(self) -> list[str]:
        return list(self._llm_providers.keys())

    def list_stt_providers(self) -> list[str]:
        return list(self._stt_providers.keys())

    def list_tts_providers(self) -> list[str]:
        return list(self._tts_providers.keys())


registry = ProviderRegistry()


def configure_providers() -> None:
    """Initialize registry providers from environment configuration."""
    has_nvidia = bool(os.getenv("NVIDIA_API_KEY") or os.getenv("LLM_API_KEY"))
    has_gemini = bool(os.getenv("GEMINI_API_KEY"))
    has_groq = bool(os.getenv("GROQ_API_KEY"))
    has_elevenlabs = bool(os.getenv("ELEVENLABS_API_KEY"))

    # Register Mock Providers (always available for fallback/testing)
    mock_llm = MockLLMProvider("mock")
    mock_stt = MockSTTProvider("mock")
    mock_tts = MockTTSProvider()
    registry.register_llm("mock", mock_llm)
    registry.register_stt("mock", mock_stt)
    registry.register_tts("mock", mock_tts)

    # Configure LLMs
    if has_nvidia and has_gemini:
        nvidia_prov = NVIDIALLMProvider()
        gemini_prov = GeminiLLMProvider()
        fallback_prov = FallbackLLMProvider(primary=nvidia_prov, fallback=gemini_prov)
        registry.register_llm("nvidia", nvidia_prov)
        registry.register_llm("gemini", gemini_prov)
        registry.register_llm("fallback", fallback_prov, default=True)
    elif has_nvidia:
        nvidia_prov = NVIDIALLMProvider()
        fallback_prov = FallbackLLMProvider(primary=nvidia_prov, fallback=mock_llm)
        registry.register_llm("nvidia", nvidia_prov)
        registry.register_llm("fallback", fallback_prov, default=True)
    elif has_gemini:
        gemini_prov = GeminiLLMProvider()
        registry.register_llm("gemini", gemini_prov, default=True)
    else:
        # Development / CI mode: Primary mock with fallback mock
        primary_mock = MockLLMProvider("nvidia-simulated")
        fallback_mock = MockLLMProvider("gemini-simulated")
        resilient_mock = FallbackLLMProvider(primary=primary_mock, fallback=fallback_mock)
        registry.register_llm("nvidia", primary_mock)
        registry.register_llm("gemini", fallback_mock)
        registry.register_llm("fallback", resilient_mock, default=True)

    # Configure STT
    if has_groq:
        groq_prov = GroqSTTProvider()
        registry.register_stt("groq", groq_prov, default=True)
    else:
        registry.register_stt("groq", mock_stt, default=True)

    # Configure TTS
    if has_elevenlabs:
        eleven_prov = ElevenLabsTTSProvider()
        fallback_tts = FallbackTTSProvider(primary=eleven_prov, fallback=mock_tts)
        registry.register_tts("elevenlabs", eleven_prov)
        registry.register_tts("fallback", fallback_tts, default=True)
    else:
        registry.register_tts("elevenlabs", mock_tts)
        registry.register_tts("fallback", mock_tts, default=True)


# Auto-configure on import
configure_providers()


def get_llm_provider(name: str | None = None) -> LLMProviderBase:
    return registry.get_llm(name)


def get_stt_provider(name: str | None = None) -> STTProviderBase:
    return registry.get_stt(name)


def get_tts_provider(name: str | None = None) -> TTSProviderBase:
    return registry.get_tts(name)
