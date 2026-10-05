"""Test Suite for Horizon E: HL7 FHIR R4 Validation & PDF Document Engine.

Validates:
1. Pydantic v2 FHIR R4 Schema Validator (Patient, Encounter, Condition, MedicationRequest,
   DiagnosticReport, Observation, Composition, Bundle).
2. Negative validation handling & FHIR OperationOutcome generation.
3. Inpatient Discharge Summary FHIR document bundle compilation and validation.
4. Cryptographically signed Prescription PDF generation, QR embedding, and digital stamp.
5. Cryptographically signed Discharge Summary PDF generation.
6. Digital signature verification and tamper detection.
7. REST API endpoints (/clinical-documents/fhir/validate, /pdf, /verify-signature).
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    BedVitalsLog,
    Doctor,
    InpatientBed,
    NurseTask,
    Patient,
    Prescription,
    PrescriptionStatus,
    User,
    UserRole,
)
from app.services.auth.service import create_access_token, get_password_hash
from app.services.clinical_pdf import (
    create_institutional_digital_signature,
    generate_canonical_clinical_digest,
    generate_signed_discharge_summary_pdf,
    generate_signed_prescription_pdf,
    verify_clinical_document_signature,
    verify_pdf_bytes_tamper,
)
from app.services.fhir_validator import FHIRValidator
from app.services.integration.fhir_mapper import (
    to_fhir_composition,
    to_fhir_discharge_bundle,
    to_fhir_encounter,
    to_fhir_observation,
)


# ─── Fixtures ─────────────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def horizon_e_test_data(db_session: AsyncSession):
    """Seed test doctor, patient, prescription, and inpatient bed."""
    # 1. Doctor
    doc_user = User(
        email="dr.chatterjee@aihos.org",
        hashed_password=get_password_hash("password123"),
        full_name="Dr. Sourav Chatterjee",
        role=UserRole.DOCTOR,
        is_active=True,
    )
    db_session.add(doc_user)
    await db_session.flush()

    doctor = Doctor(
        user_id=doc_user.user_id,
        license_number="NMC-DL-2026-90412",
        specialty="Internal Medicine & Pulmonology",
        full_name="Dr. Sourav Chatterjee",
        email="dr.chatterjee@aihos.org",
    )
    db_session.add(doctor)

    # 2. Patient
    pat_user = User(
        email="ananya.sharma@test.com",
        hashed_password=get_password_hash("password123"),
        full_name="Ananya Sharma",
        role=UserRole.PATIENT,
        is_active=True,
    )
    db_session.add(pat_user)
    await db_session.flush()

    patient = Patient(
        user_id=pat_user.user_id,
        full_name="Ananya Sharma",
        gender="female",
        phone="+919810012345",
        abha_address="ananya.sharma@abdm",
    )
    db_session.add(patient)
    await db_session.flush()

    # 3. Prescription
    prescription = Prescription(
        patient_id=patient.patient_id,
        doctor_id=doctor.doctor_id,
        status=PrescriptionStatus.FINALIZED,
        medications=[
            {
                "name": "Amoxicillin Clavulanate",
                "form": "Tablet",
                "dose": "625mg",
                "route": "Oral",
                "frequency": "Twice daily (BD)",
                "duration": "7 days",
                "instructions": "Take after meals with water",
            },
            {
                "name": "Paracetamol",
                "form": "Tablet",
                "dose": "650mg",
                "route": "Oral",
                "frequency": "SOS (As needed)",
                "duration": "3 days",
                "instructions": "Max 3 tabs/day for fever",
            },
        ],
        notes="Complete the full 7-day antibiotic course even if symptoms resolve.",
        finalized_at=datetime.now(timezone.utc),
    )
    db_session.add(prescription)

    # 4. Inpatient Bed
    bed = InpatientBed(
        bed_number="ICU-04",
        ward="Critical Care Unit",
        status="occupied",
        clinical_status="Stable",
        patient_id=patient.patient_id,
        patient_name="Ananya Sharma",
        uhid=str(patient.patient_id)[:10],
        age=34,
        gender="female",
        admitted_for="Acute Community-Acquired Lobar Pneumonia",
        attending_physician="Dr. Sourav Chatterjee",
        admit_day=3,
        diet="High Protein Soft Diet",
        allergies=["Penicillin (Mild Rash)"],
        code_status="Full Code",
        bp="118/76",
        systolic=118,
        diastolic=76,
        pulse=76,
        spo2=98,
        temp=98.8,
        respiratory_rate=16,
    )
    db_session.add(bed)
    await db_session.flush()

    # 5. Bed Vitals Log
    vital = BedVitalsLog(
        bed_id=bed.bed_id,
        patient_id=patient.patient_id,
        bp="118/76",
        systolic=118,
        diastolic=76,
        pulse=76,
        spo2=98,
        temp=98.8,
        respiratory_rate=16,
        status="stable",
        recorded_by="Nurse Pooja",
        notes="Patient resting comfortably on room air.",
    )
    db_session.add(vital)

    # 6. Nurse Task
    task = NurseTask(
        bed_id=bed.bed_id,
        patient_id=patient.patient_id,
        patient_name="Ananya Sharma",
        bed_number="ICU-04",
        ward="Critical Care Unit",
        medication="IV Ceftriaxone 1g",
        dose="1g",
        route="IV",
        due_time="14:00",
        status="administered",
    )
    db_session.add(task)
    await db_session.commit()

    return {
        "doctor": doctor,
        "doc_user": doc_user,
        "patient": patient,
        "pat_user": pat_user,
        "prescription": prescription,
        "bed": bed,
        "vital": vital,
        "task": task,
    }


# ─── 1. Unit Tests: FHIR Schema Validator ─────────────────────────────────────

def test_fhir_validator_valid_patient():
    patient_json = {
        "resourceType": "Patient",
        "id": "pat-001",
        "active": True,
        "name": [{"use": "official", "text": "Rajesh Kumar", "family": "Kumar", "given": ["Rajesh"]}],
        "gender": "male",
        "birthDate": "1980-05-15",
        "telecom": [{"system": "phone", "value": "+919876543210", "use": "mobile"}],
    }
    result = FHIRValidator.validate_resource(patient_json)
    assert result.is_valid is True
    assert result.resource_type == "Patient"
    assert len(result.errors) == 0


def test_fhir_validator_invalid_patient():
    # Invalid gender code and bad payload
    invalid_patient = {
        "resourceType": "Patient",
        "id": "pat-002",
        "gender": "not-a-valid-gender",
    }
    result = FHIRValidator.validate_resource(invalid_patient)
    assert result.is_valid is False
    assert any("gender" in err for err in result.errors)


def test_fhir_validator_medication_request():
    med_req = {
        "resourceType": "MedicationRequest",
        "id": "rx-001",
        "status": "active",
        "intent": "order",
        "medicationCodeableConcept": {
            "coding": [{"system": "http://www.nlm.nih.gov/research/umls/rxnorm", "code": "866514", "display": "Amoxicillin 500mg"}],
            "text": "Amoxicillin 500mg",
        },
        "subject": {"reference": "Patient/pat-001"},
    }
    result = FHIRValidator.validate_resource(med_req)
    assert result.is_valid is True

    # Missing medication
    bad_med = {
        "resourceType": "MedicationRequest",
        "id": "rx-bad",
        "status": "active",
        "intent": "order",
        "subject": {"reference": "Patient/pat-001"},
    }
    bad_res = FHIRValidator.validate_resource(bad_med)
    assert bad_res.is_valid is False


def test_fhir_validator_encounter_and_observation():
    encounter = {
        "resourceType": "Encounter",
        "id": "enc-001",
        "status": "in-progress",
        "class": {"system": "http://terminology.hl7.org/CodeSystem/v3-ActCode", "code": "IMP", "display": "inpatient"},
        "subject": {"reference": "Patient/pat-001"},
    }
    assert FHIRValidator.validate_resource(encounter).is_valid is True

    observation = {
        "resourceType": "Observation",
        "id": "obs-001",
        "status": "final",
        "code": {"coding": [{"system": "http://loinc.org", "code": "85354-9", "display": "Blood Pressure Panel"}]},
        "subject": {"reference": "Patient/pat-001"},
        "component": [
            {
                "code": {"coding": [{"system": "http://loinc.org", "code": "8480-6"}]},
                "valueQuantity": {"value": 120.0, "unit": "mmHg"},
            }
        ],
    }
    assert FHIRValidator.validate_resource(observation).is_valid is True


# ─── 2. Discharge Summary Composition & Document Bundle ──────────────────────

@pytest.mark.asyncio
async def test_discharge_summary_fhir_composition_and_bundle(horizon_e_test_data):
    data = horizon_e_test_data
    patient = data["patient"]
    bed = data["bed"]
    doctor = data["doctor"]
    vital = data["vital"]
    task = data["task"]
    prescription = data["prescription"]

    # 1. Observation from vitals
    obs = to_fhir_observation(vital, patient=patient)
    assert obs["resourceType"] == "Observation"
    obs_val = FHIRValidator.validate_resource(obs)
    assert obs_val.is_valid is True

    # 2. Encounter from bed
    enc = to_fhir_encounter(bed, patient=patient, doctor=doctor)
    assert enc["resourceType"] == "Encounter"
    enc_val = FHIRValidator.validate_resource(enc)
    assert enc_val.is_valid is True

    # 3. Composition
    comp = to_fhir_composition(
        patient=patient,
        bed=bed,
        vitals_logs=[vital],
        nurse_tasks=[task],
        prescriptions=[prescription],
        doctor=doctor,
    )
    assert comp["resourceType"] == "Composition"
    assert comp["type"]["coding"][0]["code"] == "18842-5"  # LOINC Discharge summary
    assert len(comp["section"]) >= 5

    comp_val = FHIRValidator.validate_resource(comp)
    assert comp_val.is_valid is True

    # 4. Document Bundle ($everything discharge)
    doc_bundle = to_fhir_discharge_bundle(
        patient=patient,
        bed=bed,
        vitals_logs=[vital],
        nurse_tasks=[task],
        prescriptions=[prescription],
        doctor=doctor,
    )
    assert doc_bundle["resourceType"] == "Bundle"
    assert doc_bundle["type"] == "document"
    assert doc_bundle["entry"][0]["resource"]["resourceType"] == "Composition"

    bundle_val = FHIRValidator.validate_bundle(doc_bundle)
    assert bundle_val.is_valid is True
    assert len(bundle_val.errors) == 0


# ─── 3. Cryptographic Signed PDF Engine ───────────────────────────────────────

def test_canonical_digest_and_digital_signature():
    payload = {
        "prescription_id": "RX-12345678",
        "patient_uhid": "UHID-9876",
        "doctor_license": "NMC-DL-2026-90412",
        "medications": [{"name": "Amoxicillin", "dose": "500mg"}],
    }
    digest = generate_canonical_clinical_digest(payload)
    assert len(digest) == 64  # SHA-256 hex string

    sig = create_institutional_digital_signature(digest)
    assert sig.startswith("SIG-AIHOS-")

    # Verification passes
    assert verify_clinical_document_signature(payload, sig) is True

    # Tampering fails verification
    tampered_payload = dict(payload)
    tampered_payload["medications"] = [{"name": "Amoxicillin", "dose": "1000mg"}]
    assert verify_clinical_document_signature(tampered_payload, sig) is False


def test_signed_prescription_pdf_generation():
    prescription = {
        "prescription_id": str(uuid4()),
        "medications": [
            {
                "name": "Azithromycin",
                "dose": "500mg",
                "route": "Oral",
                "frequency": "Once daily (OD)",
                "duration": "3 days",
                "instructions": "Take before food",
            }
        ],
        "notes": "Hydrate well and avoid direct sun exposure.",
    }
    patient = {
        "patient_id": str(uuid4()),
        "full_name": "Rohan Mehra",
        "gender": "Male",
        "age": 29,
        "abha_address": "rohan.mehra@abdm",
    }
    doctor = {
        "doctor_id": str(uuid4()),
        "full_name": "Dr. Elena Rostova",
        "license_number": "NMC-2026-102",
        "specialty": "Infectious Disease",
    }

    pdf_bytes = generate_signed_prescription_pdf(prescription, patient, doctor)
    assert isinstance(pdf_bytes, bytes)
    assert pdf_bytes.startswith(b"%PDF-")
    assert len(pdf_bytes) > 2000

    # Tamper check inspection
    tamper_report = verify_pdf_bytes_tamper(pdf_bytes)
    assert tamper_report["is_valid_pdf"] is True
    assert tamper_report["has_digital_signature_stamp"] is True
    assert tamper_report["tamper_status"] == "VERIFIED"


def test_signed_discharge_summary_pdf_generation():
    patient = {
        "patient_id": str(uuid4()),
        "full_name": "Ananya Sharma",
        "gender": "Female",
        "abha_address": "ananya.sharma@abdm",
    }
    bed = {
        "bed_id": str(uuid4()),
        "bed_number": "ICU-04",
        "ward": "Critical Care Unit",
        "age": 34,
        "gender": "Female",
        "admitted_for": "Severe Bronchial Asthma Exacerbation",
        "clinical_status": "Stable",
        "code_status": "Full Code",
        "diet": "Regular Diet",
        "admit_day": 4,
    }
    doctor = {
        "full_name": "Dr. Sourav Chatterjee",
        "license_number": "NMC-DL-2026-90412",
        "specialty": "Pulmonology & Critical Care",
    }
    vitals = [
        {"bp": "120/80", "pulse": 72, "spo2": 99, "temp": 98.4, "respiratory_rate": 16, "status": "stable"}
    ]

    pdf_bytes = generate_signed_discharge_summary_pdf(patient, bed, doctor, vitals_logs=vitals)
    assert isinstance(pdf_bytes, bytes)
    assert pdf_bytes.startswith(b"%PDF-")
    assert len(pdf_bytes) > 2500

    tamper_report = verify_pdf_bytes_tamper(pdf_bytes)
    assert tamper_report["is_valid_pdf"] is True
    assert tamper_report["tamper_status"] == "VERIFIED"


# ─── 4. REST API Endpoint Tests ───────────────────────────────────────────────

@pytest.mark.asyncio
async def test_api_fhir_validate_endpoint(client: AsyncClient, horizon_e_test_data):
    doc_user = horizon_e_test_data["doc_user"]
    token = create_access_token({"sub": doc_user.email, "role": doc_user.role.value})
    auth_headers = {"Authorization": f"Bearer {token}"}

    # 1. Valid resource
    valid_payload = {
        "resource": {
            "resourceType": "Patient",
            "id": "pat-100",
            "gender": "female",
            "name": [{"text": "Priya Singh"}],
        }
    }
    res = await client.post("/api/v1/clinical-documents/fhir/validate", json=valid_payload, headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["isValid"] is True
    assert data["operationOutcome"]["resourceType"] == "OperationOutcome"

    # 2. Direct /api/v1/fhir/validate endpoint
    res2 = await client.post("/api/v1/fhir/validate", json=valid_payload["resource"], headers=auth_headers)
    assert res2.status_code == 200
    assert res2.json()["isValid"] is True


@pytest.mark.asyncio
async def test_api_discharge_summary_fhir_bundle(client: AsyncClient, horizon_e_test_data):
    doc_user = horizon_e_test_data["doc_user"]
    bed = horizon_e_test_data["bed"]
    token = create_access_token({"sub": doc_user.email, "role": doc_user.role.value})
    auth_headers = {"Authorization": f"Bearer {token}"}

    res = await client.get(f"/api/v1/clinical-documents/fhir/discharge-summary/bed/{bed.bed_id}", headers=auth_headers)
    assert res.status_code == 200
    bundle = res.json()
    assert bundle["resourceType"] == "Bundle"
    assert bundle["type"] == "document"
    assert bundle["entry"][0]["resource"]["resourceType"] == "Composition"


@pytest.mark.asyncio
async def test_api_signed_prescription_pdf_stream(client: AsyncClient, horizon_e_test_data):
    doc_user = horizon_e_test_data["doc_user"]
    rx = horizon_e_test_data["prescription"]
    token = create_access_token({"sub": doc_user.email, "role": doc_user.role.value})
    auth_headers = {"Authorization": f"Bearer {token}"}

    res = await client.get(f"/api/v1/clinical-documents/prescription/{rx.prescription_id}/pdf", headers=auth_headers)
    assert res.status_code == 200
    assert res.headers["content-type"] == "application/pdf"
    assert res.content.startswith(b"%PDF-")


@pytest.mark.asyncio
async def test_api_signed_discharge_summary_pdf_stream(client: AsyncClient, horizon_e_test_data):
    doc_user = horizon_e_test_data["doc_user"]
    bed = horizon_e_test_data["bed"]
    token = create_access_token({"sub": doc_user.email, "role": doc_user.role.value})
    auth_headers = {"Authorization": f"Bearer {token}"}

    res = await client.get(f"/api/v1/clinical-documents/discharge-summary/bed/{bed.bed_id}/pdf", headers=auth_headers)
    assert res.status_code == 200
    assert res.headers["content-type"] == "application/pdf"
    assert res.content.startswith(b"%PDF-")


@pytest.mark.asyncio
async def test_api_signature_verification_endpoint(client: AsyncClient):
    payload = {"patient": "UHID-100", "rx": "RX-200", "ts": "2026-10-05T12:00:00Z"}
    digest = generate_canonical_clinical_digest(payload)
    sig = create_institutional_digital_signature(digest)

    # 1. Valid Signature
    res = await client.post("/api/v1/clinical-documents/verify-signature", json={"signature": sig, "payload": payload})
    assert res.status_code == 200
    data = res.json()
    assert data["is_valid"] is True
    assert data["verification_status"] == "AUTHENTIC_AND_VERIFIED"

    # 2. Tampered Payload
    tampered = dict(payload)
    tampered["rx"] = "RX-TAMPERED-999"
    res_bad = await client.post("/api/v1/clinical-documents/verify-signature", json={"signature": sig, "payload": tampered})
    assert res_bad.status_code == 200
    assert res_bad.json()["is_valid"] is False
    assert res_bad.json()["verification_status"] == "SIGNATURE_MISMATCH_OR_TAMPERED"
