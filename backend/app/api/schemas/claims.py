"""NHCX (National Health Claims Exchange) & FHIR Claim Schemas."""

from datetime import datetime
from enum import Enum
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, Field


class ClaimType(str, Enum):
    INSTITUTIONAL = "institutional"
    PROFESSIONAL = "professional"
    PHARMACY = "pharmacy"


class ClaimStatus(str, Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    PRE_AUTH_APPROVED = "pre_auth_approved"
    ADJUDICATED = "adjudicated"
    SETTLED = "settled"
    REJECTED = "rejected"


class ClaimItem(BaseModel):
    sequence: int
    care_type: str = Field(..., description="Procedure code / consultation / lab / medication")
    description: str
    net_amount: float
    unit_price: float
    quantity: int = 1


class ClaimSubmissionRequest(BaseModel):
    patient_id: UUID
    provider_id: UUID
    appointment_id: Optional[UUID] = None
    insurer_id: str = Field(..., description="NHCX Insurance Payer ID / TPA Identifier")
    policy_number: str = Field(..., description="Patient Health Insurance Policy Number")
    claim_type: ClaimType = ClaimType.PROFESSIONAL
    total_amount: float
    items: List[ClaimItem]
    diagnoses: List[str] = Field(default_factory=list)


class ClaimResponse(BaseModel):
    claim_id: UUID
    claim_reference: str
    patient_id: UUID
    provider_id: UUID
    insurer_id: str
    policy_number: str
    claim_type: ClaimType
    status: ClaimStatus
    total_amount: float
    adjudicated_amount: Optional[float] = None
    patient_copay: Optional[float] = None
    submitted_at: datetime
    adjudicated_at: Optional[datetime] = None
    settlement_reference: Optional[str] = None
    rejection_reason: Optional[str] = None
    fhir_claim_resource: Optional[dict] = None
