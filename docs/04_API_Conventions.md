# API Conventions — AI-HOS

## REST Conventions
- Versioned under `/api/v1`
- List endpoints: cursor or offset pagination (consistent choice, documented default and max page size)
- Standard error envelope:
  ```json
  {
    "error": {
      "code": "string",
      "message": "string",
      "details": {}
    }
  }
  ```
- Auto-generate OpenAPI docs from FastAPI (don't hand-write separate API spec)

## Database
- MVP core tables (FHIR-R4-mappable from day one):
  - patients
  - doctors
  - appointments
  - medical_records
  - prescriptions
  - audit_logs
  - consents (patient_id, provider_id, record_scope, granted_at, revoked_at)
- Full system may scale to 80-150 tables long-term
- Add short "FHIR mapping" comment/doc note per table