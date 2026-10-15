"""NHCX (National Health Claims Exchange) Integration API (Horizon E / Phase 7).

Implements FHIR R4 Claim and ClaimResponse standards for ABDM / NHCX:
1. Pre-authorization verification against insurance payers/TPAs.
2. Clinical claim submission with diagnostic and procedural billing items.
3. Adjudication tracking, settlement simulation, and immutable audit logs.
"""

from datetime import datetime, timezone
import logging
from typing import List, Optional
import uuid
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.claims import (
    ClaimItem,
    ClaimResponse,
    ClaimStatus,
    ClaimSubmissionRequest,
    ClaimType,
)
from app.database import get_db
from app.models import AuditLog, AuditOutcome, Patient, User, UserRole
from app.services.auth.service import get_current_active_user

logger = logging.getLogger("aihos.nhcx.claims")

router = APIRouter(prefix="/claims", tags=["nhcx-claims"])

# In-memory claims registry for NHCX tracking
_CLAIMS_REGISTRY: dict[str, dict] = {}


def _generate_fhir_claim_resource(claim_data: ClaimSubmissionRequest, claim_id: UUID, claim_ref: str) -> dict:
    """Map claim data into an HL7 FHIR R4 Claim resource bundle."""
    return {
        "resourceType": "Claim",
        "id": str(claim_id),
        "identifier": [
            {
                "system": "https://nhcx.abdm.gov.in/claims",
                "value": claim_ref,
            }
        ],
        "status": "active",
        "type": {
            "coding": [
                {
                    "system": "http://terminology.hl7.org/CodeSystem/claim-type",
                    "code": claim_data.claim_type.value,
                }
            ]
        },
        "use": "claim",
        "patient": {"reference": f"Patient/{claim_data.patient_id}"},
        "provider": {"reference": f"Practitioner/{claim_data.provider_id}"},
        "insurer": {"identifier": {"value": claim_data.insurer_id}},
        "total": {"value": claim_data.total_amount, "currency": "INR"},
        "item": [
            {
                "sequence": item.sequence,
                "productOrService": {"text": item.description},
                "unitPrice": {"value": item.unit_price, "currency": "INR"},
                "quantity": {"value": item.quantity},
                "net": {"value": item.net_amount, "currency": "INR"},
            }
            for item in claim_data.items
        ],
    }


@router.post("/submit", response_model=ClaimResponse, status_code=status.HTTP_201_CREATED)
async def submit_nhcx_claim(
    claim_req: ClaimSubmissionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Submit a clinical insurance claim to the National Health Claims Exchange (NHCX)."""
    claim_id = uuid.uuid4()
    claim_ref = f"NHCX-{datetime.now(timezone.utc).strftime('%Y%m')}-{uuid.uuid4().hex[:8].upper()}"

    # Auto-adjudicate demo coverage based on policy simulation
    adjudicated_amount = round(claim_req.total_amount * 0.85, 2)
    patient_copay = round(claim_req.total_amount - adjudicated_amount, 2)
    now = datetime.now(timezone.utc)

    fhir_resource = _generate_fhir_claim_resource(claim_req, claim_id, claim_ref)

    record = {
        "claim_id": claim_id,
        "claim_reference": claim_ref,
        "patient_id": claim_req.patient_id,
        "provider_id": claim_req.provider_id,
        "insurer_id": claim_req.insurer_id,
        "policy_number": claim_req.policy_number,
        "claim_type": claim_req.claim_type,
        "status": ClaimStatus.ADJUDICATED,
        "total_amount": claim_req.total_amount,
        "adjudicated_amount": adjudicated_amount,
        "patient_copay": patient_copay,
        "submitted_at": now,
        "adjudicated_at": now,
        "settlement_reference": f"SETTLE-{uuid.uuid4().hex[:6].upper()}",
        "rejection_reason": None,
        "fhir_claim_resource": fhir_resource,
    }
    _CLAIMS_REGISTRY[str(claim_id)] = record

    # Log audit entry
    audit = AuditLog(
        user_id=current_user.user_id,
        action="CREATE",
        resource_type="NHCX_CLAIM",
        resource_id=claim_id,
        outcome=AuditOutcome.SUCCESS,
    )
    db.add(audit)
    await db.commit()

    logger.info("Successfully submitted and adjudicated NHCX claim %s for patient %s", claim_ref, claim_req.patient_id)
    return ClaimResponse(**record)


@router.post("/pre-auth", status_code=status.HTTP_200_OK)
async def check_claim_pre_authorization(
    patient_id: UUID,
    insurer_id: str,
    policy_number: str,
    estimated_amount: float,
    current_user: User = Depends(get_current_active_user),
):
    """Perform pre-authorization verification for hospital admission or outpatient procedure."""
    is_valid_policy = len(policy_number.strip()) >= 5
    covered_limit = 500000.0  # ₹5,00,000 standard AB-PMJAY / insurance ceiling
    approved = is_valid_policy and estimated_amount <= covered_limit

    return {
        "pre_auth_id": f"PREAUTH-{uuid.uuid4().hex[:8].upper()}",
        "patient_id": str(patient_id),
        "insurer_id": insurer_id,
        "policy_number": policy_number,
        "status": "APPROVED" if approved else "DENIED",
        "approved_amount": min(estimated_amount, covered_limit) if approved else 0.0,
        "denial_reason": None if approved else "Requested amount exceeds remaining policy cover or invalid policy identifier.",
        "verified_at": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/{claim_id}", response_model=ClaimResponse)
async def get_claim_status(
    claim_id: UUID,
    current_user: User = Depends(get_current_active_user),
):
    """Retrieve the real-time status and adjudication details for an NHCX claim."""
    record = _CLAIMS_REGISTRY.get(str(claim_id))
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Claim with ID {claim_id} not found on NHCX registry",
        )
    return ClaimResponse(**record)


@router.get("/patient/{patient_id}", response_model=List[ClaimResponse])
async def list_patient_claims(
    patient_id: UUID,
    current_user: User = Depends(get_current_active_user),
):
    """List all insurance claims filed for a specific patient."""
    results = [
        ClaimResponse(**c)
        for c in _CLAIMS_REGISTRY.values()
        if str(c["patient_id"]) == str(patient_id)
    ]
    return results
