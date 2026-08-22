"""Doctor Copilot Scribe Agent for AI-HOS.

Takes voice notes, transcribes them, and produces structured clinical note drafts.
"""

from dataclasses import dataclass, field
from typing import Any, Optional
import json
import logging
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from orchestrator import AgentBase, TaskType
from providers import (
    get_llm_provider,
    get_stt_provider,
    LLMMessage,
    TranscriptionResult,
)

logger = logging.getLogger(__name__)


@dataclass
class ClinicalNoteDraft:
    """Structured clinical note draft."""
    chief_complaint: str
    history_present_illness: str
    physical_examination: str
    assessment: str
    plan: str
    diagnosis_codes: list[str] = field(default_factory=list)
    confidence: float = 0.0
    basis: str = ""
    raw_transcription: str = ""


@dataclass
class ScribeAgentResult:
    """Result from the scribe agent."""
    draft: ClinicalNoteDraft
    transcription: TranscriptionResult
    success: bool = True
    error: Optional[str] = None


class ScribeAgent(AgentBase):
    """Doctor Copilot ambient scribe agent.
    
    Takes a voice note, transcribes it via STT provider, and produces
    a structured clinical note draft via LLM provider.
    """
    
    @property
    def task_type(self) -> TaskType:
        return TaskType.SCRIBE
    
    def __init__(
        self,
        llm_provider_name: Optional[str] = None,
        stt_provider_name: Optional[str] = None,
    ):
        self._llm_provider_name = llm_provider_name
        self._stt_provider_name = stt_provider_name
    
    async def execute(self, payload: dict[str, Any]) -> ScribeAgentResult:
        """Execute the scribe agent task.
        
        Expected payload:
        {
            "audio_data": bytes,  # Required: audio file data
            "audio_format": "webm",  # Optional: audio format (default: webm)
            "language": "en",  # Optional: language code (default: en)
            "patient_id": "123",  # Optional: patient context
            "doctor_id": "456",  # Optional: doctor context
            "appointment_id": "789",  # Optional: appointment context
        }
        """
        try:
            # Extract audio data
            audio_data = payload.get("audio_data")
            if not audio_data:
                return ScribeAgentResult(
                    draft=None,
                    transcription=None,
                    success=False,
                    error="No audio_data provided in payload",
                )
            
            audio_format = payload.get("audio_format", "webm")
            language = payload.get("language", "en")
            
            # Step 1: Transcribe audio using STT provider
            logger.info("Transcribing audio via STT provider...")
            stt_provider = get_stt_provider(self._stt_provider_name)
            transcription = await stt_provider.transcribe(
                audio_data=audio_data,
                format=audio_format,
                language=language,
            )
            logger.info(f"Transcription completed: {transcription.text[:100]}...")
            
            # Step 2: Generate clinical note using LLM provider
            logger.info("Generating clinical note via LLM provider...")
            llm_provider = get_llm_provider(self._llm_provider_name)
            
            system_prompt = self._build_system_prompt()
            user_prompt = self._build_user_prompt(transcription.text, payload)
            
            messages = [
                LLMMessage(role="system", content=system_prompt),
                LLMMessage(role="user", content=user_prompt),
            ]
            
            llm_response = await llm_provider.generate(
                messages=messages,
                temperature=0.3,  # Lower temperature for more consistent medical output
                max_tokens=2000,
            )
            
            # Step 3: Parse and structure the response
            draft = self._parse_llm_response(llm_response.content, transcription.text)
            
            logger.info("Clinical note draft generated successfully")
            
            return ScribeAgentResult(
                draft=draft,
                transcription=transcription,
                success=True,
            )
        
        except Exception as e:
            logger.error(f"Scribe agent failed: {e}")
            return ScribeAgentResult(
                draft=None,
                transcription=None,
                success=False,
                error=str(e),
            )
    
    def _build_system_prompt(self) -> str:
        """Build the system prompt for clinical note generation."""
        return """You are an expert medical scribe. Your task is to convert a physician's dictated or transcribed voice note into a structured clinical note.

Follow this exact JSON format for your response:
{
    "chief_complaint": "Brief primary reason for visit",
    "history_present_illness": "Detailed narrative of the present illness",
    "physical_examination": "Relevant physical exam findings",
    "assessment": "Clinical assessment/differential diagnosis",
    "plan": "Treatment plan, follow-up, referrals",
    "diagnosis_codes": ["ICD-10 codes"],
    "confidence": 0.95,
    "basis": "Explanation of what in the transcription supports this note"
}

Guidelines:
- Extract only information present in the transcription
- Use standard medical terminology
- Include relevant ICD-10 codes when clear from context
- Confidence should reflect how well the transcription supports the note (0.0-1.0)
- Basis should explain which parts of the transcription led to each section
- If information is missing, note it in the relevant section
- Be concise but complete"""
    
    def _build_user_prompt(self, transcription_text: str, payload: dict[str, Any]) -> str:
        """Build the user prompt with transcription and context."""
        context_parts = []
        
        if payload.get("patient_id"):
            context_parts.append(f"Patient ID: {payload['patient_id']}")
        if payload.get("doctor_id"):
            context_parts.append(f"Doctor ID: {payload['doctor_id']}")
        if payload.get("appointment_id"):
            context_parts.append(f"Appointment ID: {payload['appointment_id']}")
        
        context = "\n".join(context_parts) if context_parts else "No additional context provided."
        
        return f"""Context:
{context}

Transcription:
{transcription_text}

Please generate a structured clinical note in the specified JSON format."""
    
    def _parse_llm_response(self, response_text: str, raw_transcription: str) -> ClinicalNoteDraft:
        """Parse LLM response into structured clinical note."""
        try:
            # Try to parse as JSON
            data = json.loads(response_text)
            
            return ClinicalNoteDraft(
                chief_complaint=data.get("chief_complaint", "Not specified"),
                history_present_illness=data.get("history_present_illness", "Not documented"),
                physical_examination=data.get("physical_examination", "Not documented"),
                assessment=data.get("assessment", "Not documented"),
                plan=data.get("plan", "Not documented"),
                diagnosis_codes=data.get("diagnosis_codes", []),
                confidence=float(data.get("confidence", 0.5)),
                basis=data.get("basis", "Generated from transcription"),
                raw_transcription=raw_transcription,
            )
        except json.JSONDecodeError:
            # Fallback: create a basic note from the raw response
            logger.warning("LLM response was not valid JSON, creating fallback note")
            return ClinicalNoteDraft(
                chief_complaint="See transcription",
                history_present_illness=response_text[:500],
                physical_examination="Not documented",
                assessment="Requires physician review",
                plan="Requires physician review",
                diagnosis_codes=[],
                confidence=0.3,
                basis="LLM response could not be parsed as structured JSON",
                raw_transcription=raw_transcription,
            )


# Register the agent with the global orchestrator
def register_scribe_agent(
    llm_provider_name: Optional[str] = None,
    stt_provider_name: Optional[str] = None,
) -> ScribeAgent:
    """Create and register the scribe agent with the global orchestrator."""
    from orchestrator import get_orchestrator
    
    agent = ScribeAgent(
        llm_provider_name=llm_provider_name,
        stt_provider_name=stt_provider_name,
    )
    get_orchestrator().register_agent(agent)
    return agent