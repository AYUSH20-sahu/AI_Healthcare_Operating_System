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