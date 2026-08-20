"""Patient API schemas."""

from datetime import date, datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field


class PatientBase(BaseModel):
    """Base patient schema."""
    abha_address: Optional[str] = Field(None, max_length=255)
    full_name: str = Field(..., max_length=255)
    date_of_birth: date
    gender: str = Field(..., max_length=50)
    phone: Optional[str] = Field(None, max_length=50)
    email: Optional[EmailStr] = None
    address: Optional[str] = None
    emergency_contact_name: Optional[str] = Field(None, max_length=255)
    emergency_contact_phone: Optional[str] = Field(None, max_length=50)


class PatientCreate(PatientBase):
    """Schema for creating a patient."""
    pass


class PatientUpdate(BaseModel):
    """Schema for updating a patient."""
    abha_address: Optional[str] = Field(None, max_length=255)
    full_name: Optional[str] = Field(None, max_length=255)
    date_of_birth: Optional[date] = None
    gender: Optional[str] = Field(None, max_length=50)
    phone: Optional[str] = Field(None, max_length=50)
    email: Optional[EmailStr] = None
    address: Optional[str] = None
    emergency_contact_name: Optional[str] = Field(None, max_length=255)
    emergency_contact_phone: Optional[str] = Field(None, max_length=50)


class PatientResponse(PatientBase):
    """Schema for patient response."""
    patient_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PatientListResponse(BaseModel):
    """Schema for paginated patient list response."""
    patients: list[PatientResponse]
    total: int
    page: int
    page_size: int
    total_pages: int