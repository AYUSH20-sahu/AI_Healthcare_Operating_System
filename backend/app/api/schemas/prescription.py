"""Prescription Pydantic schemas."""

from typing import Optional, List
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class MedicationBase(BaseModel):
    """Base medication schema."""
    name: str = Field(..., min_length=1, max_length=255, description="Medication name")
    dosage: str = Field(..., min_length=1, max_length=100, description="Dosage (e.g., 500mg)")
    frequency: str = Field(..., min_length=1, max_length=100, description="Frequency (e.g., twice daily)")
    duration: str = Field(..., min_length=1, max_length=100, description="Duration (e.g., 7 days)")
    route: Optional[str] = Field(None, max_length=50, description="Route of administration (e.g., oral, IV)")
    instructions: Optional[str] = Field(None, max_length=500, description="Additional instructions")
    quantity: Optional[int] = Field(None, ge=1, description="Quantity prescribed")
    refills: Optional[int] = Field(0, ge=0, description="Number of refills allowed")


class MedicationCreate(MedicationBase):
    """Schema for creating a medication entry."""
    pass


class MedicationResponse(MedicationBase):
    """Schema for medication response."""
    model_config = ConfigDict(from_attributes=True)


class PrescriptionBase(BaseModel):
    """Base prescription schema."""
    patient_id: UUID = Field(..., description="Patient ID")
    doctor_id: UUID = Field(..., description="Doctor ID")
    medical_record_id: Optional[UUID] = Field(None, description="Associated medical record ID")
    medications: List[MedicationCreate] = Field(..., min_length=1, description="List of medications")
    notes: Optional[str] = Field(None, max_length=1000, description="Prescription notes")

    model_config = ConfigDict(arbitrary_types_allowed=True)


class PrescriptionCreate(PrescriptionBase):
    """Schema for creating a prescription."""
    pass


class PrescriptionUpdate(BaseModel):
    """Schema for updating a prescription."""
    medications: Optional[List[MedicationCreate]] = Field(None, min_length=1, description="List of medications")
    notes: Optional[str] = Field(None, max_length=1000, description="Prescription notes")
    status: Optional[str] = Field(None, pattern="^(DRAFT|FINALIZED|CANCELLED)$", description="Prescription status")


class PrescriptionResponse(PrescriptionBase):
    """Schema for prescription response."""
    prescription_id: UUID
    status: str
    created_at: datetime
    updated_at: datetime
    finalized_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class PrescriptionListResponse(BaseModel):
    """Schema for paginated prescription list response."""
    prescriptions: List[PrescriptionResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class InteractionCheckRequest(BaseModel):
    """Schema for interaction check request."""
    patient_id: UUID = Field(..., description="Patient ID")
    medications: List[MedicationCreate] = Field(..., min_length=1, description="List of medications to check")


class InteractionWarning(BaseModel):
    """Schema for drug interaction/allergy warning."""
    severity: str = Field(..., description="Warning severity: mild, moderate, severe")
    type: str = Field(..., description="Warning type: interaction, allergy")
    medication: str = Field(..., description="Medication name")
    description: str = Field(..., description="Warning description")
    recommendation: Optional[str] = Field(None, description="Clinical recommendation")


class InteractionCheckResponse(BaseModel):
    """Schema for interaction check response."""
    warnings: List[InteractionWarning]
    has_warnings: bool