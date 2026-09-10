"""Ambient Scribe API Pydantic schemas."""

from datetime import datetime
from typing import Any, Optional
from uuid import UUID
from pydantic import BaseModel, Field


class ScribeProcessRequest(BaseModel):
    """Payload to trigger ambient scribe processing for a voice note."""
    patient_id: UUID | None = Field(None, description="Patient UUID")
    appointment_id: UUID | None = Field(None, description="Appointment UUID")
    patient_name: str | None = Field(None, description="Patient full name")
    vitals: dict[str, Any] | None = Field(default_factory=dict, description="Observed vital signs")
    allergies: list[Any] | None = Field(default_factory=list, description="Documented drug allergies")
    chief_complaint: str | None = Field(None, description="Clinician preliminary complaint note")


class ScribeDraftResponse(BaseModel):
    """Response returned when Scribe pipeline creates a draft medical record."""
    success: bool = True
    medical_record_id: UUID = Field(..., description="Created MedicalRecord UUID in PostgreSQL")
    appointment_id: UUID = Field(..., description="Linked Appointment UUID")
    patient_id: UUID = Field(..., description="Linked Patient UUID")
    doctor_id: UUID = Field(..., description="Linked Doctor UUID")
    status: str = Field("draft", description="Record status (strictly 'draft' until physician review)")
    soap_note: dict[str, Any] = Field(..., description="Structured clinical SOAP note sections")
    confidence: int = Field(..., ge=0, le=100, description="AI confidence score")
    basis: str = Field(..., description="Clinical basis explaining evidence from dialogue")
    transcription: str = Field(..., description="Full consultation audio transcription")
    ai_metadata: dict[str, Any] = Field(default_factory=dict, description="Provider telemetry and execution metadata")
    created_at: datetime = Field(..., description="Timestamp of draft record creation")
