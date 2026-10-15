# AI-HOS Regulatory Compliance & Healthcare Standards

## 1. Regulatory Frameworks Summary

AI-HOS is architected to satisfy national and international digital health regulatory mandates:

```
┌─────────────────────────────────────────────────────────────────┐
│               REGULATORY & STANDARDS COMPLIANCE                 │
├──────────────────────┬────────────────────┬─────────────────────┤
│      ABDM (India)    │   NHCX (Insurance) │  Data Privacy & Sec │
├──────────────────────┼────────────────────┼─────────────────────┤
│ • Milestone 1 (ABHA) │ • Pre-Authorization│ • DISHA (India)     │
│ • Milestone 2 (HIP)  │ • Claim Submission │ • HIPAA Security    │
│ • Milestone 3 (HIU)  │ • Settlement Track │ • AES-256 Storage   │
│ • HL7 FHIR-R4        │ • Query Resolution │ • SHA-256 Chaining  │
└──────────────────────┴────────────────────┴─────────────────────┘
```

---

## 2. ABDM Integration (Milestones 1, 2 & 3)

The Ayushman Bharat Digital Mission (ABDM) standards defined by the National Health Authority (NHA) are fully mapped within `backend/app/api/abdm.py` and `backend/app/services/abdm/`:

### Milestone 1: ABHA Registration & Verification
- Creation and verification of 14-digit ABHA numbers via Aadhaar or Mobile OTP.
- Mapping of patient profiles to unique ABHA addresses (`username@abdm`).

### Milestone 2: Health Information Provider (HIP)
- Hospital acts as a records repository capable of discovering patient care contexts.
- Secure bundle generation: Encrypts patient records using Diffie-Hellman key exchange and AES-GCM as specified by NHA gateway specifications.
- Transforms internal records into standard HL7 FHIR-R4 bundles (`OPConsultation`, `PrescriptionRecord`, `DischargeSummary`).

### Milestone 3: Health Information User (HIU)
- Requests patient consent for external health records.
- Processes consent approvals, initiates data transfers, and securely decrypts FHIR records for physician review during clinical encounters.

---

## 3. NHCX Insurance Claims Processing

The **National Health Claims Exchange (NHCX)** is India's centralized gateway for electronic health insurance claim adjudication.

- **Endpoint**: `/api/v1/claims/`
- **Supported Claim Lifecycles**:
  1. `PRE_AUTH`: Hospital requests cashless treatment authorization from the Third Party Administrator (TPA) / Insurer.
  2. `SETTLEMENT`: Hospital submits discharge summaries, itemized bills, and final claim documentation upon patient discharge.
  3. `REIMBURSEMENT`: Patient-initiated claim processing.
- **Status Progression**:
  `SUBMITTED` $\to$ `ACKNOWLEDGED` $\to$ `PENDING_REVIEW` $\to$ `APPROVED` | `REJECTED` $\to$ `SETTLED`.
- **Validation**: Schema enforces policy number verification, itemized cost breakdowns, ICD-10 diagnostic coding, and total claimed amount matching.

---

## 4. HL7 FHIR-R4 Implementation

Internal database models are converted to FHIR-R4 resources:
- `Patient` $\leftrightarrow$ FHIR `Patient` resource.
- `Doctor` $\leftrightarrow$ FHIR `Practitioner` resource.
- `Appointment` $\leftrightarrow$ FHIR `Appointment` / `Encounter` resource.
- `MedicalRecord` $\leftrightarrow$ FHIR `ClinicalImpression`, `Observation`, and `Condition` resources.
- `Prescription` $\leftrightarrow$ FHIR `MedicationRequest` resource.

---

## 5. Data Privacy & Security Mandates

1. **At-Rest Encryption**: Sensitive patient identifiers and encrypted consultation recordings use AES-256-GCM.
2. **In-Transit Encryption**: Strict TLS 1.3 encryption across all HTTPS endpoints and WSS WebSockets.
3. **Data Localization**: Compliant with India's Digital Personal Data Protection Act (DPDP) and DISHA guidelines requiring patient health data to remain within sovereign borders.