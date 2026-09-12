"""Telehealth & Doctor Schedule API Schemas for AI-HOS (Milestone U-14)."""

from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field


class PatientIntakeSummary(BaseModel):
    """Normalized intake data attached to an appointment."""
    session_id: Optional[UUID] = None
    chief_complaint: Optional[str] = None
    duration: Optional[str] = None
    severity: Optional[int] = None
    associated_symptoms: list[str] = Field(default_factory=list)
    summary: Optional[str] = None
    has_red_flags: bool = False
    red_flag_warnings: list[str] = Field(default_factory=list)


class DoctorScheduleItemResponse(BaseModel):
    """Enriched appointment representation for doctor's daily schedule."""
    appointment_id: UUID
    patient_id: UUID
    patient_name: str
    patient_gender: Optional[str] = None
    patient_age: Optional[int] = None
    patient_abha: Optional[str] = None
    patient_phone: Optional[str] = None
    scheduled_at: datetime
    duration_minutes: int
    status: str
    meeting_link: Optional[str] = None
    telehealth_room_id: Optional[str] = None
    notes: Optional[str] = None
    intake_summary: Optional[PatientIntakeSummary] = None

    class Config:
        from_attributes = True


class DoctorScheduleListResponse(BaseModel):
    """Aggregated schedule view for doctor consultation queue."""
    date: str
    total_appointments: int
    scheduled_count: int
    in_consultation_count: int
    completed_count: int
    appointments: list[DoctorScheduleItemResponse]


class TelehealthRoomResponse(BaseModel):
    """Full consultation room context for active video encounter."""
    appointment_id: UUID
    room_id: str
    meeting_link: str
    status: str
    doctor_id: UUID
    doctor_name: str
    doctor_specialty: str
    doctor_hospital: Optional[str] = None
    patient_id: UUID
    patient_name: str
    patient_gender: Optional[str] = None
    patient_age: Optional[int] = None
    patient_abha: Optional[str] = None
    patient_phone: Optional[str] = None
    scheduled_at: datetime
    duration_minutes: int
    intake_summary: Optional[PatientIntakeSummary] = None
    telehealth_started_at: Optional[datetime] = None
    telehealth_ended_at: Optional[datetime] = None


class TelehealthActionResponse(BaseModel):
    """Result of start/end telehealth room actions."""
    appointment_id: UUID
    status: str
    message: str
    meeting_link: Optional[str] = None
    telehealth_started_at: Optional[datetime] = None
    telehealth_ended_at: Optional[datetime] = None
