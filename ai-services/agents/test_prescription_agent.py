"""Tests for Prescription Drafting Agent."""

import json
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import sys
import os

# Add the ai-services directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agents.prescription_agent import (
    PrescriptionAgent,
    MedicationDraft,
    InteractionWarning,
    PrescriptionDraft,
    PrescriptionAgentResult,
    register_prescription_agent,
)
from orchestrator import TaskType


class TestMedicationDraft:
    """Tests for MedicationDraft dataclass."""

    def test_default_values(self):
        """Test default values."""
        med = MedicationDraft(
            name="Aspirin",
            dosage="81mg",
            frequency="once daily",
            duration="30 days",
        )
        
        assert med.route == "oral"
        assert med.instructions == ""
        assert med.quantity is None
        assert med.refills == 0

    def test_custom_values(self):
        """Test custom values."""
        med = MedicationDraft(
            name="Metoprolol",
            dosage="50mg",
            frequency="twice daily",
            duration="30 days",
            route="oral",
            instructions="Take with food",
            quantity=60,
            refills=2,
        )
        
        assert med.route == "oral"
        assert med.instructions == "Take with food"
        assert med.quantity == 60
        assert med.refills == 2


class TestInteractionWarning:
    """Tests for InteractionWarning dataclass."""

    def test_interaction_warning(self):
        """Test interaction warning."""
        warning = InteractionWarning(
            severity="severe",
            type="interaction",
            medication="Warfarin + Aspirin",
            description="Increased bleeding risk",
            recommendation="Monitor INR",
        )
        
        assert warning.severity == "severe"
        assert warning.type == "interaction"
        assert warning.recommendation == "Monitor INR"

    def test_allergy_warning(self):
        """Test allergy warning."""
        warning = InteractionWarning(
            severity="severe",
            type="allergy",
            medication="Amoxicillin",
            description="Patient allergic to penicillin",
            recommendation="Avoid; use alternative",
        )
        
        assert warning.type == "allergy"
        assert "penicillin" in warning.description.lower()


class TestPrescriptionDraft:
    """Tests for PrescriptionDraft dataclass."""

    def test_default_values(self):
        """Test default values."""
        draft = PrescriptionDraft(
            medications=[],
            diagnosis="Hypertension",
            clinical_note_summary="Patient has high BP",
        )
        
        assert draft.confidence == 0.0
        assert draft.basis == ""
        assert draft.warnings == []
        assert draft.patient_allergies_considered == []

    def test_with_warnings(self):
        """Test with warnings."""
        warning = InteractionWarning(
            severity="moderate",
            type="interaction",
            medication="Lisinopril + Potassium",
            description="Potassium increase",
        )
        
        draft = PrescriptionDraft(
            medications=[],
            diagnosis="Hypertension",
            clinical_note_summary="Patient has high BP",
            warnings=[warning],
            patient_allergies_considered=["penicillin"],
        )
        
        assert len(draft.warnings) == 1
        assert draft.patient_allergies_considered == ["penicillin"]


class TestPrescriptionAgentResult:
    """Tests for PrescriptionAgentResult."""

    def test_success_result(self):
        """Test successful result."""
        draft = PrescriptionDraft(
            medications=[],
            diagnosis="Test",
            clinical_note_summary="Test",
        )
        
        result = PrescriptionAgentResult(draft=draft, success=True)
        
        assert result.success is True
        assert result.draft is draft
        assert result.error is None

    def test_failure_result(self):
        """Test failure result."""
        result = PrescriptionAgentResult(
            draft=None,
            success=False,
            error="Something went wrong",
        )
        
        assert result.success is False
        assert result.error == "Something went wrong"
        assert result.draft is None


class TestPrescriptionAgent:
    """Tests for PrescriptionAgent."""

    @pytest_asyncio.fixture
    async def mock_llm_provider(self):
        """Mock LLM provider."""
        provider = AsyncMock()
        provider.generate = AsyncMock(return_value=MagicMock(
            content=json.dumps({
                "medications": [
                    {
                        "name": "Aspirin",
                        "dosage": "81mg",
                        "frequency": "once daily",
                        "duration": "30 days",
                        "route": "oral",
                        "instructions": "Take with food",
                        "quantity": 30,
                        "refills": 1,
                    },
                    {
                        "name": "Metoprolol",
                        "dosage": "50mg",
                        "frequency": "twice daily",
                        "duration": "30 days",
                        "route": "oral",
                        "instructions": "",
                        "quantity": 60,
                        "refills": 1,
                    }
                ],
                "diagnosis": "Hypertension with coronary artery disease",
                "clinical_note_summary": "Patient has hypertension and history of MI, needs antiplatelet and beta-blocker",
                "confidence": 0.9,
                "basis": "Clinical note indicates hypertension and prior MI, supporting aspirin for secondary prevention and metoprolol for rate control",
            })
        ))
        return provider

    @pytest_asyncio.fixture
    async def prescription_agent(self):
        """Create prescription agent (providers will be mocked in each test)."""
        return PrescriptionAgent()

    @pytest.mark.asyncio
    async def test_task_type(self, prescription_agent):
        """Test agent task type."""
        assert prescription_agent.task_type == TaskType.PRESCRIPTION_DRAFT

    @pytest.mark.asyncio
    async def test_execute_success(self, prescription_agent, mock_llm_provider):
        """Test successful execution."""
        clinical_note = {
            "chief_complaint": "Hypertension follow-up",
            "history_present_illness": "Patient with known hypertension and prior MI 2 years ago",
            "physical_examination": "BP 145/90, HR 72",
            "assessment": "Hypertension, coronary artery disease",
            "plan": "Optimize BP control, continue antiplatelet",
            "diagnosis_codes": ["I10", "I25.2"],
        }
        
        payload = {
            "clinical_note": clinical_note,
            "patient_allergies": ["penicillin"],
            "patient_id": "123",
            "doctor_id": "456",
            "appointment_id": "789",
        }
        
        with patch("agents.prescription_agent.get_llm_provider", return_value=mock_llm_provider):
            result = await prescription_agent.execute(payload)
        
        assert result.success is True
        assert result.draft is not None
        assert result.error is None
        
        # Verify draft content
        assert len(result.draft.medications) == 2
        assert result.draft.medications[0].name == "Aspirin"
        assert result.draft.medications[0].dosage == "81mg"
        assert result.draft.medications[1].name == "Metoprolol"
        assert result.draft.diagnosis == "Hypertension with coronary artery disease"
        assert result.draft.confidence == 0.9
        assert "hypertension" in result.draft.basis.lower()
        
        # Verify warnings (penicillin allergy should not trigger for aspirin/metoprolol)
        assert result.draft.patient_allergies_considered == ["penicillin"]

    @pytest.mark.asyncio
    async def test_execute_no_clinical_note(self, prescription_agent):
        """Test execution with missing clinical note."""
        payload = {"patient_allergies": ["penicillin"]}
        
        result = await prescription_agent.execute(payload)
        
        assert result.success is False
        assert "No clinical_note provided" in result.error
        assert result.draft is None

    @pytest.mark.asyncio
    async def test_execute_llm_failure(self, prescription_agent, mock_llm_provider):
        """Test execution when LLM fails."""
        mock_llm_provider.generate = AsyncMock(side_effect=Exception("LLM service unavailable"))
        
        clinical_note = {"assessment": "Hypertension"}
        payload = {"clinical_note": clinical_note}
        
        with patch("agents.prescription_agent.get_llm_provider", return_value=mock_llm_provider):
            result = await prescription_agent.execute(payload)
        
        assert result.success is False
        assert "LLM service unavailable" in result.error

    @pytest.mark.asyncio
    async def test_execute_llm_invalid_json(self, prescription_agent, mock_llm_provider):
        """Test execution when LLM returns invalid JSON."""
        mock_llm_provider.generate = AsyncMock(return_value=MagicMock(
            content="This is not valid JSON at all"
        ))
        
        clinical_note = {"assessment": "Hypertension"}
        payload = {"clinical_note": clinical_note}
        
        with patch("agents.prescription_agent.get_llm_provider", return_value=mock_llm_provider):
            result = await prescription_agent.execute(payload)
        
        # Should still succeed but with fallback parsing
        assert result.success is True
        assert result.draft is not None
        assert result.draft.confidence == 0.3  # Low confidence for fallback
        assert "could not be parsed" in result.draft.basis.lower()
        assert len(result.draft.medications) == 0  # No medications in fallback

    @pytest.mark.asyncio
    async def test_execute_warfarin_aspirin_interaction(self, prescription_agent, mock_llm_provider):
        """Test warfarin-aspirin interaction detection."""
        mock_llm_provider.generate = AsyncMock(return_value=MagicMock(
            content=json.dumps({
                "medications": [
                    {"name": "Warfarin", "dosage": "5mg", "frequency": "once daily", "duration": "30 days"},
                    {"name": "Aspirin", "dosage": "81mg", "frequency": "once daily", "duration": "30 days"},
                ],
                "diagnosis": "Atrial fibrillation with coronary artery disease",
                "clinical_note_summary": "Patient needs anticoagulation and antiplatelet",
                "confidence": 0.85,
                "basis": "Clinical note indicates AF and CAD",
            })
        ))
        
        clinical_note = {"assessment": "Atrial fibrillation, coronary artery disease"}
        payload = {"clinical_note": clinical_note, "patient_allergies": []}
        
        with patch("agents.prescription_agent.get_llm_provider", return_value=mock_llm_provider):
            result = await prescription_agent.execute(payload)
        
        assert result.success is True
        assert len(result.draft.warnings) >= 1
        
        # Check for warfarin-aspirin interaction
        interaction_warnings = [w for w in result.draft.warnings if w.type == "interaction"]
        assert len(interaction_warnings) >= 1
        warfarin_aspirin = [w for w in interaction_warnings if "warfarin" in w.medication.lower() and "aspirin" in w.medication.lower()]
        assert len(warfarin_aspirin) >= 1
        assert warfarin_aspirin[0].severity == "severe"

    @pytest.mark.asyncio
    async def test_execute_penicillin_allergy(self, prescription_agent, mock_llm_provider):
        """Test penicillin allergy detection with amoxicillin."""
        mock_llm_provider.generate = AsyncMock(return_value=MagicMock(
            content=json.dumps({
                "medications": [
                    {"name": "Amoxicillin", "dosage": "500mg", "frequency": "three times daily", "duration": "7 days"},
                ],
                "diagnosis": "Strep throat",
                "clinical_note_summary": "Patient has strep throat",
                "confidence": 0.9,
                "basis": "Clinical note indicates bacterial infection",
            })
        ))
        
        clinical_note = {"assessment": "Strep throat"}
        payload = {"clinical_note": clinical_note, "patient_allergies": ["penicillin"]}
        
        with patch("agents.prescription_agent.get_llm_provider", return_value=mock_llm_provider):
            result = await prescription_agent.execute(payload)
        
        assert result.success is True
        
        # Check for penicillin allergy warning
        allergy_warnings = [w for w in result.draft.warnings if w.type == "allergy"]
        assert len(allergy_warnings) >= 1
        amoxicillin_warning = [w for w in allergy_warnings if "amoxicillin" in w.medication.lower()]
        assert len(amoxicillin_warning) >= 1
        assert amoxicillin_warning[0].severity == "severe"

    @pytest.mark.asyncio
    async def test_execute_aspirin_allergy_nsaid_cross_reactivity(self, prescription_agent, mock_llm_provider):
        """Test aspirin allergy cross-reactivity with ibuprofen."""
        mock_llm_provider.generate = AsyncMock(return_value=MagicMock(
            content=json.dumps({
                "medications": [
                    {"name": "Ibuprofen", "dosage": "400mg", "frequency": "every 6 hours", "duration": "as needed"},
                ],
                "diagnosis": "Musculoskeletal pain",
                "clinical_note_summary": "Patient has back pain",
                "confidence": 0.8,
                "basis": "Clinical note indicates musculoskeletal pain",
            })
        ))
        
        clinical_note = {"assessment": "Low back pain"}
        payload = {"clinical_note": clinical_note, "patient_allergies": ["aspirin"]}
        
        with patch("agents.prescription_agent.get_llm_provider", return_value=mock_llm_provider):
            result = await prescription_agent.execute(payload)
        
        assert result.success is True
        
        # Check for aspirin allergy cross-reactivity with ibuprofen
        allergy_warnings = [w for w in result.draft.warnings if w.type == "allergy"]
        ibuprofen_warning = [w for w in allergy_warnings if "ibuprofen" in w.medication.lower()]
        assert len(ibuprofen_warning) >= 1
        assert ibuprofen_warning[0].severity == "severe"

    @pytest.mark.asyncio
    async def test_execute_custom_provider(self, prescription_agent, mock_llm_provider):
        """Test agent with custom provider name."""
        with patch("agents.prescription_agent.get_llm_provider", return_value=mock_llm_provider) as mock_get_llm:
            agent = PrescriptionAgent(llm_provider_name="custom-llm")
            
            clinical_note = {"assessment": "Hypertension"}
            payload = {"clinical_note": clinical_note}
            
            await agent.execute(payload)
            
            mock_get_llm.assert_called_once_with("custom-llm")


class TestRegisterPrescriptionAgent:
    """Tests for register_prescription_agent function."""

    @pytest.mark.asyncio
    async def test_register_prescription_agent(self):
        """Test registering prescription agent with orchestrator."""
        with patch("orchestrator.get_orchestrator") as mock_get_orch:
            mock_orch = MagicMock()
            mock_get_orch.return_value = mock_orch
            
            agent = register_prescription_agent()
            
            assert isinstance(agent, PrescriptionAgent)
            mock_orch.register_agent.assert_called_once_with(agent)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])