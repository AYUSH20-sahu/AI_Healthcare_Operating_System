"""Schemas for Patient Medical Reports and Medicine Reminders (Milestone U-16)."""

from datetime import date, datetime
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, Field


# =============================================================================
# Patient Medical Reports Schemas
# =============================================================================

class PatientReportResponse(BaseModel):
    """Metadata response schema for an uploaded patient medical report."""
    report_id: UUID
    patient_id: UUID
    title: str
    report_type: str  # lab, imaging, prescription, discharge, other
    file_name: str
    file_size_bytes: int
    mime_type: str
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PatientReportListResponse(BaseModel):
    """List response for patient medical reports."""
    reports: List[PatientReportResponse]
    total: int


# =============================================================================
# Patient Medicine Reminders Schemas
# =============================================================================

class MedicineReminderCreateRequest(BaseModel):
    """Request schema for creating a new medicine reminder."""
    medication_name: str = Field(..., min_length=1, max_length=255, description="Medication name")
    dosage: str = Field(..., min_length=1, max_length=100, description="Dosage (e.g. 500mg, 1 tablet)")
    frequency: str = Field(..., min_length=1, max_length=100, description="Frequency (e.g. Once daily, Twice daily)")
    times_of_day: List[str] = Field(default_factory=list, description="Target reminder times in HH:MM format")
    instructions: Optional[str] = Field(None, max_length=1000, description="Special intake instructions")
    start_date: Optional[date] = Field(None, description="Start date of medication course")
    end_date: Optional[date] = Field(None, description="End date of medication course")
    is_active: bool = Field(True, description="Whether the reminder is active")


class MedicineReminderUpdateRequest(BaseModel):
    """Request schema for updating an existing medicine reminder."""
    medication_name: Optional[str] = Field(None, min_length=1, max_length=255)
    dosage: Optional[str] = Field(None, min_length=1, max_length=100)
    frequency: Optional[str] = Field(None, min_length=1, max_length=100)
    times_of_day: Optional[List[str]] = None
    instructions: Optional[str] = Field(None, max_length=1000)
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    is_active: Optional[bool] = None


class MedicineReminderResponse(BaseModel):
    """Response schema for a medicine reminder schedule."""
    reminder_id: UUID
    patient_id: UUID
    medication_name: str
    dosage: str
    frequency: str
    times_of_day: List[str]
    instructions: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class MedicineReminderListResponse(BaseModel):
    """List response for medicine reminders."""
    reminders: List[MedicineReminderResponse]
    total: int
