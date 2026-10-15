# AI-HOS Security, RBAC & Consent Management

## 1. Authentication Architecture

AI-HOS implements standard stateless JWT (JSON Web Token) bearer authentication.

- **Token Signing**: Signed with HMAC-SHA256 (`HS256`).
- **Secret Key Rotation**: Injected via `SECRET_KEY` environment variable.
- **Expiration Policy**:
  - Access Token: Default 60 minutes.
  - Refresh Token: Default 7 days.
- **Password Hashing**: Dual Argon2id / bcrypt verification via `passlib.context.CryptContext`.

---

## 2. Role-Based Access Control (RBAC) Matrix

The platform strictly segregates user permissions via the `UserRole` enumeration:

| Resource / Action | ADMIN | HEAD_PHYSICIAN | DOCTOR | NURSE | PATIENT |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Manage Organizations & System Settings** | ✅ | ❌ | ❌ | ❌ | ❌ |
| **Provision & Deactivate Staff Users** | ✅ | ❌ | ❌ | ❌ | ❌ |
| **View Audit Logs & System Metrics** | ✅ | ✅ (Dept) | ❌ | ❌ | ❌ |
| **Create & Sign SOAP Clinical Notes** | ❌ | ✅ | ✅ | ❌ | ❌ |
| **Issue Electronic Prescriptions** | ❌ | ✅ | ✅ | ❌ | ❌ |
| **Conduct Doctor Telehealth Sessions** | ✅ (Supervise) | ✅ | ✅ | ❌ | ❌ |
| **Join Patient Consultation Room** | ✅ (QA) | ❌ | ❌ | ❌ | ✅ (Self) |
| **Record Inpatient Vitals & Triage** | ❌ | ✅ | ✅ | ✅ | ❌ |
| **Book Appointments** | ✅ | ❌ | ❌ | ✅ | ✅ |
| **View Own Medical Records & Rx** | ❌ | ❌ | ❌ | ❌ | ✅ (Self) |
| **Submit NHCX Insurance Claims** | ✅ | ❌ | ❌ | ❌ | ❌ |

---

## 3. ABDM Consent Artefact Lifecycle

Under the Ayushman Bharat Digital Mission (ABDM), patient health records cannot be accessed across different facilities without an explicit, cryptographically verifiable consent artefact.

```
[ HIU: Hospital ]            [ ABDM Gateway ]              [ Patient App ]
       │                            │                             │
       │─── 1. Consent Request ────▶│                             │
       │                            │─── 2. Push Notification ───▶│
       │                            │                             │
       │                            │◀── 3. Patient Approves ─────│
       │◀── 4. Consent Artefact ────│                             │
       │                            │                             │
       │─── 5. Request Data (HIP) ─▶│                             │
       │◀── 6. Encrypted FHIR Bundle│                             │
```

- **Consent Statuses**: `REQUESTED`, `GRANTED`, `REVOKED`, `EXPIRED`.
- **Granular Scoping**: Consent defines exact date range, record types (Prescription, DiagnosticReport, DischargeSummary), and purpose of access.

---

## 4. Tamper-Evident Audit Logging

All security-sensitive operations are appended to the `audit_logs` table:
- Captured attributes: `timestamp`, `user_id`, `organization_id`, `action`, `resource_type`, `resource_id`, `ip_address`, `user_agent`.
- Cryptographic hash chaining: Each signed clinical encounter calculates a SHA-256 digest over `patient_id + doctor_id + encounter_date + subjective + objective + assessment + plan`. Any downstream modification invalidates the integrity hash.