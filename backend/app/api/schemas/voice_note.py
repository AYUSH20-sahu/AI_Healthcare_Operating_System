"""Voice Note Pydantic schemas."""

from typing import Optional
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class VoiceNoteBase(BaseModel):
    """Base voice note schema."""
    appointment_id: UUID = Field(..., description="Appointment ID")
    file_name: str = Field(..., min_length=1, max_length=255, description="Original file name")
    content_type: str = Field(..., max_length=100, description="MIME type (e.g., audio/webm)")
    file_size: int = Field(..., ge=1, description="File size in bytes")
    duration_seconds: Optional[int] = Field(None, ge=0, description="Audio duration in seconds")


class VoiceNoteCreate(VoiceNoteBase):
    """Schema for creating a voice note."""
    pass


class VoiceNoteUpdate(BaseModel):
    """Schema for updating a voice note."""
    transcription: Optional[str] = Field(None, description="Transcribed text")
    transcription_status: Optional[str] = Field(None, pattern="^(pending|processing|completed|failed)$", description="Transcription status")


class VoiceNoteResponse(VoiceNoteBase):
    """Schema for voice note response."""
    voice_note_id: UUID
    doctor_id: UUID
    patient_id: UUID
    file_path: str
    transcription: Optional[str] = None
    transcription_status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class VoiceNoteListResponse(BaseModel):
    """Schema for paginated voice note list response."""
    voice_notes: list[VoiceNoteResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class VoiceNoteUploadResponse(BaseModel):
    """Schema for voice note upload response."""
    voice_note_id: UUID
    upload_url: Optional[str] = None
    message: str