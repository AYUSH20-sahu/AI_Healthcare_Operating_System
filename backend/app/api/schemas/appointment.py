"""Appointment API schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class AppointmentBase(BaseModel):
    """Base appointment schema."""
    patient_id: UUID
    doctor_id: UUID
    scheduled_at: datetime
    duration_minutes: int = Field(default=30, ge=15, le=240)
    notes: str | None = None


class AppointmentCreate(AppointmentBase):
    """Schema for creating an appointment."""


class AppointmentUpdate(BaseModel):
    """Schema for updating an appointment."""
    scheduled_at: datetime | None = None
    duration_minutes: int | None = Field(None, ge=15, le=240)
    notes: str | None = None


class AppointmentResponse(AppointmentBase):
    """Schema for appointment response."""
    appointment_id: UUID
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AppointmentListResponse(BaseModel):
    """Schema for paginated appointment list response."""
    appointments: list[AppointmentResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class TimeSlotItem(BaseModel):
    """Individual clinical time slot for a doctor's schedule."""
    slot_time: str = Field(..., description="Display time string, e.g. '09:30 AM'")
    start_time: datetime = Field(..., description="ISO 8601 start timestamp")
    end_time: datetime = Field(..., description="ISO 8601 end timestamp")
    duration_minutes: int = Field(default=30)
    is_available: bool = Field(..., description="Whether this slot is open for booking")
    conflict_reason: str | None = Field(None, description="Reason if slot is not available")


class DoctorAvailabilityResponse(BaseModel):
    """Full daily time slot matrix for an attending physician."""
    doctor_id: UUID
    doctor_name: str
    specialty: str
    hospital_affiliation: str | None = None
    date: str
    total_slots: int
    available_slots_count: int
    slots: list[TimeSlotItem]


class PatientAppointmentBookRequest(BaseModel):
    """Dedicated booking request payload submitted by patients."""
    doctor_id: UUID
    scheduled_at: datetime
    duration_minutes: int = Field(default=30, ge=15, le=120)
    reason: str | None = Field(None, max_length=1000, description="Patient-reported consultation reason or chief complaint")
    intake_session_id: UUID | None = Field(None, description="Optional active U-13 intake session ID to link")