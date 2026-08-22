"""Tests for Doctor Copilot Scribe Agent."""

import asyncio
import json
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import sys
import os

# Add the ai-services directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agents.scribe_agent import (
    ScribeAgent,
    ClinicalNoteDraft,
    ScribeAgentResult,
    register_scribe_agent,
)
from orchestrator import TaskType, TaskRequest
from providers import TranscriptionResult


class TestClinicalNoteDraft:
    """Tests for ClinicalNoteDraft dataclass."""

    def test_default_values(self):
        """Test default values."""
        draft = ClinicalNoteDraft(
            chief_complaint="Chest pain",
            history_present_illness="Patient reports chest pain for 2 hours",
            physical_examination="BP 140/90, HR 88",
            assessment="Possible angina",
            plan="ECG, troponin, cardiology referral",
        )
        
        assert draft.diagnosis_codes == []
        assert draft.confidence == 0.0
        assert draft.basis == ""
        assert draft.raw_transcription == ""

    def test_custom_values(self):
        """Test custom values."""
        draft = ClinicalNoteDraft(
            chief_complaint="Chest pain",
            history_present_illness="Patient reports chest pain for 2 hours",
            physical_examination="BP 140/90, HR 88",
            assessment="Possible angina",
            plan="ECG, troponin, cardiology referral",
            diagnosis_codes=["I20.9"],
            confidence=0.95,
            basis="Transcription clearly describes chest pain symptoms",
            raw_transcription="Patient says chest pain for 2 hours...",
        )
        
        assert draft.diagnosis_codes == ["I20.9"]
        assert draft.confidence == 0.95
        assert "chest pain" in draft.basis.lower()


class TestScribeAgentResult:
    """Tests for ScribeAgentResult."""

    def test_success_result(self):
        """Test successful result."""
        draft = ClinicalNoteDraft(
            chief_complaint="Test",
            history_present_illness="Test",
            physical_examination="Test",
            assessment="Test",
            plan="Test",
        )
        transcription = TranscriptionResult(text="Test transcription", language="en")
        
        result = ScribeAgentResult(draft=draft, transcription=transcription, success=True)
        
        assert result.success is True
        assert result.draft is draft
        assert result.transcription is transcription
        assert result.error is None

    def test_failure_result(self):
        """Test failure result."""
        result = ScribeAgentResult(
            draft=None,
            transcription=None,
            success=False,
            error="Something went wrong",
        )
        
        assert result.success is False
        assert result.error == "Something went wrong"
        assert result.draft is None


class TestScribeAgent:
    """Tests for ScribeAgent."""

    @pytest_asyncio.fixture
    async def mock_llm_provider(self):
        """Mock LLM provider."""
        provider = AsyncMock()
        provider.generate = AsyncMock(return_value=MagicMock(
            content=json.dumps({
                "chief_complaint": "Chest pain",
                "history_present_illness": "Patient reports chest pain for 2 hours, radiating to left arm",
                "physical_examination": "BP 140/90, HR 88, RR 18, O2 98%",
                "assessment": "Acute coronary syndrome, rule out MI",
                "plan": "ECG, troponin x3, aspirin 325mg, cardiology consult",
                "diagnosis_codes": ["I20.0", "I21.9"],
                "confidence": 0.92,
                "basis": "Transcription describes classic anginal symptoms with radiation",
            })
        ))
        return provider

    @pytest_asyncio.fixture
    async def mock_stt_provider(self):
        """Mock STT provider."""
        provider = AsyncMock()
        provider.transcribe = AsyncMock(return_value=TranscriptionResult(
            text="Patient reports chest pain for 2 hours, radiating to left arm. Blood pressure 140 over 90, heart rate 88.",
            language="en",
            duration=15.5,
            confidence=0.95,
        ))
        return provider

    @pytest_asyncio.fixture
    async def scribe_agent(self):
        """Create scribe agent (providers will be mocked in each test)."""
        return ScribeAgent()

    @pytest.mark.asyncio
    async def test_task_type(self, scribe_agent):
        """Test agent task type."""
        assert scribe_agent.task_type == TaskType.SCRIBE

    @pytest.mark.asyncio
    async def test_execute_success(self, scribe_agent, mock_llm_provider, mock_stt_provider):
        """Test successful execution."""
        audio_data = b"fake audio data"
        payload = {
            "audio_data": audio_data,
            "audio_format": "webm",
            "language": "en",
            "patient_id": "123",
            "doctor_id": "456",
            "appointment_id": "789",
        }
        
        with patch("agents.scribe_agent.get_llm_provider", return_value=mock_llm_provider):
            with patch("agents.scribe_agent.get_stt_provider", return_value=mock_stt_provider):
                result = await scribe_agent.execute(payload)
        
        assert result.success is True
        assert result.draft is not None
        assert result.transcription is not None
        assert result.error is None
        
        # Verify draft content
        assert result.draft.chief_complaint == "Chest pain"
        assert "chest pain" in result.draft.history_present_illness.lower()
        assert result.draft.confidence == 0.92
        assert "radiation" in result.draft.basis.lower()
        assert result.draft.diagnosis_codes == ["I20.0", "I21.9"]
        
        # Verify transcription
        assert result.transcription.text == "Patient reports chest pain for 2 hours, radiating to left arm. Blood pressure 140 over 90, heart rate 88."
        assert result.transcription.language == "en"
        assert result.transcription.duration == 15.5
        
        # Verify providers were called
        mock_stt_provider.transcribe.assert_called_once_with(
            audio_data=audio_data,
            format="webm",
            language="en",
        )
        mock_llm_provider.generate.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_no_audio_data(self, scribe_agent):
        """Test execution with missing audio data."""
        payload = {"patient_id": "123"}
        
        result = await scribe_agent.execute(payload)
        
        assert result.success is False
        assert "No audio_data provided" in result.error
        assert result.draft is None
        assert result.transcription is None

    @pytest.mark.asyncio
    async def test_execute_stt_failure(self, scribe_agent, mock_llm_provider, mock_stt_provider):
        """Test execution when STT fails."""
        mock_stt_provider.transcribe = AsyncMock(side_effect=Exception("STT service unavailable"))
        
        payload = {"audio_data": b"audio", "audio_format": "webm"}
        
        with patch("agents.scribe_agent.get_llm_provider", return_value=mock_llm_provider):
            with patch("agents.scribe_agent.get_stt_provider", return_value=mock_stt_provider):
                result = await scribe_agent.execute(payload)
        
        assert result.success is False
        assert "STT service unavailable" in result.error

    @pytest.mark.asyncio
    async def test_execute_llm_failure(self, scribe_agent, mock_llm_provider, mock_stt_provider):
        """Test execution when LLM fails."""
        mock_llm_provider.generate = AsyncMock(side_effect=Exception("LLM service unavailable"))
        
        payload = {"audio_data": b"audio", "audio_format": "webm"}
        
        with patch("agents.scribe_agent.get_llm_provider", return_value=mock_llm_provider):
            with patch("agents.scribe_agent.get_stt_provider", return_value=mock_stt_provider):
                result = await scribe_agent.execute(payload)
        
        assert result.success is False
        assert "LLM service unavailable" in result.error

    @pytest.mark.asyncio
    async def test_execute_llm_invalid_json(self, scribe_agent, mock_llm_provider, mock_stt_provider):
        """Test execution when LLM returns invalid JSON."""
        mock_llm_provider.generate = AsyncMock(return_value=MagicMock(
            content="This is not valid JSON at all"
        ))
        
        payload = {"audio_data": b"audio", "audio_format": "webm"}
        
        with patch("agents.scribe_agent.get_llm_provider", return_value=mock_llm_provider):
            with patch("agents.scribe_agent.get_stt_provider", return_value=mock_stt_provider):
                result = await scribe_agent.execute(payload)
        
        # Should still succeed but with fallback parsing
        assert result.success is True
        assert result.draft is not None
        assert result.draft.confidence == 0.3  # Low confidence for fallback
        assert "could not be parsed" in result.draft.basis.lower()

    @pytest.mark.asyncio
    async def test_execute_default_format_and_language(self, scribe_agent, mock_llm_provider, mock_stt_provider):
        """Test execution with default format and language."""
        payload = {"audio_data": b"audio"}
        
        with patch("agents.scribe_agent.get_llm_provider", return_value=mock_llm_provider):
            with patch("agents.scribe_agent.get_stt_provider", return_value=mock_stt_provider):
                await scribe_agent.execute(payload)
        
        mock_stt_provider.transcribe.assert_called_once_with(
            audio_data=b"audio",
            format="webm",  # default
            language="en",  # default
        )

    @pytest.mark.asyncio
    async def test_execute_custom_providers(self, mock_llm_provider, mock_stt_provider):
        """Test agent with custom provider names."""
        with patch("agents.scribe_agent.get_llm_provider", return_value=mock_llm_provider) as mock_get_llm:
            with patch("agents.scribe_agent.get_stt_provider", return_value=mock_stt_provider) as mock_get_stt:
                agent = ScribeAgent(
                    llm_provider_name="custom-llm",
                    stt_provider_name="custom-stt",
                )
                
                payload = {"audio_data": b"audio"}
                await agent.execute(payload)
                
                mock_get_llm.assert_called_once_with("custom-llm")
                mock_get_stt.assert_called_once_with("custom-stt")


class TestRegisterScribeAgent:
    """Tests for register_scribe_agent function."""

    @pytest.mark.asyncio
    async def test_register_scribe_agent(self):
        """Test registering scribe agent with orchestrator."""
        # Patch the get_orchestrator function where it's imported in the function
        with patch("orchestrator.get_orchestrator") as mock_get_orch:
            mock_orch = MagicMock()
            mock_get_orch.return_value = mock_orch
            
            agent = register_scribe_agent()
            
            assert isinstance(agent, ScribeAgent)
            mock_orch.register_agent.assert_called_once_with(agent)


# Need to import json for the mock
import json


if __name__ == "__main__":
    pytest.main([__file__, "-v"])