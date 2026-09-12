"""AI Patient Intake API Schemas for AI-HOS (Milestone U-13)."""

from datetime import datetime
from typing import Any, Optional
from uuid import UUID
from pydantic import BaseModel, Field, model_validator


class StructuredSymptomsData(BaseModel):
    """Normalized clinical symptom data collected during intake."""
    chief_complaint: Optional[str] = Field(None, description="Primary symptom or complaint reported")
    duration: Optional[str] = Field(None, description="Onset and duration of symptoms")
    severity: Optional[int] = Field(None, ge=1, le=10, description="Reported pain/intensity severity from 1 to 10")
    associated_symptoms: list[str] = Field(default_factory=list, description="Secondary or co-occurring symptoms")
    aggravating_factors: list[str] = Field(default_factory=list, description="Triggers or factors worsening symptoms")
    relieving_factors: list[str] = Field(default_factory=list, description="Factors alleviating symptoms")
    summary: Optional[str] = Field(None, description="Objective clinical summary for the attending physician")


class IntakeMessage(BaseModel):
    """Individual conversational dialogue turn."""
    role: str = Field(..., description="Speaker role: 'patient', 'user', or 'assistant'")
    content: str = Field(..., description="Message text content")
    timestamp: str = Field(..., description="ISO 8601 string timestamp")


class IntakeSessionCreateRequest(BaseModel):
    """Optional initial payload when initiating intake."""
    initial_message: Optional[str] = Field(None, max_length=2000, description="Optional opening symptom statement")


class IntakeMessageRequest(BaseModel):
    """Payload sent by the patient during an ongoing intake session."""
    content: str = Field(..., min_length=1, max_length=2000, description="Patient's message or symptom response")


class IntakeMessageResponse(BaseModel):
    """Response returned after processing a patient intake turn."""
    session_id: UUID
    reply: str
    is_complete: bool
    structured_symptoms: StructuredSymptomsData
    ai_confidence: int
    basis: Optional[str] = None
    status: str


class IntakeSessionResponse(BaseModel):
    """Full representation of an IntakeSession."""
    session_id: UUID
    id: Optional[UUID] = None
    patient_id: UUID
    status: str
    messages: list[dict[str, Any]] = Field(default_factory=list)
    structured_symptoms: Optional[dict[str, Any]] = None
    ai_confidence: Optional[float] = None
    basis: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None

    @model_validator(mode="after")
    def sync_id(self):
        if self.id is None:
            self.id = self.session_id
        return self

    class Config:
        from_attributes = True


class IntakeCompleteRequest(BaseModel):
    """Optional manual completion note or override."""
    notes: Optional[str] = Field(None, max_length=1000)
