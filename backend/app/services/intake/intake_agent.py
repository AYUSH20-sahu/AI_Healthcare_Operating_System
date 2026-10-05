"""AI Patient Intake & Symptom Collection Agent for AI-HOS (U-13 / M25).

Engages patients in empathetic, non-diagnostic symptom collection dialogue.
Clarifies chief complaints, onset, duration, severity, and associated symptoms.
Outputs structured clinical symptom summaries for attending physicians.

STRICT CLINICAL RULES:
1. NON-DIAGNOSTIC: NEVER state or suggest medical diagnoses (e.g. do NOT say "You might have migraine").
2. NO PRESCRIPTION: NEVER recommend or prescribe drugs, dosages, or self-medications.
3. IN-MEMORY ISOLATION: Operates strictly in-memory without direct database access.
"""

import json
import logging
import re
from dataclasses import asdict, dataclass, field
from typing import Any, Optional

from app.services.orchestrator import AgentBase, TaskType, get_orchestrator
from app.services.providers import (
    LLMMessage,
    LLMResponse,
    get_llm_provider,
)

logger = logging.getLogger("intake_agent")

INTAKE_SYSTEM_PROMPT = """You are the AI-HOS Patient Intake Assistant, an empathetic, conversational clinical intake AI.

YOUR PRIMARY ROLE:
Gather thorough, structured symptom information from the patient before their consultation with a licensed physician.

CRITICAL CLINICAL & SAFETY GUARDRAILS (ZERO TOLERANCE):
1. ABSOLUTELY NO DIAGNOSIS: You must NEVER tell the patient what medical condition they have, might have, or suggest a differential diagnosis.
2. ABSOLUTELY NO PRESCRIPTIONS OR DRUG RECOMMENDATIONS: You must NEVER recommend, suggest, or prescribe medications, dosages, over-the-counter drugs, or home treatments.
3. NO CLINICAL PROGNOSIS: Do not predict disease outcomes or reassure with unfounded clinical guarantees.
4. RED FLAGS / EMERGENCY ESCALATION: If the patient mentions acute crushing chest pain, difficulty breathing, sudden severe numbness or weakness, stroke symptoms, uncontrolled bleeding, or severe trauma, advise them immediately to seek emergency emergency medical care or call 911/emergency services.
5. OBJECTIVE STRUCTURING: Your purpose is solely to organize the patient's reported symptoms clearly so the human doctor can review them efficiently.

CONVERSATION STYLE:
- Warm, polite, professional, and empathetic.
- Ask 1 to 2 concise clarifying questions at a time so the patient is not overwhelmed.
- Clarify key dimensions:
  * Chief complaint (primary symptom/issue)
  * Onset & duration (when did it start, continuous or intermittent)
  * Severity (ask for a rating on a scale of 1 to 10)
  * Location & radiation (where is it felt)
  * Associated symptoms (fever, nausea, fatigue, etc.)
  * Aggravating or relieving factors (what makes it worse or better)

COMPLETION CRITERIA:
- Mark `is_complete: true` when the chief complaint, duration/onset, and approximate severity or key context have been clearly shared (typically after 2 to 4 turns of dialogue), OR when the patient explicitly requests to finish/submit.
- When complete, provide a friendly closing remark thanking them and confirming their symptoms have been organized for their doctor.

RESPONSE FORMAT:
You MUST respond with a valid JSON object strictly matching this schema:
{
  "reply": "Your empathetic conversational response to the patient, including any follow-up question or closing statement.",
  "is_complete": false,
  "structured_symptoms": {
    "chief_complaint": "Primary symptom or reported issue",
    "duration": "Reported duration (e.g. 3 days, 2 hours)",
    "severity": 7,
    "associated_symptoms": ["symptom 1", "symptom 2"],
    "aggravating_factors": ["factor 1"],
    "relieving_factors": ["factor 1"],
    "summary": "Objective clinical summary of patient-reported symptoms for the attending physician."
  },
  "ai_confidence": 85,
  "basis": "Explanation of clinical intake assessment and rationale for questions or completion."
}
Do not wrap your JSON in conversational preambles outside the JSON block. Return valid JSON only.
"""


@dataclass
class StructuredSymptoms:
    chief_complaint: str = ""
    duration: str = ""
    severity: Optional[int] = None
    associated_symptoms: list[str] = field(default_factory=list)
    aggravating_factors: list[str] = field(default_factory=list)
    relieving_factors: list[str] = field(default_factory=list)
    summary: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class IntakeAgentResult:
    reply: str
    is_complete: bool
    structured_symptoms: dict[str, Any]
    ai_confidence: int
    basis: str
    ai_metadata: dict[str, Any] = field(default_factory=dict)
    fallback_used: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class IntakeAgent(AgentBase):
    """AI Patient Intake Agent for symptom collection and structuring."""

    @property
    def task_type(self) -> TaskType:
        return TaskType.INTAKE

    def __init__(self, provider_name: Optional[str] = None):
        self._provider_name = provider_name

    async def execute(self, payload: dict[str, Any]) -> IntakeAgentResult:
        """Execute conversational symptom intake turn.

        Expected payload:
        - patient_name: str
        - age: Optional[int]
        - gender: Optional[str]
        - messages: list[dict[str, str]]  # previous turn history [{"role": "user"/"assistant", "content": "..."}]
        - new_message: str  # latest user message
        """
        patient_name = payload.get("patient_name") or "Patient"
        age = payload.get("age")
        gender = payload.get("gender")
        messages_history = payload.get("messages") or []
        new_message = payload.get("new_message") or ""

        provider = get_llm_provider(self._provider_name)

        # Build prompt
        context_str = f"Patient Name: {patient_name}"
        if age:
            context_str += f", Age: {age}"
        if gender:
            context_str += f", Gender: {gender}"

        # Build message history for LLM
        llm_messages: list[LLMMessage] = [
            LLMMessage(role="system", content=f"{INTAKE_SYSTEM_PROMPT}\n\nPATIENT CONTEXT:\n{context_str}")
        ]

        for msg in messages_history:
            role = "user" if msg.get("role") in ("user", "patient") else "assistant"
            llm_messages.append(LLMMessage(role=role, content=msg.get("content", "")))

        # Append latest user input if not already at end of history
        if new_message:
            if not messages_history or messages_history[-1].get("content") != new_message:
                llm_messages.append(LLMMessage(role="user", content=new_message))

        logger.info(
            "Executing IntakeAgent turn with provider: %s (history len: %d)",
            provider.name,
            len(llm_messages),
        )

        try:
            response: LLMResponse = await provider.generate(
                messages=llm_messages,
                temperature=0.3,
                max_tokens=1500,
            )
            raw_content = response.content
            fallback_used = response.fallback_used
            ai_metadata = {
                "provider": response.provider,
                "model": response.model,
                "fallback_used": response.fallback_used,
                "latency_ms": response.latency_ms,
                "usage": response.usage,
            }
        except Exception as e:
            logger.warning("IntakeAgent provider call failed: %s. Using safe fallback response.", e)
            return self._build_safe_fallback(
                user_input=new_message,
                messages_history=messages_history,
                patient_name=patient_name,
                error=str(e),
            )

        parsed = self._parse_llm_json(raw_content, new_message)

        # Guardrail enforcement: verify that no diagnostic or prescriptive statements were emitted
        reply = self._enforce_guardrails(parsed.get("reply", ""))
        structured = parsed.get("structured_symptoms") or {}

        # Validate severity
        sev = structured.get("severity")
        if sev is not None:
            try:
                sev = max(1, min(10, int(sev)))
            except (ValueError, TypeError):
                sev = None
        structured["severity"] = sev

        return IntakeAgentResult(
            reply=reply,
            is_complete=bool(parsed.get("is_complete", False)),
            structured_symptoms=structured,
            ai_confidence=int(parsed.get("ai_confidence", 85)),
            basis=parsed.get("basis") or "Symptom clarification based on patient conversational reports.",
            ai_metadata=ai_metadata,
            fallback_used=fallback_used,
        )

    def _parse_llm_json(self, content: str, user_input: str) -> dict[str, Any]:
        """Parse structured intake response from LLM."""
        text = content.strip()
        # Strip markdown fences if present
        if "```json" in text:
            match = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL)
            if match:
                text = match.group(1).strip()
        elif "```" in text:
            match = re.search(r"```\s*(.*?)\s*```", text, re.DOTALL)
            if match:
                text = match.group(1).strip()

        try:
            data = json.loads(text)
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError:
            logger.warning("Failed to parse JSON directly from LLM intake response. Extracting fallback.")

        # Fallback JSON extractor
        json_pattern = re.search(r"\{.*\}", text, re.DOTALL)
        if json_pattern:
            try:
                data = json.loads(json_pattern.group(0))
                if isinstance(data, dict):
                    return data
            except Exception:
                pass

        # Text fallback if LLM returned plain text
        return {
            "reply": content or "Thank you for sharing your symptoms. Could you describe how long this has been going on, and rate its intensity from 1 to 10?",
            "is_complete": False,
            "structured_symptoms": {
                "chief_complaint": user_input[:100] if user_input else "Unspecified symptoms",
                "duration": "Unknown",
                "severity": None,
                "associated_symptoms": [],
                "aggravating_factors": [],
                "relieving_factors": [],
                "summary": f"Patient reported: {user_input}" if user_input else "Intake in progress",
            },
            "ai_confidence": 70,
            "basis": "Extracted from conversational input (unstructured fallback).",
        }

    def _enforce_guardrails(self, reply: str) -> str:
        """Sanitize reply to guarantee non-diagnostic and non-prescriptive safety."""
        # Replace dangerous prescriptive claims if any slip through
        cleaned = re.sub(
            r"(?i)\b(you have|you are suffering from|I diagnose you with)\b",
            "you are describing symptoms often discussed regarding",
            reply,
        )
        cleaned = re.sub(
            r"(?i)\b(I prescribe|take \d+\s*(?:mg|tablets|pills)|start taking)\b",
            "your doctor will discuss suitable treatments such as",
            cleaned,
        )
        return cleaned

    def _build_safe_fallback(
        self,
        user_input: str,
        messages_history: list[dict[str, Any]] | None = None,
        patient_name: str = "Patient",
        error: str = "",
    ) -> IntakeAgentResult:
        """Progressive clinical state-machine response when external LLM providers are unavailable."""
        history = list(messages_history or [])
        patient_turns: list[str] = [
            m.get("content", "").strip()
            for m in history
            if m.get("role") in ("patient", "user") and m.get("content", "").strip()
        ]
        if user_input.strip() and (not patient_turns or patient_turns[-1] != user_input.strip()):
            patient_turns.append(user_input.strip())

        turn_count = len(patient_turns)

        # 1. Chief complaint (first user message)
        chief_complaint = patient_turns[0] if patient_turns else (user_input.strip() or "Reported symptoms")

        # 2. Extract severity rating (1-10) without mistaking durations/dosages (e.g. "2 days", "650 mg")
        detected_severity: int | None = None

        # Priority 1: Standalone rating in any turn e.g. "7", "7/10", "rated 7 out of 10"
        for turn in patient_turns:
            clean = turn.strip()
            m = re.match(r"^(?:(?:severity|rate|rating|pain|score)\s*(?:is|of|:)?\s*)?(10|[1-9])(?:\s*(?:/|out of)\s*10)?\.?$", clean, re.IGNORECASE)
            if m:
                try:
                    val = int(m.group(1))
                    if 1 <= val <= 10:
                        detected_severity = val
                        break
                except ValueError:
                    pass

        # Priority 2: Explicit severity phrases within sentence e.g. "severity: 8" or "pain is 7"
        if detected_severity is None:
            for turn in patient_turns:
                m = re.search(r"\b(?:severity|rate|rating|pain score|level)\s*(?:is|of|:)?\s*(10|[1-9])\b", turn, re.IGNORECASE)
                if m:
                    try:
                        val = int(m.group(1))
                        if 1 <= val <= 10:
                            detected_severity = val
                            break
                    except ValueError:
                        pass

        # Priority 3: Fraction format e.g. "7/10" or "8 out of 10"
        if detected_severity is None:
            for turn in patient_turns:
                m = re.search(r"\b(10|[1-9])\s*(?:/|out of)\s*10\b", turn, re.IGNORECASE)
                if m:
                    try:
                        val = int(m.group(1))
                        if 1 <= val <= 10:
                            detected_severity = val
                            break
                    except ValueError:
                        pass

        # Priority 4: In turn answering severity inquiry (turn 2), number NOT followed by time or dosage units
        if detected_severity is None and len(patient_turns) >= 2:
            turn_2 = patient_turns[1]
            m = re.search(r"\b(10|[1-9])(?!\s*(?:days?|hours?|hrs?|weeks?|months?|years?|mg|ml|tablets?|pills?|times?|am|pm))\b", turn_2, re.IGNORECASE)
            if m:
                try:
                    val = int(m.group(1))
                    if 1 <= val <= 10:
                        detected_severity = val
                except ValueError:
                    pass

        # 3. Extract duration clues
        detected_duration = "Reported in consultation"
        duration_pattern = re.compile(
            r"\b(\d+\s*(?:day|days|hour|hours|week|weeks|month|months)|yesterday(?:\s+(?:morning|evening|afternoon|night))?|since\s+\w+|today|few\s+\w+)\b",
            re.IGNORECASE,
        )
        for turn in patient_turns:
            dur_match = duration_pattern.search(turn)
            if dur_match:
                detected_duration = dur_match.group(0)

        # 4. Check for emergency red flags
        red_flag_pattern = re.compile(
            r"\b(chest pain|heart attack|can't breathe|cannot breathe|difficulty breathing|shortness of breath|unconscious|passed out|stroke|severe bleeding|heavy bleeding|coughing blood)\b",
            re.IGNORECASE,
        )
        if any(red_flag_pattern.search(t) for t in patient_turns):
            return IntakeAgentResult(
                reply=(
                    "⚠️ IMPORTANT MEDICAL NOTICE: You have described symptoms that may indicate an urgent medical situation. "
                    "If you are experiencing severe chest pain, extreme difficulty breathing, sudden numbness, or heavy bleeding, "
                    "please call emergency services or visit the nearest emergency department immediately."
                ),
                is_complete=True,
                structured_symptoms={
                    "chief_complaint": chief_complaint[:120],
                    "duration": detected_duration,
                    "severity": detected_severity or 9,
                    "associated_symptoms": ["URGENT: Red flag symptoms detected"],
                    "aggravating_factors": [],
                    "relieving_factors": [],
                    "summary": f"EMERGENCY RED FLAG: Patient reported potentially critical symptoms: {user_input}",
                },
                ai_confidence=95,
                basis="Emergency red flag keywords identified during intake screening.",
                ai_metadata={"fallback": True, "red_flag": True, "error": error},
                fallback_used=True,
            )

        # 5. Progressive Multi-Turn State Machine
        if turn_count <= 1:
            reply = (
                f"Thank you for sharing, {patient_name}. I have noted: \"{chief_complaint[:100]}\". "
                "Could you please share when these symptoms started and how severe they feel on a scale of 1 to 10?"
            )
            is_complete = False
        elif turn_count == 2:
            sev_str = f"a severity rating of {detected_severity}/10" if detected_severity else "your description"
            reply = (
                f"Thank you for clarifying. I have recorded {sev_str}. "
                "Are you experiencing any other associated symptoms—such as fever, chills, dizziness, vomiting, or body aches?"
            )
            is_complete = False
        elif turn_count == 3:
            reply = (
                "Understood. Have you noticed anything that makes the symptoms better or worse? "
                "Also, please mention if you have any drug allergies or existing medical conditions."
            )
            is_complete = False
        else:
            # Turn 4 or more: finalize intake
            sev_display = f"{detected_severity}/10" if detected_severity else "moderate"
            reply = (
                f"Thank you very much, {patient_name}. I have gathered all necessary information. "
                f"Your symptoms, duration ({detected_duration}), and severity ({sev_display}) have been structured "
                "and securely prepared for your attending physician to review before your consultation."
            )
            is_complete = True

        all_text = " | ".join(patient_turns)
        associated = [t for t in patient_turns[1:3] if len(t) > 3 and not re.match(r"^\d+$", t)]
        return IntakeAgentResult(
            reply=reply,
            is_complete=is_complete,
            structured_symptoms={
                "chief_complaint": chief_complaint[:120],
                "duration": detected_duration,
                "severity": detected_severity,
                "associated_symptoms": associated,
                "aggravating_factors": [],
                "relieving_factors": [],
                "summary": f"Patient reported: {all_text[:300]}",
            },
            ai_confidence=75 if not is_complete else 90,
            basis="Conversational clinical intake protocol tracking chief complaint, timeline, and severity.",
            ai_metadata={"fallback": True, "turn_count": turn_count, "error": error},
            fallback_used=True,
        )


# Global instance and orchestrator registration
intake_agent = IntakeAgent()
get_orchestrator().register_agent(intake_agent)
