"""Medical Record API schemas."""

from datetime import datetime
from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel, Field


class MedicalRecordContent(BaseModel):
    """Medical record content structure."""
    chief_complaint: str = Field(..., max_length=500)
    history_present_illness: Optional[str] = None
    physical_examination: Optional[str] = None
    assessment: Optional[str] = None
    plan: Optional[str] = None
    diagnosis_codes: Optional[List[str]] = Field(default_factory=list)


class MedicalRecordContentUpdate(BaseModel):
    """Medical record content structure for updates (all fields optional)."""
    chief_complaint: Optional[str] = Field(None, max_length=500)
    history_present_illness: Optional[str] = None
    physical_examination: Optional[str] = None
    assessment: Optional[str] = None
    plan: Optional[str] = None
    diagnosis_codes: Optional[List[str]] = None


class MedicalRecordBase(BaseModel):
    """Base medical record schema."""
    patient_id: UUID
    doctor_id: UUID
    appointment_id: Optional[UUID] = None
    content: MedicalRecordContent
    status: str = Field(default="DRAFT", pattern="^(DRAFT|FINALIZED|AMENDED)$")


class MedicalRecordCreate(MedicalRecordBase):
    """Schema for creating a medical record."""
    pass


class MedicalRecordUpdate(BaseModel):
    """Schema for updating a medical record."""
    content: Optional[MedicalRecordContentUpdate] = None
    status: Optional[str] = Field(None, pattern="^(DRAFT|FINALIZED|AMENDED)$")


class MedicalRecordFilter(BaseModel):
    """Schema for filtering medical records."""
    status: Optional[str] = Field(None, pattern="^(DRAFT|FINALIZED|AMENDED)$")


class MedicalRecordResponse(MedicalRecordBase):
    """Schema for medical record response."""
    record_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class MedicalRecordListResponse(BaseModel):
    """Schema for paginated medical record list response."""
    records: list[MedicalRecordResponse]
    total: int
    page: int
    page_size: int
    total_pages: int