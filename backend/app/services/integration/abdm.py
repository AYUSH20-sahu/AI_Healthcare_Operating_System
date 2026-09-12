"""Ayushman Bharat Digital Mission (ABDM) Integration Service Boundary (Milestone U-21).

Provides integration stubs for:
- ABHA address / health ID linking and 2-step OTP verification
- Consent Manager HIU / HIP lifecycle hooks & notification callbacks
- HFR (Health Facility Registry) and HPR (Healthcare Professional Registry) profiles
- Strict sandbox isolation and security guarantees (Zero Credential Exposure)
"""

from datetime import datetime, timedelta
import logging
import re
import secrets
from typing import Any, Dict, List, Optional
import uuid
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models import AuditLog, AuditOutcome, Doctor, Patient, User

logger = logging.getLogger("aihos.abdm")

# In-memory transaction registry for OTP verification (in production, backed by Redis)
_ABHA_TX_STORE: Dict[str, Dict[str, Any]] = {}
_CONSENT_REQUEST_STORE: Dict[str, Dict[str, Any]] = {}


class ABDMIntegrationService:
    """Isolated integration service boundary for the ABDM ecosystem."""

    @classmethod
    def get_gateway_status(cls) -> Dict[str, Any]:
        """Return public status of the ABDM gateway.
        
        CRITICAL: Never exposes ABDM_CLIENT_SECRET or raw secret credentials.
        """
        is_configured = bool(settings.ABDM_CLIENT_ID and settings.ABDM_CLIENT_SECRET)
        return {
            "gateway_status": "ONLINE" if (is_configured or settings.ABDM_SANDBOX_MODE) else "OFFLINE",
            "environment": "sandbox" if settings.ABDM_SANDBOX_MODE else "production",
            "base_url": settings.ABDM_BASE_URL,
            "hfr_facility_id": settings.HFR_FACILITY_ID,
            "hfr_facility_name": settings.HFR_FACILITY_NAME,
            "supported_auth_modes": ["MOBILE_OTP", "AADHAAR_OTP"],
            "client_configured": is_configured,
            "abdm_version": "v0.5",
        }

    @classmethod
    def initiate_abha_linking(
        cls,
        patient: Patient,
        abha_address: str,
        auth_mode: str = "MOBILE_OTP",
    ) -> Dict[str, Any]:
        """Initiate ABHA linking OTP transaction for patient."""
        cleaned_address = abha_address.strip().lower()
        if not re.match(r"^[a-zA-Z0-9._-]+(@[a-zA-Z0-9]+)?$", cleaned_address):
            raise ValueError("Invalid ABHA address format. Must be e.g. name@abdm or standard identifier.")

        transaction_id = str(uuid.uuid4())
        # In sandbox, default OTP is 123456 or a 6-digit random code
        simulated_otp = "123456" if settings.ABDM_SANDBOX_MODE else f"{secrets.randbelow(900000) + 100000}"

        _ABHA_TX_STORE[transaction_id] = {
            "patient_id": patient.patient_id,
            "abha_address": cleaned_address,
            "auth_mode": auth_mode,
            "expected_otp": simulated_otp,
            "created_at": datetime.utcnow(),
            "expires_at": datetime.utcnow() + timedelta(minutes=10),
        }

        masked_dest = patient.phone[-4:] if patient.phone and len(patient.phone) >= 4 else "XXXX"

        return {
            "transaction_id": transaction_id,
            "abha_address": cleaned_address,
            "auth_mode": auth_mode,
            "message": f"OTP successfully dispatched to mobile ending with {masked_dest}.",
            "sandbox_test_otp": "123456" if settings.ABDM_SANDBOX_MODE else None,
            "expires_in_seconds": 600,
        }

    @classmethod
    async def verify_abha_linking(
        cls,
        patient: Patient,
        transaction_id: str,
        otp: str,
        db: AsyncSession,
        current_user: User,
    ) -> Dict[str, Any]:
        """Verify OTP and persist verified ABHA address on the patient profile."""
        tx_data = _ABHA_TX_STORE.get(transaction_id)
        if not tx_data:
            raise ValueError("Invalid or expired transaction_id. Please restart the OTP process.")

        if tx_data["patient_id"] != patient.patient_id:
            raise PermissionError("Transaction does not belong to the current authenticated patient.")

        if datetime.utcnow() > tx_data["expires_at"]:
            _ABHA_TX_STORE.pop(transaction_id, None)
            raise ValueError("OTP has expired. Please request a new verification code.")

        # In sandbox mode, accept either the generated code or universal test code '123456'
        valid = (otp.strip() == tx_data["expected_otp"]) or (settings.ABDM_SANDBOX_MODE and otp.strip() == "123456")
        if not valid:
            raise ValueError("Invalid OTP provided. Please re-enter the verification code.")

        # Successfully verified: persist to patient
        target_address = tx_data["abha_address"]
        patient.abha_address = target_address
        patient.updated_at = datetime.utcnow()

        # Write immutable audit event
        audit_entry = AuditLog(
            user_id=current_user.user_id,
            action="ABDM_LINK_ABHA",
            resource_type="patients",
            resource_id=patient.patient_id,
            outcome=AuditOutcome.SUCCESS,
            details={
                "abha_address": target_address,
                "auth_mode": tx_data["auth_mode"],
                "transaction_id": transaction_id,
            },
        )
        db.add(audit_entry)
        await db.commit()
        await db.refresh(patient)

        _ABHA_TX_STORE.pop(transaction_id, None)

        return {
            "status": "LINKED",
            "patient_id": str(patient.patient_id),
            "abha_address": target_address,
            "verified_at": datetime.utcnow().isoformat(),
            "message": "ABHA address linked successfully to your official health record.",
        }

    @classmethod
    async def unlink_abha(
        cls,
        patient: Patient,
        db: AsyncSession,
        current_user: User,
    ) -> Dict[str, Any]:
        """Safely unlink ABHA address from patient profile with audit logging."""
        previous_address = patient.abha_address
        patient.abha_address = None
        patient.updated_at = datetime.utcnow()

        audit_entry = AuditLog(
            user_id=current_user.user_id,
            action="ABDM_UNLINK_ABHA",
            resource_type="patients",
            resource_id=patient.patient_id,
            outcome=AuditOutcome.SUCCESS,
            details={
                "previous_abha_address": previous_address,
            },
        )
        db.add(audit_entry)
        await db.commit()
        await db.refresh(patient)

        return {
            "status": "UNLINKED",
            "patient_id": str(patient.patient_id),
            "message": "ABHA address unlinked successfully.",
        }

    @classmethod
    def create_consent_request(
        cls,
        patient_id: UUID,
        provider_id: UUID,
        record_scope: str = "full_access",
        purpose: str = "Clinical Care and Consultation",
    ) -> Dict[str, Any]:
        """Create ABDM Consent Manager HIU request artefact."""
        request_id = str(uuid.uuid4())
        record = {
            "request_id": request_id,
            "patient_id": str(patient_id),
            "provider_id": str(provider_id),
            "record_scope": record_scope,
            "purpose": purpose,
            "status": "REQUESTED",
            "created_at": datetime.utcnow().isoformat(),
            "consent_artefact_id": None,
        }
        _CONSENT_REQUEST_STORE[request_id] = record
        return record

    @classmethod
    def handle_consent_notification(cls, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Process ABDM Consent Manager notification callback."""
        notification_id = payload.get("notification_id") or str(uuid.uuid4())
        status = payload.get("status", "GRANTED")
        request_id = payload.get("request_id")

        if request_id and request_id in _CONSENT_REQUEST_STORE:
            _CONSENT_REQUEST_STORE[request_id]["status"] = status
            _CONSENT_REQUEST_STORE[request_id]["consent_artefact_id"] = payload.get("consent_artefact_id", str(uuid.uuid4()))

        return {
            "notification_id": notification_id,
            "acknowledged_at": datetime.utcnow().isoformat(),
            "status": "ACKNOWLEDGED",
        }

    @classmethod
    def get_consent_status(cls, request_id: str) -> Dict[str, Any]:
        """Inspect status of ABDM consent artefact."""
        if request_id in _CONSENT_REQUEST_STORE:
            return _CONSENT_REQUEST_STORE[request_id]
        return {
            "request_id": request_id,
            "status": "GRANTED",  # Default positive state for simulation
            "consent_artefact_id": f"artefact-{request_id[:8]}",
            "updated_at": datetime.utcnow().isoformat(),
        }

    @classmethod
    def get_hfr_facility_info(cls) -> Dict[str, Any]:
        """Return HFR (Health Facility Registry) metadata."""
        return {
            "facility_id": settings.HFR_FACILITY_ID,
            "facility_name": settings.HFR_FACILITY_NAME,
            "facility_type": "Multispeciality Hospital & Telehealth Node",
            "ownership": "Private / Autonomous Healthcare Node",
            "state": "Delhi",
            "district": "New Delhi",
            "abdm_registered": True,
            "hiu_hip_status": "ACTIVE_HIP_HIU",
        }

    @classmethod
    def get_hpr_practitioner_info(cls, doctor: Doctor) -> Dict[str, Any]:
        """Return HPR (Healthcare Professionals Registry) verification stub."""
        hpr_id = f"{doctor.full_name.lower().replace('dr.', '').strip().replace(' ', '')}@hpr"
        return {
            "doctor_id": str(doctor.doctor_id),
            "hpr_id": hpr_id,
            "full_name": doctor.full_name,
            "specialty": doctor.specialty or "General Medicine",
            "registration_number": doctor.license_number or "HPR-IN-9988",
            "verification_status": "VERIFIED_HPR_CLINICIAN",
            "telehealth_authorized": True,
        }
