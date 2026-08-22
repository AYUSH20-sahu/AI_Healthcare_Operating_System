"""Tests for Provider Adapter."""

import os
import sys
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch

# Add the ai-services directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from providers import (
    ProviderType,
    LLMMessage,
    LLMResponse,
    TranscriptionResult,
    SynthesisResult,
    MockLLMProvider,
    MockSTTProvider,
    MockTTSProvider,
    NVIDIALLMProvider,
    GeminiLLMProvider,
    FallbackLLMProvider,
    GroqSTTProvider,
    ProviderRegistry,
    LLMProviderBase,
    STTProviderBase,
    TTSProviderBase,
    get_llm_provider,
    get_stt_provider,
    get_tts_provider,
)


class TestMockLLMProvider:
    """Tests for MockLLMProvider."""

    @pytest_asyncio.fixture
    async def provider(self):
        return MockLLMProvider()

    @pytest.mark.asyncio
    async def test_health_check(self, provider):
        """Test health check returns True."""
        assert await provider.health_check() is True

    @pytest.mark.asyncio
    async def test_name(self, provider):
        """Test provider name."""
        assert provider.name == "mock"

    @pytest.mark.asyncio
    async def test_provider_type(self, provider):
        """Test provider type."""
        assert provider.provider_type == ProviderType.LLM

    @pytest.mark.asyncio
    async def test_generate_clinical_note(self, provider):
        """Test generating a clinical note."""
        messages = [
            LLMMessage(role="system", content="You are a medical scribe."),
            LLMMessage(role="user", content="Create a clinical note for chest pain"),
        ]
        response = await provider.generate(messages)
        
        assert isinstance(response, LLMResponse)
        assert "chief_complaint" in response.content
        assert "Chest pain" in response.content
        assert response.model == "mock-model"
        assert response.finish_reason == "stop"

    @pytest.mark.asyncio
    async def test_generate_prescription(self, provider):
        """Test generating a prescription."""
        messages = [
            LLMMessage(role="system", content="You are a prescription writer."),
            LLMMessage(role="user", content="Create a prescription for hypertension"),
        ]
        response = await provider.generate(messages)
        
        assert isinstance(response, LLMResponse)
        assert "medications" in response.content
        assert "Aspirin" in response.content

    @pytest.mark.asyncio
    async def test_generate_generic(self, provider):
        """Test generating a generic response."""
        messages = [
            LLMMessage(role="user", content="Hello world"),
        ]
        response = await provider.generate(messages)
        
        assert isinstance(response, LLMResponse)
        assert "Mock response to: Hello world" in response.content

    @pytest.mark.asyncio
    async def test_stream_generate(self, provider):
        """Test streaming generation."""
        messages = [
            LLMMessage(role="user", content="Test streaming"),
        ]
        chunks = []
        async for chunk in provider.stream_generate(messages):
            chunks.append(chunk)
        
        full_response = "".join(chunks)
        assert "Mock response to: Test streaming" in full_response


class TestMockSTTProvider:
    """Tests for MockSTTProvider."""

    @pytest_asyncio.fixture
    async def provider(self):
        return MockSTTProvider()

    @pytest.mark.asyncio
    async def test_health_check(self, provider):
        """Test health check returns True."""
        assert await provider.health_check() is True

    @pytest.mark.asyncio
    async def test_name(self, provider):
        """Test provider name."""
        assert provider.name == "mock"

    @pytest.mark.asyncio
    async def test_provider_type(self, provider):
        assert provider.provider_type == ProviderType.STT

    @pytest.mark.asyncio
    async def test_transcribe(self, provider):
        """Test transcription."""
        audio_data = b"fake audio data"
        result = await provider.transcribe(audio_data, format="webm", language="en")
        
        assert isinstance(result, TranscriptionResult)
        assert result.text == "This is a mock transcription of the audio file."
        assert result.language == "en"
        assert result.duration == 30.0
        assert result.confidence == 0.95


class TestMockTTSProvider:
    """Tests for MockTTSProvider."""

    @pytest_asyncio.fixture
    async def provider(self):
        return MockTTSProvider()

    @pytest.mark.asyncio
    async def test_health_check(self, provider):
        """Test health check returns True."""
        assert await provider.health_check() is True

    @pytest.mark.asyncio
    async def test_name(self, provider):
        """Test provider name."""
        assert provider.name == "mock"

    @pytest.mark.asyncio
    async def test_provider_type(self, provider):
        assert provider.provider_type == ProviderType.TTS

    @pytest.mark.asyncio
    async def test_synthesize(self, provider):
        """Test speech synthesis."""
        text = "Hello world"
        result = await provider.synthesize(text, voice="default", format="mp3", sample_rate=22050)
        
        assert isinstance(result, SynthesisResult)
        assert result.format == "mp3"
        assert result.sample_rate == 22050
        assert result.duration is not None
        assert len(result.audio_data) > 0


class TestProviderRegistry:
    """Tests for ProviderRegistry."""

    @pytest_asyncio.fixture
    async def registry(self):
        return ProviderRegistry()

    @pytest.mark.asyncio
    async def test_register_llm(self, registry):
        """Test registering an LLM provider."""
        provider = MockLLMProvider()
        registry.register_llm("test-llm", provider, default=True)
        
        assert "test-llm" in registry.list_llm_providers()
        assert registry.get_llm("test-llm") is provider
        assert registry.get_llm() is provider  # default

    @pytest.mark.asyncio
    async def test_register_stt(self, registry):
        """Test registering an STT provider."""
        provider = MockSTTProvider()
        registry.register_stt("test-stt", provider, default=True)
        
        assert "test-stt" in registry.list_stt_providers()
        assert registry.get_stt("test-stt") is provider
        assert registry.get_stt() is provider  # default

    @pytest.mark.asyncio
    async def test_register_tts(self, registry):
        """Test registering a TTS provider."""
        provider = MockTTSProvider()
        registry.register_tts("test-tts", provider, default=True)
        
        assert "test-tts" in registry.list_tts_providers()
        assert registry.get_tts("test-tts") is provider
        assert registry.get_tts() is provider  # default

    @pytest.mark.asyncio
    async def test_get_llm_not_found(self, registry):
        """Test getting non-existent LLM provider raises error."""
        with pytest.raises(ValueError, match="LLM provider 'nonexistent' not found"):
            registry.get_llm("nonexistent")

    @pytest.mark.asyncio
    async def test_get_stt_not_found(self, registry):
        """Test getting non-existent STT provider raises error."""
        with pytest.raises(ValueError, match="STT provider 'nonexistent' not found"):
            registry.get_stt("nonexistent")

    @pytest.mark.asyncio
    async def test_get_tts_not_found(self, registry):
        """Test getting non-existent TTS provider raises error."""
        with pytest.raises(ValueError, match="TTS provider 'nonexistent' not found"):
            registry.get_tts("nonexistent")

    @pytest.mark.asyncio
    async def test_get_llm_no_default(self, registry):
        """Test getting LLM without default raises error."""
        # Create a fresh registry without defaults
        fresh_registry = ProviderRegistry()
        with pytest.raises(ValueError, match="No LLM provider specified and no default set"):
            fresh_registry.get_llm()


class TestGlobalRegistry:
    """Tests for global registry functions."""

    @pytest.mark.asyncio
    async def test_get_llm_provider(self):
        """Test getting LLM provider from global registry."""
        provider = get_llm_provider("mock")
        from providers import MockLLMProvider
        assert isinstance(provider, MockLLMProvider)

    @pytest.mark.asyncio
    async def test_get_stt_provider(self):
        """Test getting STT provider from global registry."""
        provider = get_stt_provider("mock")
        from providers import MockSTTProvider
        assert isinstance(provider, MockSTTProvider)

    @pytest.mark.asyncio
    async def test_get_tts_provider(self):
        """Test getting TTS provider from global registry."""
        provider = get_tts_provider("mock")
        from providers import MockTTSProvider
        assert isinstance(provider, MockTTSProvider)

    @pytest.mark.asyncio
    async def test_get_llm_provider_default(self):
        """Test getting default LLM provider."""
        provider = get_llm_provider()
        from providers import MockLLMProvider
        assert isinstance(provider, MockLLMProvider)

    @pytest.mark.asyncio
    async def test_get_stt_provider_default(self):
        """Test getting default STT provider."""
        provider = get_stt_provider()
        from providers import MockSTTProvider
        assert isinstance(provider, MockSTTProvider)

    @pytest.mark.asyncio
    async def test_get_tts_provider_default(self):
        """Test getting default TTS provider."""
        provider = get_tts_provider()
        from providers import MockTTSProvider
        assert isinstance(provider, MockTTSProvider)


class TestIntegration:
    """Integration tests for provider adapter."""

    @pytest.mark.asyncio
    async def test_llm_generate_and_stream(self):
        """Test LLM generate and stream produce consistent results."""
        from providers import MockLLMProvider, LLMMessage
        provider = MockLLMProvider()
        
        messages = [LLMMessage(role="user", content="Test")]
        
        # Generate
        response = await provider.generate(messages)
        
        # Stream
        chunks = []
        async for chunk in provider.stream_generate(messages):
            pass  # Just consume
        
        # Both should work without errors
        assert response.content is not None

    @pytest.mark.asyncio
    async def test_stt_transcribe_with_different_formats(self):
        """Test STT with different audio formats."""
        provider = MockSTTProvider()
        
        for fmt in ["webm", "mp3", "wav", "ogg"]:
            result = await provider.transcribe(b"audio", format=fmt)
            assert isinstance(result, TranscriptionResult)

    @pytest.mark.asyncio
    async def test_tts_synthesize_with_different_formats(self):
        """Test TTS with different formats."""
        provider = MockTTSProvider()
        
        for fmt in ["mp3", "wav", "ogg"]:
            result = await provider.synthesize("Test", format=fmt)
            assert isinstance(result, SynthesisResult)
            assert result.format == fmt

    @pytest.mark.asyncio
    async def test_registry_multiple_providers(self):
        """Test registry with multiple providers."""
        registry = ProviderRegistry()
        
        registry.register_llm("provider1", MockLLMProvider())
        registry.register_llm("provider2", MockLLMProvider())
        
        assert len(registry.list_llm_providers()) == 2
        assert "provider1" in registry.list_llm_providers()
        assert "provider2" in registry.list_llm_providers()


class TestNVIDIALLMProvider:
    """Tests for NVIDIALLMProvider."""

    @pytest_asyncio.fixture
    async def provider(self):
        return NVIDIALLMProvider(
            api_key="test-key",
            base_url="https://test.api.nvidia.com/v1",
            default_model="test-model",
        )

    @pytest.mark.asyncio
    async def test_name(self, provider):
        """Test provider name."""
        assert provider.name == "nvidia"

    @pytest.mark.asyncio
    async def test_provider_type(self, provider):
        assert provider.provider_type == ProviderType.LLM

    @pytest.mark.asyncio
    async def test_health_check_success(self, provider):
        """Test health check when API is available."""
        with patch("openai.AsyncOpenAI") as mock_openai:
            mock_client = AsyncMock()
            mock_openai.return_value = mock_client
            mock_client.chat.completions.create = AsyncMock(
                return_value=MagicMock(choices=[MagicMock(message=MagicMock(content="pong"))])
            )
            
            result = await provider.health_check()
            assert result is True

    @pytest.mark.asyncio
    async def test_health_check_failure(self, provider):
        """Test health check when API fails."""
        with patch("openai.AsyncOpenAI") as mock_openai:
            mock_client = AsyncMock()
            mock_openai.return_value = mock_client
            mock_client.chat.completions.create = AsyncMock(side_effect=Exception("API Error"))
            
            result = await provider.health_check()
            assert result is False

    @pytest.mark.asyncio
    async def test_generate(self, provider):
        """Test generate method."""
        with patch("openai.AsyncOpenAI") as mock_openai:
            mock_client = AsyncMock()
            mock_openai.return_value = mock_client
            mock_response = MagicMock()
            mock_response.choices = [MagicMock(message=MagicMock(content="Test response"), finish_reason="stop")]
            mock_response.model = "test-model"
            mock_response.usage = MagicMock(prompt_tokens=10, completion_tokens=20, total_tokens=30)
            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
            
            messages = [LLMMessage(role="user", content="Test")]
            response = await provider.generate(messages)
            
            assert isinstance(response, LLMResponse)
            assert response.content == "Test response"
            assert response.model == "test-model"
            assert response.usage["total_tokens"] == 30

    @pytest.mark.asyncio
    async def test_stream_generate(self, provider):
        """Test stream_generate method."""
        with patch("openai.AsyncOpenAI") as mock_openai:
            mock_client = AsyncMock()
            mock_openai.return_value = mock_client
            
            # Create async iterator for streaming
            async def mock_stream():
                for chunk_text in ["Hello", " ", "World"]:
                    yield MagicMock(choices=[MagicMock(delta=MagicMock(content=chunk_text))])
            
            mock_client.chat.completions.create = AsyncMock(return_value=mock_stream())
            
            messages = [LLMMessage(role="user", content="Test")]
            chunks = []
            async for chunk in provider.stream_generate(messages):
                chunks.append(chunk)
            
            assert chunks == ["Hello", " ", "World"]


class TestGeminiLLMProvider:
    """Tests for GeminiLLMProvider."""

    @pytest_asyncio.fixture
    async def provider(self):
        return GeminiLLMProvider(api_key="test-key", default_model="gemini-1.5-flash")

    @pytest.mark.asyncio
    async def test_name(self, provider):
        """Test provider name."""
        assert provider.name == "gemini"

    @pytest.mark.asyncio
    async def test_provider_type(self, provider):
        assert provider.provider_type == ProviderType.LLM

    @pytest.mark.asyncio
    async def test_health_check_success(self, provider):
        """Test health check when API is available."""
        with patch("google.generativeai.GenerativeModel") as mock_model_class:
            mock_model = AsyncMock()
            mock_model_class.return_value = mock_model
            mock_model.generate_content_async = AsyncMock(return_value=MagicMock(text="pong"))
            
            result = await provider.health_check()
            assert result is True

    @pytest.mark.asyncio
    async def test_health_check_failure(self, provider):
        """Test health check when API fails."""
        with patch("google.generativeai.GenerativeModel") as mock_model_class:
            mock_model = AsyncMock()
            mock_model_class.return_value = mock_model
            mock_model.generate_content_async = AsyncMock(side_effect=Exception("API Error"))
            
            result = await provider.health_check()
            assert result is False

    @pytest.mark.asyncio
    async def test_generate(self, provider):
        """Test generate method."""
        with patch("google.generativeai.GenerativeModel") as mock_model_class:
            mock_model = AsyncMock()
            mock_model_class.return_value = mock_model
            mock_response = MagicMock()
            mock_response.text = "Test response"
            mock_response.candidates = [MagicMock(finish_reason=1)]
            mock_model.generate_content_async = AsyncMock(return_value=mock_response)
            
            messages = [LLMMessage(role="user", content="Test")]
            response = await provider.generate(messages)
            
            assert isinstance(response, LLMResponse)
            assert response.content == "Test response"
            assert response.model == "gemini-1.5-flash"

    @pytest.mark.asyncio
    async def test_stream_generate(self, provider):
        """Test stream_generate method."""
        with patch("google.generativeai.GenerativeModel") as mock_model_class:
            mock_model = AsyncMock()
            mock_model_class.return_value = mock_model
            
            async def mock_stream():
                for chunk_text in ["Hello", " ", "World"]:
                    yield MagicMock(text=chunk_text)
            
            mock_model.generate_content_async = AsyncMock(return_value=mock_stream())
            
            messages = [LLMMessage(role="user", content="Test")]
            chunks = []
            async for chunk in provider.stream_generate(messages):
                chunks.append(chunk)
            
            assert chunks == ["Hello", " ", "World"]


class TestFallbackLLMProvider:
    """Tests for FallbackLLMProvider - the critical NVIDIA->Gemini fallback path."""

    @pytest_asyncio.fixture
    async def primary_provider(self):
        """Mock primary provider that fails."""
        provider = AsyncMock(spec=LLMProviderBase)
        provider.name = "nvidia"
        provider.provider_type = ProviderType.LLM
        provider.generate = AsyncMock(side_effect=Exception("Rate limited"))
        
        async def failing_stream():
            raise Exception("Rate limited")
            yield  # Make it an async generator
        
        # Return the async generator directly (not a coroutine)
        provider.stream_generate = MagicMock(return_value=failing_stream())
        provider.health_check = AsyncMock(return_value=False)
        return provider

    @pytest_asyncio.fixture
    async def fallback_provider(self):
        """Mock fallback provider that succeeds."""
        provider = AsyncMock(spec=LLMProviderBase)
        provider.name = "gemini"
        provider.provider_type = ProviderType.LLM
        provider.generate = AsyncMock(return_value=LLMResponse(
            content="Fallback response",
            model="gemini-1.5-flash",
            finish_reason="stop",
        ))
        
        async def mock_stream():
            yield "Fallback"
            yield " response"
        
        provider.stream_generate = MagicMock(return_value=mock_stream())
        provider.health_check = AsyncMock(return_value=True)
        return provider

    @pytest_asyncio.fixture
    async def fallback_llm(self, primary_provider, fallback_provider):
        return FallbackLLMProvider(primary_provider, fallback_provider)

    @pytest.mark.asyncio
    async def test_name(self, fallback_llm):
        """Test provider name includes both providers."""
        assert fallback_llm.name == "nvidia->gemini"

    @pytest.mark.asyncio
    async def test_provider_type(self, fallback_llm):
        assert fallback_llm.provider_type == ProviderType.LLM

    @pytest.mark.asyncio
    async def test_health_check(self, fallback_llm, primary_provider, fallback_provider):
        """Test health check returns True if either provider is healthy."""
        result = await fallback_llm.health_check()
        assert result is True
        primary_provider.health_check.assert_called_once()
        fallback_provider.health_check.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_fallback_on_primary_failure(self, fallback_llm, primary_provider, fallback_provider):
        """Test that generate falls back to secondary provider when primary fails."""
        messages = [LLMMessage(role="user", content="Test")]
        
        response = await fallback_llm.generate(messages)
        
        # Primary should have been called first
        primary_provider.generate.assert_called_once_with(messages, None, 0.7, None)
        # Fallback should have been called after primary failed
        fallback_provider.generate.assert_called_once_with(messages, None, 0.7, None)
        # Response should be from fallback
        assert response.content == "Fallback response"
        assert response.model == "gemini-1.5-flash"

    @pytest.mark.asyncio
    async def test_generate_primary_succeeds_no_fallback(self, fallback_llm, primary_provider, fallback_provider):
        """Test that fallback is NOT called when primary succeeds."""
        primary_provider.generate = AsyncMock(return_value=LLMResponse(
            content="Primary response",
            model="nvidia/nemotron-3-ultra",
            finish_reason="stop",
        ))
        primary_provider.health_check = AsyncMock(return_value=True)
        
        messages = [LLMMessage(role="user", content="Test")]
        response = await fallback_llm.generate(messages)
        
        primary_provider.generate.assert_called_once()
        fallback_provider.generate.assert_not_called()
        assert response.content == "Primary response"

    @pytest.mark.asyncio
    async def test_generate_both_fail_raises(self, fallback_llm, primary_provider, fallback_provider):
        """Test that exception is raised when both providers fail."""
        fallback_provider.generate = AsyncMock(side_effect=Exception("Also failed"))
        
        messages = [LLMMessage(role="user", content="Test")]
        
        with pytest.raises(Exception, match="Also failed"):
            await fallback_llm.generate(messages)
        
        primary_provider.generate.assert_called_once()
        fallback_provider.generate.assert_called_once()

    @pytest.mark.asyncio
    async def test_stream_generate_fallback_on_primary_failure(self, fallback_llm, primary_provider, fallback_provider):
        """Test that stream_generate falls back to secondary provider when primary fails."""
        messages = [LLMMessage(role="user", content="Test")]
        
        chunks = []
        async for chunk in fallback_llm.stream_generate(messages):
            chunks.append(chunk)
        
        # Primary should have been called first
        primary_provider.stream_generate.assert_called_once()
        # Fallback should have been called after primary failed
        fallback_provider.stream_generate.assert_called_once()
        # Response should be from fallback
        assert chunks == ["Fallback", " response"]

    @pytest.mark.asyncio
    async def test_stream_generate_primary_succeeds_no_fallback(self, fallback_llm, primary_provider, fallback_provider):
        """Test that fallback is NOT called for streaming when primary succeeds."""
        async def primary_stream():
            yield "Primary"
            yield " stream"
        
        primary_provider.stream_generate = MagicMock(return_value=primary_stream())
        primary_provider.health_check = AsyncMock(return_value=True)
        
        messages = [LLMMessage(role="user", content="Test")]
        chunks = []
        async for chunk in fallback_llm.stream_generate(messages):
            chunks.append(chunk)
        
        primary_provider.stream_generate.assert_called_once()
        fallback_provider.stream_generate.assert_not_called()
        assert chunks == ["Primary", " stream"]


class TestGroqSTTProvider:
    """Tests for GroqSTTProvider."""

    @pytest_asyncio.fixture
    async def provider(self):
        return GroqSTTProvider(api_key="test-key", default_model="whisper-large-v3-turbo")

    @pytest.mark.asyncio
    async def test_name(self, provider):
        """Test provider name."""
        assert provider.name == "groq"

    @pytest.mark.asyncio
    async def test_provider_type(self, provider):
        assert provider.provider_type == ProviderType.STT

    @pytest.mark.asyncio
    async def test_health_check(self, provider):
        """Test health check."""
        result = await provider.health_check()
        assert result is True

    @pytest.mark.asyncio
    async def test_transcribe(self, provider):
        """Test transcribe method."""
        with patch("groq.AsyncGroq") as mock_groq:
            mock_client = AsyncMock()
            mock_groq.return_value = mock_client
            mock_response = MagicMock()
            mock_response.text = "Transcribed text"
            mock_response.language = "en"
            mock_response.duration = 5.5
            mock_client.audio.transcriptions.create = AsyncMock(return_value=mock_response)
            
            audio_data = b"fake audio data"
            result = await provider.transcribe(audio_data, format="webm", language="en")
            
            assert isinstance(result, TranscriptionResult)
            assert result.text == "Transcribed text"
            assert result.language == "en"
            assert result.duration == 5.5
            assert result.confidence is None


class TestProviderRegistryAutoConfig:
    """Tests for auto-configuration from environment variables."""

    @pytest.mark.asyncio
    async def test_auto_config_nvidia_with_gemini_fallback(self):
        """Test registry auto-configures NVIDIA primary with Gemini fallback."""
        with patch.dict(os.environ, {
            "LLM_PROVIDER": "nvidia",
            "NVIDIA_API_KEY": "test-nvidia-key",
            "NVIDIA_BASE_URL": "https://test.nvidia.com/v1",
            "NVIDIA_MODEL": "test-model",
            "GEMINI_API_KEY": "test-gemini-key",
            "STT_PROVIDER": "mock",
            "TTS_PROVIDER": "mock",
        }):
            # Need to re-import to trigger auto-config
            import importlib
            import providers
            importlib.reload(providers)
            
            from providers import registry, FallbackLLMProvider
            
            # Should have fallback provider as default
            default_llm = registry.get_llm()
            assert isinstance(default_llm, FallbackLLMProvider)
            assert default_llm.name == "nvidia->gemini"

    @pytest.mark.asyncio
    async def test_auto_config_gemini_only(self):
        """Test registry auto-configures Gemini only."""
        with patch.dict(os.environ, {
            "LLM_PROVIDER": "gemini",
            "GEMINI_API_KEY": "test-gemini-key",
            "STT_PROVIDER": "mock",
            "TTS_PROVIDER": "mock",
        }):
            import importlib
            import providers
            importlib.reload(providers)
            
            from providers import registry, GeminiLLMProvider
            
            default_llm = registry.get_llm()
            assert isinstance(default_llm, GeminiLLMProvider)

    @pytest.mark.asyncio
    async def test_auto_config_groq_stt(self):
        """Test registry auto-configures Groq STT."""
        with patch.dict(os.environ, {
            "LLM_PROVIDER": "mock",
            "STT_PROVIDER": "groq",
            "GROQ_API_KEY": "test-groq-key",
            "TTS_PROVIDER": "mock",
        }):
            import importlib
            import providers
            importlib.reload(providers)
            
            from providers import registry, GroqSTTProvider
            
            default_stt = registry.get_stt()
            assert isinstance(default_stt, GroqSTTProvider)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])