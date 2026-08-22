"""Provider adapter interface for LLM, STT, and TTS services."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, AsyncIterator, Optional
import json
import os
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from openai import AsyncOpenAI
    import google.generativeai as genai
    from groq import AsyncGroq

logger = logging.getLogger(__name__)


class ProviderType(Enum):
    """Supported provider types."""
    LLM = "llm"
    STT = "stt"
    TTS = "tts"


class LLMProvider(Enum):
    """Supported LLM providers."""
    GEMINI = "gemini"
    OPENAI = "openai"
    CLAUDE = "claude"
    MOCK = "mock"


class STTProvider(Enum):
    """Supported STT providers."""
    WHISPER = "whisper"
    MOCK = "mock"


class TTSProvider(Enum):
    """Supported TTS providers."""
    ELEVENLABS = "elevenlabs"
    MOCK = "mock"


@dataclass
class LLMMessage:
    """Message for LLM conversation."""
    role: str  # system, user, assistant
    content: str


@dataclass
class LLMResponse:
    """Response from LLM provider."""
    content: str
    model: str
    usage: Optional[dict] = None
    finish_reason: Optional[str] = None


@dataclass
class TranscriptionResult:
    """Result from STT provider."""
    text: str
    language: Optional[str] = None
    duration: Optional[float] = None
    confidence: Optional[float] = None


@dataclass
class SynthesisResult:
    """Result from TTS provider."""
    audio_data: bytes
    format: str  # mp3, wav, etc.
    sample_rate: int
    duration: Optional[float] = None


class BaseProvider(ABC):
    """Base class for all providers."""
    
    @property
    @abstractmethod
    def provider_type(self) -> ProviderType:
        """Return the provider type."""
        pass
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Return the provider name."""
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """Check if provider is available."""
        pass


class LLMProviderBase(BaseProvider):
    """Base class for LLM providers."""
    
    @property
    def provider_type(self) -> ProviderType:
        return ProviderType.LLM
    
    @abstractmethod
    async def generate(
        self,
        messages: list[LLMMessage],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> LLMResponse:
        """Generate a response from the LLM."""
        pass
    
    @abstractmethod
    async def stream_generate(
        self,
        messages: list[LLMMessage],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        """Stream generate a response from the LLM."""
        pass


class STTProviderBase(BaseProvider):
    """Base class for STT providers."""
    
    @property
    def provider_type(self) -> ProviderType:
        return ProviderType.STT
    
    @abstractmethod
    async def transcribe(
        self,
        audio_data: bytes,
        format: str = "webm",
        language: Optional[str] = None,
        **kwargs: Any,
    ) -> TranscriptionResult:
        """Transcribe audio to text."""
        pass


class TTSProviderBase(BaseProvider):
    """Base class for TTS providers."""
    
    @property
    def provider_type(self) -> ProviderType:
        return ProviderType.TTS
    
    @abstractmethod
    async def synthesize(
        self,
        text: str,
        voice: Optional[str] = None,
        format: str = "mp3",
        sample_rate: int = 22050,
        **kwargs: Any,
    ) -> SynthesisResult:
        """Synthesize text to speech."""
        pass


class MockLLMProvider(LLMProviderBase):
    """Mock LLM provider for testing."""
    
    @property
    def name(self) -> str:
        return "mock"
    
    async def health_check(self) -> bool:
        return True
    
    async def generate(
        self,
        messages: list[LLMMessage],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> LLMResponse:
        # Return a mock response based on the last user message
        last_user_msg = next((m.content for m in reversed(messages) if m.role == "user"), "")
        
        # Simple mock responses based on keywords
        if "clinical" in last_user_msg.lower() or "medical" in last_user_msg.lower():
            content = json.dumps({
                "chief_complaint": "Chest pain",
                "history_present_illness": "Patient reports chest pain for 2 hours",
                "physical_examination": "BP 140/90, HR 88",
                "assessment": "Possible angina",
                "plan": "ECG, troponin, cardiology referral",
                "diagnosis_codes": ["I20.9"],
            })
        elif "prescription" in last_user_msg.lower():
            content = json.dumps({
                "medications": [
                    {"name": "Aspirin", "dosage": "81mg", "frequency": "once daily", "duration": "30 days"},
                    {"name": "Metoprolol", "dosage": "50mg", "frequency": "twice daily", "duration": "30 days"},
                ]
            })
        else:
            content = f"Mock response to: {last_user_msg[:100]}"
        
        return LLMResponse(
            content=content,
            model="mock-model",
            usage={"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
            finish_reason="stop",
        )
    
    async def stream_generate(
        self,
        messages: list[LLMMessage],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        response = await self.generate(messages, model, temperature, max_tokens, **kwargs)
        # Simulate streaming by yielding chunks
        for i in range(0, len(response.content), 10):
            yield response.content[i:i+10]


class MockSTTProvider(STTProviderBase):
    """Mock STT provider for testing."""
    
    @property
    def name(self) -> str:
        return "mock"
    
    async def health_check(self) -> bool:
        return True
    
    async def transcribe(
        self,
        audio_data: bytes,
        format: str = "webm",
        language: Optional[str] = None,
        **kwargs: Any,
    ) -> TranscriptionResult:
        # Return mock transcription
        return TranscriptionResult(
            text="This is a mock transcription of the audio file.",
            language=language or "en",
            duration=30.0,
            confidence=0.95,
        )


class MockTTSProvider(TTSProviderBase):
    """Mock TTS provider for testing."""
    
    @property
    def name(self) -> str:
        return "mock"
    
    async def health_check(self) -> bool:
        return True
    
    async def synthesize(
        self,
        text: str,
        voice: Optional[str] = None,
        format: str = "mp3",
        sample_rate: int = 22050,
        **kwargs: Any,
    ) -> SynthesisResult:
        # Return mock audio data (silence)
        duration = len(text) * 0.1  # Rough estimate
        audio_data = b"\x00" * int(sample_rate * duration * 2)  # 16-bit stereo
        
        return SynthesisResult(
            audio_data=audio_data,
            format=format,
            sample_rate=sample_rate,
            duration=duration,
        )


class NVIDIALLMProvider(LLMProviderBase):
    """NVIDIA NIM LLM provider using OpenAI-compatible API."""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        default_model: Optional[str] = None,
    ):
        self._api_key = api_key or os.getenv("NVIDIA_API_KEY")
        self._base_url = base_url or os.getenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1")
        self._default_model = default_model or os.getenv("NVIDIA_MODEL", "nvidia/nemotron-3-ultra-550b-a55b")
        self._client: Optional["AsyncOpenAI"] = None
    
    @property
    def name(self) -> str:
        return "nvidia"
    
    async def _get_client(self) -> "AsyncOpenAI":
        if self._client is None:
            try:
                from openai import AsyncOpenAI
                self._client = AsyncOpenAI(
                    api_key=self._api_key,
                    base_url=self._base_url,
                )
            except ImportError:
                raise RuntimeError("openai package not installed. Run: pip install openai")
        return self._client
    
    async def health_check(self) -> bool:
        try:
            client = await self._get_client()
            # Try a simple completion to verify connectivity
            await client.chat.completions.create(
                model=self._default_model,
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=5,
            )
            return True
        except Exception as e:
            logger.warning(f"NVIDIA health check failed: {e}")
            return False
    
    async def generate(
        self,
        messages: list[LLMMessage],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> LLMResponse:
        client = await self._get_client()
        model_name = model or self._default_model
        
        openai_messages = [{"role": m.role, "content": m.content} for m in messages]
        
        response = await client.chat.completions.create(
            model=model_name,
            messages=openai_messages,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs,
        )
        
        return LLMResponse(
            content=response.choices[0].message.content or "",
            model=response.model,
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
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        client = await self._get_client()
        model_name = model or self._default_model
        
        openai_messages = [{"role": m.role, "content": m.content} for m in messages]
        
        stream = await client.chat.completions.create(
            model=model_name,
            messages=openai_messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
            **kwargs,
        )
        
        async for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content


class GeminiLLMProvider(LLMProviderBase):
    """Google Gemini LLM provider (fallback)."""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        default_model: Optional[str] = None,
    ):
        self._api_key = api_key or os.getenv("GEMINI_API_KEY")
        self._default_model = default_model or "gemini-1.5-flash"
        self._model = None
    
    @property
    def name(self) -> str:
        return "gemini"
    
    async def _get_model(self):
        if self._model is None:
            try:
                import google.generativeai as genai
                genai.configure(api_key=self._api_key)
                self._model = genai.GenerativeModel(self._default_model)
            except ImportError:
                raise RuntimeError("google-generativeai package not installed. Run: pip install google-generativeai")
        return self._model
    
    async def health_check(self) -> bool:
        try:
            model = await self._get_model()
            # Simple test generation
            await model.generate_content_async("ping")
            return True
        except Exception as e:
            logger.warning(f"Gemini health check failed: {e}")
            return False
    
    async def generate(
        self,
        messages: list[LLMMessage],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> LLMResponse:
        model_instance = await self._get_model()
        model_name = model or self._default_model
        
        # Convert messages to Gemini format
        # Gemini expects a single prompt string or list of parts
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
        
        response = await model_instance.generate_content_async(
            prompt,
            generation_config=generation_config,
        )
        
        return LLMResponse(
            content=response.text or "",
            model=model_name,
            usage=None,  # Gemini doesn't provide token counts in the same way
            finish_reason="stop" if response.candidates and response.candidates[0].finish_reason == 1 else "unknown",
        )
    
    async def stream_generate(
        self,
        messages: list[LLMMessage],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> AsyncIterator[str]:
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
        
        response = await model_instance.generate_content_async(
            prompt,
            generation_config=generation_config,
            stream=True,
        )
        
        async for chunk in response:
            if chunk.text:
                yield chunk.text


class FallbackLLMProvider(LLMProviderBase):
    """LLM provider that automatically falls back from primary to secondary."""
    
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
    def provider_type(self) -> ProviderType:
        return ProviderType.LLM
    
    async def health_check(self) -> bool:
        primary_healthy = await self._primary.health_check()
        fallback_healthy = await self._fallback.health_check()
        return primary_healthy or fallback_healthy
    
    async def generate(
        self,
        messages: list[LLMMessage],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> LLMResponse:
        # Try primary first
        try:
            logger.info(f"Attempting generation with primary provider: {self._primary.name}")
            response = await self._primary.generate(messages, model, temperature, max_tokens, **kwargs)
            logger.info(f"Generation successful with primary provider: {self._primary.name}")
            return response
        except Exception as e:
            logger.warning(f"Primary provider {self._primary.name} failed: {e}. Falling back to {self._fallback.name}")
            try:
                response = await self._fallback.generate(messages, model, temperature, max_tokens, **kwargs)
                logger.info(f"Generation successful with fallback provider: {self._fallback.name}")
                return response
            except Exception as fallback_error:
                logger.error(f"Fallback provider {self._fallback.name} also failed: {fallback_error}")
                raise
    
    async def stream_generate(
        self,
        messages: list[LLMMessage],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        # Try primary first
        try:
            logger.info(f"Attempting streaming with primary provider: {self._primary.name}")
            async for chunk in self._primary.stream_generate(messages, model, temperature, max_tokens, **kwargs):
                yield chunk
            logger.info(f"Streaming successful with primary provider: {self._primary.name}")
            return
        except Exception as e:
            logger.warning(f"Primary provider {self._primary.name} streaming failed: {e}. Falling back to {self._fallback.name}")
            try:
                async for chunk in self._fallback.stream_generate(messages, model, temperature, max_tokens, **kwargs):
                    yield chunk
                logger.info(f"Streaming successful with fallback provider: {self._fallback.name}")
                return
            except Exception as fallback_error:
                logger.error(f"Fallback provider {self._fallback.name} streaming also failed: {fallback_error}")
                raise


class GroqSTTProvider(STTProviderBase):
    """Groq STT provider using Whisper."""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        default_model: Optional[str] = None,
    ):
        self._api_key = api_key or os.getenv("GROQ_API_KEY")
        self._default_model = default_model or "whisper-large-v3-turbo"
        self._client: Optional["AsyncGroq"] = None
    
    @property
    def name(self) -> str:
        return "groq"
    
    async def _get_client(self) -> "AsyncGroq":
        if self._client is None:
            try:
                from groq import AsyncGroq
                self._client = AsyncGroq(api_key=self._api_key)
            except ImportError:
                raise RuntimeError("groq package not installed. Run: pip install groq")
        return self._client
    
    async def health_check(self) -> bool:
        try:
            client = await self._get_client()
            # Groq doesn't have a simple health check, so we just verify client creation
            return self._api_key is not None
        except Exception as e:
            logger.warning(f"Groq health check failed: {e}")
            return False
    
    async def transcribe(
        self,
        audio_data: bytes,
        format: str = "webm",
        language: Optional[str] = None,
        **kwargs: Any,
    ) -> TranscriptionResult:
        client = await self._get_client()
        model = kwargs.get("model", self._default_model)
        
        # Create a file-like object from bytes
        import io
        audio_file = io.BytesIO(audio_data)
        audio_file.name = f"audio.{format}"
        
        response = await client.audio.transcriptions.create(
            file=audio_file,
            model=model,
            language=language,
            response_format="verbose_json",
        )
        
        return TranscriptionResult(
            text=response.text,
            language=response.language,
            duration=response.duration,
            confidence=None,  # Groq doesn't provide confidence scores
        )


class ProviderRegistry:
    """Registry for managing provider instances."""
    
    def __init__(self):
        self._llm_providers: dict[str, LLMProviderBase] = {}
        self._stt_providers: dict[str, STTProviderBase] = {}
        self._tts_providers: dict[str, TTSProviderBase] = {}
        self._default_llm: Optional[str] = None
        self._default_stt: Optional[str] = None
        self._default_tts: Optional[str] = None
    
    def register_llm(self, name: str, provider: LLMProviderBase, default: bool = False):
        """Register an LLM provider."""
        self._llm_providers[name] = provider
        if default or self._default_llm is None:
            self._default_llm = name
    
    def register_stt(self, name: str, provider: STTProviderBase, default: bool = False):
        """Register an STT provider."""
        self._stt_providers[name] = provider
        if default or self._default_stt is None:
            self._default_stt = name
    
    def register_tts(self, name: str, provider: TTSProviderBase, default: bool = False):
        """Register a TTS provider."""
        self._tts_providers[name] = provider
        if default or self._default_tts is None:
            self._default_tts = name
    
    def get_llm(self, name: Optional[str] = None) -> LLMProviderBase:
        """Get an LLM provider by name."""
        name = name or self._default_llm
        if name is None:
            raise ValueError("No LLM provider specified and no default set")
        if name not in self._llm_providers:
            raise ValueError(f"LLM provider '{name}' not found")
        return self._llm_providers[name]
    
    def get_stt(self, name: Optional[str] = None) -> STTProviderBase:
        """Get an STT provider by name."""
        name = name or self._default_stt
        if name is None:
            raise ValueError("No STT provider specified and no default set")
        if name not in self._stt_providers:
            raise ValueError(f"STT provider '{name}' not found")
        return self._stt_providers[name]
    
    def get_tts(self, name: Optional[str] = None) -> TTSProviderBase:
        """Get a TTS provider by name."""
        name = name or self._default_tts
        if name is None:
            raise ValueError("No TTS provider specified and no default set")
        if name not in self._tts_providers:
            raise ValueError(f"TTS provider '{name}' not found")
        return self._tts_providers[name]
    
    def list_llm_providers(self) -> list[str]:
        """List available LLM providers."""
        return list(self._llm_providers.keys())
    
    def list_stt_providers(self) -> list[str]:
        """List available STT providers."""
        return list(self._stt_providers.keys())
    
    def list_tts_providers(self) -> list[str]:
        """List available TTS providers."""
        return list(self._tts_providers.keys())


# Global registry instance
registry = ProviderRegistry()


def _configure_registry_from_env() -> None:
    """Configure the global registry from environment variables."""
    # Configure LLM providers
    llm_provider = os.getenv("LLM_PROVIDER", "mock").lower()
    
    if llm_provider == "nvidia":
        # NVIDIA primary with Gemini fallback
        nvidia_provider = NVIDIALLMProvider()
        gemini_provider = GeminiLLMProvider()
        fallback_provider = FallbackLLMProvider(nvidia_provider, gemini_provider)
        registry.register_llm("nvidia", nvidia_provider)
        registry.register_llm("gemini", gemini_provider)
        registry.register_llm("fallback", fallback_provider, default=True)
    elif llm_provider == "gemini":
        # Gemini only
        gemini_provider = GeminiLLMProvider()
        registry.register_llm("gemini", gemini_provider, default=True)
    elif llm_provider == "openai":
        # OpenAI would go here
        registry.register_llm("mock", MockLLMProvider(), default=True)
    else:
        # Default to mock
        registry.register_llm("mock", MockLLMProvider(), default=True)
    
    # Configure STT providers
    stt_provider = os.getenv("STT_PROVIDER", "mock").lower()
    
    if stt_provider == "groq":
        groq_provider = GroqSTTProvider()
        registry.register_stt("groq", groq_provider, default=True)
    else:
        registry.register_stt("mock", MockSTTProvider(), default=True)
    
    # Configure TTS providers
    tts_provider = os.getenv("TTS_PROVIDER", "mock").lower()
    
    if tts_provider == "elevenlabs":
        # ElevenLabs would go here (M34)
        registry.register_tts("mock", MockTTSProvider(), default=True)
    else:
        registry.register_tts("mock", MockTTSProvider(), default=True)


# Auto-configure on import
_configure_registry_from_env()


def get_llm_provider(name: Optional[str] = None) -> LLMProviderBase:
    """Get an LLM provider from the global registry."""
    return registry.get_llm(name)


def get_stt_provider(name: Optional[str] = None) -> STTProviderBase:
    """Get an STT provider from the global registry."""
    return registry.get_stt(name)


def get_tts_provider(name: Optional[str] = None) -> TTSProviderBase:
    """Get a TTS provider from the global registry."""
    return registry.get_tts(name)