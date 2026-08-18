# Auth, RBAC, Consent — AI-HOS

## Authentication
- JWT-based (access + refresh tokens)
- Password hashing: bcrypt/argon2
- Signup and login endpoints

## RBAC (Role-Based Access Control)
Roles:
- patient
- doctor
- admin
- nurse
- receptionist

Implementation:
- Central permissions matrix (module x role) as configuration
- `require_role` dependency/decorator for FastAPI routes
- No scattered if-checks

## Consent Management
- Consent is a first-class, auditable object (not a login side-effect)
- Endpoints:
  - POST /consents — grant consent
  - DELETE /consents/{id} — revoke consent
  - GET /patients/{id}/consents — list active consents
- Fields: consent_id, patient_id, provider_id, record_scope, granted_at, revoked_at

## Compliance Audit Logging
- Separate from general application observability/error logging
- Automatic middleware records every read/write of patient/health data
- Fields: log_id, user_id, action, resource_type, resource_id, timestamp, outcome
- Different retention rules than general logging