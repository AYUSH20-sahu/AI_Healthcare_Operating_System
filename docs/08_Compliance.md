# Compliance — AI-HOS

## Regulatory Frameworks

### India
- **DPDP Act 2023** (Digital Personal Data Protection)
- **ABDM Ecosystem**:
  - ABHA IDs (tokenized, not raw national IDs)
  - Consent Manager
  - Health Information Exchange (HIE)
  - HFR (Health Facility Registry)
  - HPR (Healthcare Professional Registry)

### International
- **HIPAA** Privacy/Security Rules (if U.S. patient data processed)
- **HL7 FHIR R4** as canonical interoperability format

## Data Protection
- **In Transit**: TLS 1.2+
- **At Rest**: AES-256
- **National IDs**: Never stored raw — use tokenized ABHA addresses
- **Secrets**: Never in source control — environment variables / secrets manager

## Audit Logging
- Compliance audit logging (audit_logs table) separate from observability logging
- Every access to patient/health data logged: who, what resource, when, outcome
- Different retention rules for compliance vs. observability logs

## Data Residency
- Production data must be able to be hosted in-region