"""Doctor Copilot API Pydantic schemas."""

from typing import Any, Optional
from uuid import UUID
from pydantic import BaseModel, Field


class CopilotAnalysisRequest(BaseModel):
    """Request payload for Copilot analysis and clinical note extraction."""
    transcription: str | None = Field(None, description="Transcribed consultation audio text or clinical dictation")
    patient_id: str | None = Field(None, description="Patient identifier")
    patient_name: str | None = Field(None, description="Patient full name")
    appointment_id: str | None = Field(None, description="Associated appointment identifier")
    vitals: dict[str, Any] | None = Field(default_factory=dict, description="Patient vitals (BP, HR, SpO2, Temp)")
    allergies: list[Any] | None = Field(default_factory=list, description="Known patient allergies")
    chief_complaint: str | None = Field(None, description="Physician's initial chief complaint note")
    language: str = Field("en", description="Spoken/dictated language code")


class AIMetadataResponse(BaseModel):
    """Observability metadata block for provider telemetry."""
    provider: str = Field(..., description="Provider that produced output (nvidia, gemini, manual)")
    model: str = Field(..., description="Model name or architecture used")
    fallback_used: bool = Field(False, description="True if primary NVIDIA NIM failed and Gemini fallback was engaged")
    latency_ms: float = Field(0.0, description="End-to-end LLM processing latency in milliseconds")
    confidence: int = Field(90, ge=0, le=100, description="AI clinical concordance score (0-100)")
    tokens: dict[str, int] | None = Field(None, description="Token consumption metrics")


class CopilotSoapResponse(BaseModel):
    """Structured clinical SOAP note."""
    subjective: dict[str, Any]
    objective: dict[str, Any]
    assessment: dict[str, Any]
    plan: dict[str, Any]


class CopilotDataResponse(BaseModel):
    """Synthesized clinical data payload."""
    soap: dict[str, Any]
    icd10_codes: list[str] = Field(default_factory=list)
    medications: list[dict[str, Any]] = Field(default_factory=list)
    diagnostics_ordered: list[str] = Field(default_factory=list)
    confidence: int = 90


class CopilotAnalysisResponse(BaseModel):
    """Unified response envelope returned by Copilot API."""
    success: bool = True
    status: str = Field("completed", description="Task execution status (completed, fallback_to_human, failed)")
    task_id: str = Field(..., description="Unique orchestrator task execution identifier")
    data: CopilotDataResponse | None = None
    ai_metadata: AIMetadataResponse
    requires_human_fallback: bool = False
    fallback_reason: str | None = None


class ProviderStatusItem(BaseModel):
    """Status details for an individual AI provider."""
    name: str
    type: str
    status: str
    healthy: bool


class AIProviderHealthResponse(BaseModel):
    """Health check and active configuration overview of AI providers."""
    active_llm: str
    active_stt: str
    llm_providers: list[str]
    stt_providers: list[str]
    failover_ready: bool
