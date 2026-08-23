"""Doctor Review/Approval API schemas for M23."""

from datetime import datetime
from uuid import UUID
from typing import Optional, Literal
from pydantic import BaseModel, Field, ConfigDict


class MedicalRecordApprovalRequest(BaseModel):
    """Schema for medical record approval/rejection."""
    action: Literal["approve", "reject", "request_changes"]
    reviewer_notes: Optional[str] = Field(None, max_length=2000, description="Doctor's review notes")
    edited_content: Optional[dict] = Field(None, description="Edited content if requesting changes")


class MedicalRecordApprovalResponse(BaseModel):
    """Schema for medical record approval response."""
    record_id: UUID
    status: str
    action: str
    reviewer_id: UUID
    reviewed_at: datetime
    reviewer_notes: Optional[str] = None
    message: str


class PrescriptionApprovalRequest(BaseModel):
    """Schema for prescription approval/rejection."""
    action: Literal["approve", "reject", "request_changes"]
    reviewer_notes: Optional[str] = Field(None, max_length=2000, description="Doctor's review notes")
    edited_medications: Optional[list[dict]] = Field(None, description="Edited medications if requesting changes")


class PrescriptionApprovalResponse(BaseModel):
    """Schema for prescription approval response."""
    prescription_id: UUID
    status: str
    action: str
    reviewer_id: UUID
    reviewed_at: datetime
    reviewer_notes: Optional[str] = None
    message: str


class DraftListResponse(BaseModel):
    """Schema for listing draft records/prescriptions for review."""
    medical_records: list[dict] = Field(default_factory=list)
    prescriptions: list[dict] = Field(default_factory=list)
    total: int
    page: int
    page_size: int
    total_pages: int