"""Doctor API schemas."""

from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field


class DoctorBase(BaseModel):
    """Base doctor schema."""
    specialty: str = Field(..., max_length=100)
    license_number: str = Field(..., max_length=100)
    hospital_affiliation: Optional[str] = Field(None, max_length=255)
    email: EmailStr
    full_name: str = Field(..., max_length=255)
    phone: Optional[str] = Field(None, max_length=50)


class DoctorCreate(DoctorBase):
    """Schema for creating a doctor."""
    pass


class DoctorUpdate(BaseModel):
    """Schema for updating a doctor."""
    specialty: Optional[str] = Field(None, max_length=100)
    license_number: Optional[str] = Field(None, max_length=100)
    hospital_affiliation: Optional[str] = Field(None, max_length=255)
    email: Optional[EmailStr] = None
    full_name: Optional[str] = Field(None, max_length=255)
    phone: Optional[str] = Field(None, max_length=50)


class DoctorResponse(DoctorBase):
    """Schema for doctor response."""
    doctor_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DoctorListResponse(BaseModel):
    """Schema for paginated doctor list response."""
    doctors: list[DoctorResponse]
    total: int
    page: int
    page_size: int
    total_pages: int