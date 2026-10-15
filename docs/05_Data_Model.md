# AI-HOS Data Models & Database Schema

## 1. Relational Entity Overview

The AI-HOS database schema is declared with SQLAlchemy 2.0 Async declarative models in `backend/app/models/__init__.py`. All primary keys use RFC 4122 Version 4 UUIDs.

```
       ┌───────────────────┐
       │   organizations   │
       └─────────┬─────────┘
                 │ 1:N
 ┌───────────────┼───────────────┬────────────────┬──────────────┐
 │               │               │                │              │
┌▼────────┐    ┌─▼───────┐    ┌──▼─────────┐    ┌─▼─────────┐ ┌──▼────────┐
│  users  │    │ doctors │    │  patients  │    │  claims   │ │ audit_logs│
└────┬────┘    └────┬────┘    └─────┬──────┘    └───────────┘ └───────────┘
     │ 1:1          │ 1:N           │ 1:N
     └──────────────┼───────────────┘
                    │
           ┌────────┴────────┬──────────────────┐
           │                 │                  │
    ┌──────▼───────┐  ┌──────▼────────┐  ┌──────▼────────┐
    │ appointments │  │medical_records│  │ prescriptions │
    └──────────────┘  └───────────────┘  └───────────────┘
```

---

## 2. Core Entities & Schema Reference

### 2.1 `organizations`
Represents an isolated hospital network, diagnostic clinic, or medical department.
- `organization_id` (`UUID`, PK): Unique tenant identifier.
- `name` (`VARCHAR(255)`): Hospital or clinic name.
- `slug` (`VARCHAR(100)`, Unique): Tenant routing slug.
- `is_active` (`BOOLEAN`): Active tenant status.

### 2.2 `users`
System user account representing doctors, nurses, administrators, and registered patients.
- `user_id` (`UUID`, PK)
- `email` (`VARCHAR(255)`, Unique, Index)
- `hashed_password` (`VARCHAR(255)`): Argon2id / bcrypt digest.
- `role` (`ENUM`): `ADMIN`, `HEAD_PHYSICIAN`, `DOCTOR`, `NURSE`, `PATIENT`.
- `organization_id` (`UUID`, FK `organizations.organization_id`, Index, Nullable)

### 2.3 `doctors`
Practitioner clinical profile.
- `doctor_id` (`UUID`, PK)
- `user_id` (`UUID`, FK `users.user_id`, Unique)
- `full_name` (`VARCHAR(255)`): Attending doctor's name.
- `license_number` (`VARCHAR(100)`, Unique): Medical council registration.
- `specialty` (`VARCHAR(100)`): Clinical specialty.
- `hospital_affiliation` (`VARCHAR(255)`): Clinic/department assignment.
- `organization_id` (`UUID`, FK `organizations.organization_id`, Index, Nullable)

### 2.4 `patients`
Patient demographic and national ABHA identity profile.
- `patient_id` (`UUID`, PK)
- `user_id` (`UUID`, FK `users.user_id`, Unique, Nullable)
- `full_name` (`VARCHAR(255)`): Patient's legal name.
- `date_of_birth` (`DATE`): Date of birth for age resolution.
- `gender` (`VARCHAR(20)`): Gender designation.
- `phone` (`VARCHAR(20)`): Contact telephone.
- `abha_number` (`VARCHAR(20)`, Index, Nullable): 14-digit national ABHA ID.
- `abha_address` (`VARCHAR(100)`, Index, Nullable): ABHA handle (`name@abdm`).
- `organization_id` (`UUID`, FK `organizations.organization_id`, Index, Nullable)

### 2.5 `appointments`
Outpatient visit or virtual telehealth encounter slot.
- `appointment_id` (`UUID`, PK)
- `patient_id` (`UUID`, FK `patients.patient_id`, Index)
- `doctor_id` (`UUID`, FK `doctors.doctor_id`, Index)
- `scheduled_at` (`DATETIME`, Index): Slot start time.
- `duration_minutes` (`INTEGER`, Default `30`): Appointment duration.
- `status` (`ENUM`): `SCHEDULED`, `COMPLETED`, `CANCELLED`, `NO_SHOW`.
- `reason` (`VARCHAR(500)`, Nullable): Visit reason or chief complaint.
- `notes` (`TEXT`, Nullable): Preliminary notes or intake summary.
- `telehealth_room_id` (`VARCHAR(100)`, Index, Nullable): Telehealth room identifier.
- `meeting_link` (`VARCHAR(500)`, Nullable): Virtual consultation URL.
- `organization_id` (`UUID`, FK `organizations.organization_id`, Index, Nullable)

### 2.6 `medical_records` (Clinical SOAP Encounter)
- `record_id` (`UUID`, PK)
- `patient_id` (`UUID`, FK `patients.patient_id`, Index)
- `doctor_id` (`UUID`, FK `doctors.doctor_id`, Index)
- `encounter_date` (`DATETIME`, Index)
- `subjective` (`TEXT`): Patient-reported symptoms and history.
- `objective` (`TEXT`): Clinical examination observations and vitals.
- `assessment` (`TEXT`): Diagnoses and differential considerations.
- `plan` (`TEXT`): Diagnostic orders, therapeutics, and follow-up.
- `signed_by_doctor_id` (`UUID`, FK `doctors.doctor_id`, Nullable): Attending physician sign-off.
- `signed_at` (`DATETIME`, Nullable): Tamper-evident sign-off timestamp.
- `record_hash` (`VARCHAR(64)`, Nullable): SHA-256 cryptographic integrity hash.
- `organization_id` (`UUID`, FK `organizations.organization_id`, Index, Nullable)

### 2.7 `prescriptions`
- `prescription_id` (`UUID`, PK)
- `appointment_id` (`UUID`, FK `appointments.appointment_id`, Nullable)
- `patient_id` (`UUID`, FK `patients.patient_id`, Index)
- `doctor_id` (`UUID`, FK `doctors.doctor_id`, Index)
- `medications` (`JSONB` / `JSON`): Structured array of medication items (drug, dosage, frequency, route, duration).
- `instructions` (`TEXT`, Nullable): Patient administration advice.
- `status` (`VARCHAR(50)`): `DRAFT`, `SIGNED`, `DISPENSED`, `CANCELLED`.
- `organization_id` (`UUID`, FK `organizations.organization_id`, Index, Nullable)

### 2.8 `claims` (NHCX Insurance Integration)
- `claim_id` (`UUID`, PK)
- `claim_number` (`VARCHAR(50)`, Unique, Index)
- `patient_id` (`UUID`, FK `patients.patient_id`, Index)
- `hospital_id` (`VARCHAR(100)`)
- `insurer_id` (`VARCHAR(100)`)
- `policy_number` (`VARCHAR(100)`)
- `claim_type` (`ENUM`): `PRE_AUTH`, `SETTLEMENT`, `REIMBURSEMENT`.
- `total_claimed_amount` (`NUMERIC(12, 2)`)
- `approved_amount` (`NUMERIC(12, 2)`, Default `0.00`)
- `status` (`ENUM`): `SUBMITTED`, `ACKNOWLEDGED`, `PENDING_REVIEW`, `APPROVED`, `REJECTED`, `SETTLED`.
- `organization_id` (`UUID`, FK `organizations.organization_id`, Index, Nullable)