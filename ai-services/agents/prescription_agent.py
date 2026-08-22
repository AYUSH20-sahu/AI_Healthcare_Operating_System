"""Prescription Drafting Agent for AI-HOS.

Given a consultation's structured note, produces a draft prescription via the provider adapter,
runs it through the check_interactions function, and attaches any warnings plus a confidence/basis field.
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
    LLMMessage,
)

logger = logging.getLogger(__name__)


@dataclass
class MedicationDraft:
    """Draft medication in a prescription."""
    name: str
    dosage: str
    frequency: str
    duration: str
    route: str = "oral"
    instructions: str = ""
    quantity: Optional[int] = None
    refills: int = 0


@dataclass
class InteractionWarning:
    """Drug interaction or allergy warning."""
    severity: str  # mild, moderate, severe
    type: str  # interaction, allergy
    medication: str
    description: str
    recommendation: Optional[str] = None


@dataclass
class PrescriptionDraft:
    """Structured prescription draft."""
    medications: list[MedicationDraft]
    diagnosis: str
    clinical_note_summary: str
    confidence: float = 0.0
    basis: str = ""
    warnings: list[InteractionWarning] = field(default_factory=list)
    patient_allergies_considered: list[str] = field(default_factory=list)


@dataclass
class PrescriptionAgentResult:
    """Result from the prescription agent."""
    draft: Optional[PrescriptionDraft]
    success: bool = True
    error: Optional[str] = None


class PrescriptionAgent(AgentBase):
    """Prescription drafting agent.
    
    Takes a structured clinical note, produces a draft prescription via LLM provider,
    runs it through drug interaction/allergy checking, and returns a structured draft
    with warnings and confidence/basis fields.
    """
    
    @property
    def task_type(self) -> TaskType:
        return TaskType.PRESCRIPTION_DRAFT
    
    def __init__(
        self,
        llm_provider_name: Optional[str] = None,
    ):
        self._llm_provider_name = llm_provider_name
    
    async def execute(self, payload: dict[str, Any]) -> PrescriptionAgentResult:
        """Execute the prescription drafting agent task.
        
        Expected payload:
        {
            "clinical_note": {  # Required: structured clinical note from scribe agent
                "chief_complaint": "...",
                "history_present_illness": "...",
                "physical_examination": "...",
                "assessment": "...",
                "plan": "...",
                "diagnosis_codes": ["I20.9"],
            },
            "patient_allergies": ["penicillin"],  # Optional: patient's known allergies
            "patient_id": "123",  # Optional: patient context
            "doctor_id": "456",  # Optional: doctor context
            "appointment_id": "789",  # Optional: appointment context
        }
        """
        try:
            # Extract clinical note
            clinical_note = payload.get("clinical_note")
            if not clinical_note:
                return PrescriptionAgentResult(
                    draft=None,
                    success=False,
                    error="No clinical_note provided in payload",
                )
            
            patient_allergies = payload.get("patient_allergies", [])
            
            # Step 1: Generate prescription using LLM provider
            logger.info("Generating prescription via LLM provider...")
            llm_provider = get_llm_provider(self._llm_provider_name)
            
            system_prompt = self._build_system_prompt()
            user_prompt = self._build_user_prompt(clinical_note, patient_allergies, payload)
            
            messages = [
                LLMMessage(role="system", content=system_prompt),
                LLMMessage(role="user", content=user_prompt),
            ]
            
            llm_response = await llm_provider.generate(
                messages=messages,
                temperature=0.2,  # Low temperature for consistent medical output
                max_tokens=2000,
            )
            
            # Step 2: Parse and structure the response
            draft = self._parse_llm_response(llm_response.content, clinical_note)
            
            # Step 3: Run interaction/allergy checking
            logger.info("Checking drug interactions and allergies...")
            draft.warnings = self._check_interactions(draft.medications, patient_allergies)
            draft.patient_allergies_considered = patient_allergies
            
            logger.info(f"Prescription draft generated with {len(draft.warnings)} warnings")
            
            return PrescriptionAgentResult(
                draft=draft,
                success=True,
            )
        
        except Exception as e:
            logger.error(f"Prescription agent failed: {e}")
            return PrescriptionAgentResult(
                draft=None,
                success=False,
                error=str(e),
            )
    
    def _build_system_prompt(self) -> str:
        """Build the system prompt for prescription generation."""
        return """You are an expert clinical pharmacist assisting with prescription drafting. Your task is to convert a structured clinical note into a structured prescription draft.

Follow this exact JSON format for your response:
{
    "medications": [
        {
            "name": "Medication name (generic preferred)",
            "dosage": "Dosage with units (e.g., '10mg', '500mg')",
            "frequency": "Frequency (e.g., 'once daily', 'twice daily', 'every 8 hours')",
            "duration": "Duration (e.g., '7 days', '30 days', 'as needed')",
            "route": "Route of administration (oral, topical, IV, etc.)",
            "instructions": "Special instructions (e.g., 'take with food', 'take at bedtime')",
            "quantity": 30,
            "refills": 0
        }
    ],
    "diagnosis": "Primary diagnosis for this prescription",
    "clinical_note_summary": "Brief summary linking clinical note to prescription rationale",
    "confidence": 0.95,
    "basis": "Explanation of what in the clinical note supports each medication choice"
}

Guidelines:
- Use generic medication names when possible
- Include appropriate dosages for the diagnosed condition
- Consider standard treatment guidelines
- Include quantity and refills appropriate for the condition
- Confidence should reflect how well the clinical note supports the prescription (0.0-1.0)
- Basis should explain which parts of the clinical note led to each medication
- If information is insufficient, note it and set lower confidence
- Be concise but complete
- Maximum 5 medications per prescription"""
    
    def _build_user_prompt(
        self,
        clinical_note: dict[str, Any],
        patient_allergies: list[str],
        payload: dict[str, Any]
    ) -> str:
        """Build the user prompt with clinical note and context."""
        context_parts = []
        
        if payload.get("patient_id"):
            context_parts.append(f"Patient ID: {payload['patient_id']}")
        if payload.get("doctor_id"):
            context_parts.append(f"Doctor ID: {payload['doctor_id']}")
        if payload.get("appointment_id"):
            context_parts.append(f"Appointment ID: {payload['appointment_id']}")
        if patient_allergies:
            context_parts.append(f"Patient Allergies: {', '.join(patient_allergies)}")
        
        context = "\n".join(context_parts) if context_parts else "No additional context provided."
        
        note_parts = []
        for key, value in clinical_note.items():
            if value:
                note_parts.append(f"{key.replace('_', ' ').title()}: {value}")
        
        note_text = "\n".join(note_parts) if note_parts else "No clinical note provided."
        
        return f"""Context:
{context}

Clinical Note:
{note_text}

Please generate a structured prescription draft in the specified JSON format."""
    
    def _parse_llm_response(self, response_text: str, clinical_note: dict[str, Any]) -> PrescriptionDraft:
        """Parse LLM response into structured prescription draft."""
        try:
            # Try to parse as JSON
            data = json.loads(response_text)
            
            medications = []
            for med_data in data.get("medications", []):
                medications.append(MedicationDraft(
                    name=med_data.get("name", "Unknown"),
                    dosage=med_data.get("dosage", "As directed"),
                    frequency=med_data.get("frequency", "As directed"),
                    duration=med_data.get("duration", "As directed"),
                    route=med_data.get("route", "oral"),
                    instructions=med_data.get("instructions", ""),
                    quantity=med_data.get("quantity"),
                    refills=med_data.get("refills", 0),
                ))
            
            return PrescriptionDraft(
                medications=medications,
                diagnosis=data.get("diagnosis", clinical_note.get("assessment", "Not specified")),
                clinical_note_summary=data.get("clinical_note_summary", "Generated from clinical note"),
                confidence=float(data.get("confidence", 0.5)),
                basis=data.get("basis", "Generated from clinical note"),
            )
        except json.JSONDecodeError:
            # Fallback: create a basic draft from the raw response
            logger.warning("LLM response was not valid JSON, creating fallback prescription")
            return PrescriptionDraft(
                medications=[],
                diagnosis=clinical_note.get("assessment", "Not specified"),
                clinical_note_summary="LLM response could not be parsed as structured JSON",
                confidence=0.3,
                basis="LLM response could not be parsed as structured JSON",
            )
    
    def _check_interactions(
        self,
        medications: list[MedicationDraft],
        patient_allergies: list[str]
    ) -> list[InteractionWarning]:
        """Check drug interactions and allergies using static tables.
        
        This mirrors the backend's check_interactions function.
        """
        warnings = []
        med_names = [med.name.lower().strip() for med in medications]
        
        # Static known drug interactions table (mirrors backend)
        KNOWN_INTERACTIONS = {
            ("warfarin", "aspirin"): {
                "severity": "severe",
                "description": "Increased risk of bleeding when warfarin is combined with aspirin",
                "recommendation": "Monitor INR closely; consider alternative analgesic"
            },
            ("warfarin", "ibuprofen"): {
                "severity": "severe",
                "description": "NSAIDs increase bleeding risk with warfarin",
                "recommendation": "Avoid combination; use acetaminophen instead"
            },
            ("lisinopril", "potassium"): {
                "severity": "moderate",
                "description": "ACE inhibitors can increase potassium levels",
                "recommendation": "Monitor serum potassium; adjust supplementation"
            },
            ("metformin", "contrast"): {
                "severity": "severe",
                "description": "Risk of lactic acidosis with IV contrast",
                "recommendation": "Hold metformin 48h before and after contrast administration"
            },
            ("simvastatin", "clarithromycin"): {
                "severity": "severe",
                "description": "Strong CYP3A4 inhibition increases statin levels",
                "recommendation": "Use alternative antibiotic or hold statin during therapy"
            },
            ("digoxin", "furosemide"): {
                "severity": "moderate",
                "description": "Loop diuretics can cause hypokalemia increasing digoxin toxicity",
                "recommendation": "Monitor potassium and digoxin levels"
            },
            ("methotrexate", "nsaids"): {
                "severity": "severe",
                "description": "NSAIDs reduce methotrexate clearance",
                "recommendation": "Avoid concurrent use; monitor for toxicity"
            },
        }
        
        # Static known allergies (mirrors backend)
        KNOWN_ALLERGIES = {
            "penicillin": ["amoxicillin", "ampicillin", "piperacillin", "ticarcillin"],
            "sulfa": ["sulfamethoxazole", "sulfasalazine", "sulfadiazine"],
            "aspirin": ["aspirin", "ibuprofen", "naproxen", "celecoxib"],
            "latex": [],
        }
        
        # Check drug-drug interactions
        for i, med1 in enumerate(med_names):
            for med2 in med_names[i+1:]:
                for pair in [(med1, med2), (med2, med1)]:
                    if pair in KNOWN_INTERACTIONS:
                        interaction = KNOWN_INTERACTIONS[pair]
                        warnings.append(InteractionWarning(
                            severity=interaction["severity"],
                            type="interaction",
                            medication=f"{pair[0].title()} + {pair[1].title()}",
                            description=interaction["description"],
                            recommendation=interaction.get("recommendation")
                        ))
        
        # Check drug-allergy interactions
        for allergy in patient_allergies:
            allergy_lower = allergy.lower().strip()
            if allergy_lower in KNOWN_ALLERGIES:
                cross_reactive = KNOWN_ALLERGIES[allergy_lower]
                for med in med_names:
                    if med in cross_reactive:
                        warnings.append(InteractionWarning(
                            severity="severe",
                            type="allergy",
                            medication=med.title(),
                            description=f"Patient has known allergy to {allergy}; {med.title()} may cause cross-reaction",
                            recommendation=f"Avoid {med.title()}; use alternative medication class"
                        ))
            # Also check if the medication name matches the allergy directly
            for med in med_names:
                if med == allergy_lower:
                    warnings.append(InteractionWarning(
                        severity="severe",
                        type="allergy",
                        medication=med.title(),
                        description=f"Patient has known allergy to {allergy}; {med.title()} is contraindicated",
                        recommendation=f"Avoid {med.title()}; use alternative medication class"
                    ))
        
        return warnings


# Register the agent with the global orchestrator
def register_prescription_agent(
    llm_provider_name: Optional[str] = None,
) -> PrescriptionAgent:
    """Create and register the prescription agent with the global orchestrator."""
    from orchestrator import get_orchestrator
    
    agent = PrescriptionAgent(
        llm_provider_name=llm_provider_name,
    )
    get_orchestrator().register_agent(agent)
    return agent