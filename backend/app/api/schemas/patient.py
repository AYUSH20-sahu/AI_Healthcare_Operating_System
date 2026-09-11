"""Patient API schemas."""

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class PatientBase(BaseModel):
    """Base patient schema."""
    abha_address: str | None = Field(None, max_length=255)
    full_name: str = Field(..., max_length=255)
    date_of_birth: date
    gender: str = Field(..., max_length=50)
    phone: str | None = Field(None, max_length=50)
    email: EmailStr | None = None
    address: str | None = None
    emergency_contact_name: str | None = Field(None, max_length=255)
    emergency_contact_phone: str | None = Field(None, max_length=50)


class PatientCreate(PatientBase):
    """Schema for creating a patient."""


class PatientUpdate(BaseModel):
    """Schema for updating a patient."""
    abha_address: str | None = Field(None, max_length=255)
    full_name: str | None = Field(None, max_length=255)
    date_of_birth: date | None = None
    gender: str | None = Field(None, max_length=50)
    phone: str | None = Field(None, max_length=50)
    email: EmailStr | None = None
    address: str | None = None
    emergency_contact_name: str | None = Field(None, max_length=255)
    emergency_contact_phone: str | None = Field(None, max_length=50)


class PatientResponse(PatientBase):
    """Schema for patient response."""
    patient_id: UUID
    user_id: UUID | None = None
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


class PatientSelfUpdate(BaseModel):
    """Schema for patient updating their own profile."""
    full_name: str | None = Field(None, max_length=255)
    phone: str | None = Field(None, max_length=50)
    address: str | None = None
    emergency_contact_name: str | None = Field(None, max_length=255)
    emergency_contact_phone: str | None = Field(None, max_length=50)
    abha_address: str | None = Field(None, max_length=255)


class PatientPortalAppointmentItem(BaseModel):
    """Patient view of an appointment."""
    appointment_id: UUID
    doctor_id: UUID
    doctor_name: str
    doctor_specialty: str | None = None
    hospital_affiliation: str | None = None
    scheduled_at: datetime
    duration_minutes: int
    status: str
    reason: str | None = None
    meeting_link: str | None = None


class PatientPortalRecordItem(BaseModel):
    """Patient view of a finalized medical record."""
    record_id: UUID
    doctor_id: UUID
    doctor_name: str
    appointment_id: UUID | None = None
    status: str
    chief_complaint: str | None = None
    assessment: str | None = None
    plan: str | None = None
    content: dict | None = None
    finalized_at: datetime | None = None
    created_at: datetime


class PatientPortalPrescriptionItem(BaseModel):
    """Patient view of a prescription."""
    prescription_id: UUID
    doctor_id: UUID
    doctor_name: str
    medical_record_id: UUID | None = None
    status: str
    medications: list[dict]
    notes: str | None = None
    finalized_at: datetime | None = None
    created_at: datetime


class PatientPortalDashboardResponse(BaseModel):
    """Patient dashboard summary."""
    patient: PatientResponse
    upcoming_appointments_count: int
    finalized_records_count: int
    active_prescriptions_count: int
    next_appointment: PatientPortalAppointmentItem | None = None
    recent_prescriptions: list[PatientPortalPrescriptionItem] = Field(default_factory=list)