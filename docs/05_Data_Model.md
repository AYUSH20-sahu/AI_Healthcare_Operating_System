# Data Model — AI-HOS

## Core Tables (MVP)

### patients
- patient_id (UUID, PK)
- abha_address (tokenized, not raw national ID)
- demographics (name, dob, gender, contact)
- created_at, updated_at
- **FHIR Mapping**: Patient resource

### doctors
- doctor_id (UUID, PK)
- user_id (FK to auth users)
- specialty, license_number, hospital_affiliation
- created_at, updated_at
- **FHIR Mapping**: Practitioner resource

### appointments
- appointment_id (UUID, PK)
- patient_id (FK)
- doctor_id (FK)
- scheduled_at, duration_minutes
- status (scheduled/completed/cancelled/no-show)
- created_at, updated_at
- **FHIR Mapping**: Appointment resource

### medical_records
- record_id (UUID, PK)
- patient_id (FK)
- doctor_id (FK)
- appointment_id (FK, nullable)
- content (structured clinical data)
- status (draft/finalized)
- created_at, updated_at, finalized_at
- **FHIR Mapping**: Composition / ClinicalImpression resource

### prescriptions
- prescription_id (UUID, PK)
- medical_record_id (FK)
- patient_id (FK)
- doctor_id (FK)
- medications (structured list)
- status (draft/finalized)
- created_at, updated_at, finalized_at
- **FHIR Mapping**: MedicationRequest resource

### audit_logs
- log_id (UUID, PK)
- user_id (FK)
- action (CREATE/READ/UPDATE/DELETE)
- resource_type (string)
- resource_id (UUID)
- timestamp
- outcome (success/failure)
- **FHIR Mapping**: AuditEvent resource

### consents
- consent_id (UUID, PK)
- patient_id (FK)
- provider_id (FK)
- record_scope (string)
- granted_at
- revoked_at (nullable)
- **FHIR Mapping**: Consent resource