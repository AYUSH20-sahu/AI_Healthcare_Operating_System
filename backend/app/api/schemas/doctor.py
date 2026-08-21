"""Doctor API schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class DoctorBase(BaseModel):
    """Base doctor schema."""
    specialty: str = Field(..., max_length=100)
    license_number: str = Field(..., max_length=100)
    hospital_affiliation: str | None = Field(None, max_length=255)
    email: EmailStr
    full_name: str = Field(..., max_length=255)
    phone: str | None = Field(None, max_length=50)


class DoctorCreate(DoctorBase):
    """Schema for creating a doctor."""


class DoctorUpdate(BaseModel):
    """Schema for updating a doctor."""
    specialty: str | None = Field(None, max_length=100)
    license_number: str | None = Field(None, max_length=100)
    hospital_affiliation: str | None = Field(None, max_length=255)
    email: EmailStr | None = None
    full_name: str | None = Field(None, max_length=255)
    phone: str | None = Field(None, max_length=50)


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