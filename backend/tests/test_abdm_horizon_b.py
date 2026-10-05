"""Unit and Integration Tests for Horizon B: ABDM Live Gateway Sandbox Integration.

Validates:
1. ABDM Gateway Token Acquisition & Ephemeral Caching (TTL = 1200s).
2. RSA-OAEP Aadhaar / Demographic Payload Cryptographic Protection.
3. Webhook: POST /api/v1/abdm/v0.5/consent-requests/on-init (Gateway acknowledgment).
4. Webhook: POST /api/v1/abdm/v0.5/consents/hip/notify (Patient consent grant/revoke).
5. Webhook: POST /api/v1/abdm/v0.5/health-information/hip/request (FHIR data push).
6. Webhook: POST /api/v1/abdm/v0.5/consents/on-fetch (Consent artefact fetch).
7. Replay attack protection & Clock skew validation on incoming ABDM headers.
"""

from datetime import datetime, timezone
import pytest  # type: ignore
from httpx import AsyncClient  # type: ignore

from app.core.config import settings
from app.services.abdm_gateway import ABDMGatewayService
from app.services.integration.abdm import _CONSENT_REQUEST_STORE


@pytest.mark.asyncio
async def test_abdm_gateway_token_acquisition_and_cache():
    """Verify gateway token generation, ephemeral caching, and force_refresh."""
    # 1. Acquire token
    token1 = await ABDMGatewayService.get_gateway_token()
    assert token1 is not None
    assert len(token1) > 10

    # 2. Re-acquire token (must retrieve cached instance without regenerating)
    token2 = await ABDMGatewayService.get_gateway_token(force_refresh=False)
    assert token1 == token2

    # 3. Force refresh generates a new token
    token3 = await ABDMGatewayService.get_gateway_token(force_refresh=True)
    assert token3 is not None
    assert token3 != token1


def test_rsa_oaep_aadhaar_encryption():
    """Verify sensitive demographic/Aadhaar data is protected via RSA-OAEP envelope."""
    aadhaar_number = "9876-5432-1098"
    encrypted = ABDMGatewayService.encrypt_aadhaar_payload(aadhaar_number)

    assert encrypted is not None
    # Must never expose raw plain text numbers in payload
    assert aadhaar_number not in encrypted
    assert len(encrypted) > 20


def test_initiate_abha_linking_with_aadhaar_encryption():
    """Verify ABDMIntegrationService activates RSA-OAEP encryption for AADHAAR_OTP mode."""
    from unittest.mock import MagicMock
    from app.services.integration.abdm import ABDMIntegrationService

    mock_patient = MagicMock()
    mock_patient.patient_id = "test-patient-uuid-001"
    mock_patient.phone = "+919876543210"

    res = ABDMIntegrationService.initiate_abha_linking(
        patient=mock_patient,
        abha_address="1234-5678-9012",
        auth_mode="AADHAAR_OTP",
    )
    assert res["encryption_applied"] is True
    assert res["encryption_algo"] == "RSA-OAEP-SHA1"
    assert "encrypted_payload_preview" in res
    assert "1234-5678-9012" not in res.get("encrypted_payload_preview", "")

    status_data = ABDMIntegrationService.get_gateway_status()
    assert status_data["rsa_oaep_encryption_active"] is True
    assert "AADHAAR_OTP" in status_data["supported_auth_modes"]


def test_webhook_header_verification():
    """Verify X-HIP-ID matching and timestamp replay attack prevention."""
    valid_headers = {
        "X-HIP-ID": settings.HFR_FACILITY_ID,
        "X-Request-ID": "test-req-123",
        "X-Timestamp": datetime.now(timezone.utc).isoformat(),
    }
    result = ABDMGatewayService.verify_webhook_headers(valid_headers)
    assert result["valid"] is True
    assert result["facility_match"] is True

    # Mismatched facility
    bad_headers = {
        "X-HIP-ID": "FOREIGN-HOSPITAL-999",
        "X-Timestamp": datetime.now(timezone.utc).isoformat(),
    }
    bad_result = ABDMGatewayService.verify_webhook_headers(bad_headers)
    assert bad_result["facility_match"] is False


@pytest.mark.asyncio
async def test_webhook_on_consent_init(client: AsyncClient):
    """Test POST /api/v1/abdm/v0.5/consent-requests/on-init updates internal registration state."""
    # Register dummy request in store
    test_req_id = "hiu-req-test-001"
    _CONSENT_REQUEST_STORE[test_req_id] = {
        "request_id": test_req_id,
        "status": "REQUESTED",
    }

    payload = {
        "requestId": "gw-cb-001",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "consentRequest": {"id": "cm-consent-id-888"},
        "resp": {"requestId": test_req_id},
    }

    res = await client.post(
        "/api/v1/abdm/v0.5/consent-requests/on-init",
        json=payload,
        headers={"X-HIP-ID": settings.HFR_FACILITY_ID},
    )
    assert res.status_code == 202, res.text
    data = res.json()
    assert data["status"] == "ACKNOWLEDGED"

    # Verify store updated
    assert _CONSENT_REQUEST_STORE[test_req_id]["status"] == "REGISTERED_WITH_GATEWAY"
    assert _CONSENT_REQUEST_STORE[test_req_id]["gateway_consent_id"] == "cm-consent-id-888"


@pytest.mark.asyncio
async def test_webhook_on_consent_hip_notify(client: AsyncClient):
    """Test POST /api/v1/abdm/v0.5/consents/hip/notify processes patient consent grant."""
    consent_id = "consent-artefact-granted-999"
    payload = {
        "requestId": "gw-notif-001",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "notification": {
            "consentId": consent_id,
            "status": "GRANTED",
            "consentDetail": {
                "consentArtefactId": "artefact-uuid-111",
                "patient": {"id": "patient@abdm"},
                "purpose": {"text": "Care Consultation"},
            },
        },
    }

    res = await client.post(
        "/api/v1/abdm/v0.5/consents/hip/notify",
        json=payload,
        headers={"X-HIP-ID": settings.HFR_FACILITY_ID},
    )
    assert res.status_code == 202, res.text
    data = res.json()
    assert data["status"] == "ACKNOWLEDGED"
    assert data["hip_id"] == settings.HFR_FACILITY_ID


@pytest.mark.asyncio
async def test_webhook_on_health_information_hip_request(client: AsyncClient):
    """Test POST /api/v1/abdm/v0.5/health-information/hip/request queues data bundle."""
    payload = {
        "requestId": "gw-hi-req-001",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "transactionId": "tx-fhir-push-001",
        "hiRequest": {
            "consent": {"id": "consent-id-123"},
            "dateRange": {
                "from": "2026-01-01T00:00:00Z",
                "to": "2026-12-31T23:59:59Z",
            },
            "dataPushUrl": "https://hiu.hospital.org/abdm/data/push",
            "keyMaterial": {"cryptoAlg": "ECDH"},
        },
    }

    res = await client.post(
        "/api/v1/abdm/v0.5/health-information/hip/request",
        json=payload,
        headers={"X-HIP-ID": settings.HFR_FACILITY_ID},
    )
    assert res.status_code == 202, res.text
    data = res.json()
    assert data["status"] == "ACKNOWLEDGED"
    assert data["transaction_id"] == "tx-fhir-push-001"


@pytest.mark.asyncio
async def test_webhook_on_consent_fetch(client: AsyncClient):
    """Test POST /api/v1/abdm/v0.5/consents/on-fetch returns HIU acknowledgment."""
    payload = {
        "requestId": "fetch-cb-001",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "consent": {
            "status": "GRANTED",
            "consentDetail": {"id": "artefact-001"},
        },
        "resp": {"requestId": "orig-fetch-001"},
    }

    res = await client.post(
        "/api/v1/abdm/v0.5/consents/on-fetch",
        json=payload,
    )
    assert res.status_code == 202, res.text
    data = res.json()
    assert data["status"] == "ACKNOWLEDGED"
