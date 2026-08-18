# Architecture — AI-HOS

## Five-Layer Architecture

### Layer 1: Client Layer
Three separate applications:
- **Patient App** (web + voice) — `/patient`
- **Doctor App** (dense dashboard) — `/doctor`
- **Admin App** (ops/analytics) — `/admin`

### Layer 2: Gateway Layer
Single API Gateway:
- Authentication
- Routing
- TLS termination
- **No business logic**

### Layer 3: Service Layer (Deterministic, Testable)
- **Auth Service**: RBAC + consent management (consent is a first-class, auditable object)
- **Core API**: Sole writer of clinical truth (patients, appointments, medical records, prescriptions) to PostgreSQL
- **Integration Service**: FHIR/ABDM/HIE — isolated so external standards churn never destabilizes core logic
- **Orchestrator**: Only thing allowed to route work to AI agents; applies timeouts, retries, fallback-to-human

### Layer 4: Agent Layer (Generative, Non-Deterministic)
Three scoped groups:
- **Intake & Triage**: Symptom capture, urgency detection, routing — never diagnoses or prescribes
- **Doctor Copilot**: Ambient scribing + prescription drafting — outputs are always drafts
- **Ops & Follow-up**: Reminders, follow-up messaging, admin record summaries

### Layer 5: Data Layer
- **PostgreSQL**: System of record
- **Redis**: Session/cache only, never durable clinical data
- **ABDM/FHIR HIE**: External, reached only via Integration service

## Hard Rules
- Agents NEVER write directly to PostgreSQL and NEVER call external HIE directly
- No AI-generated clinical content is ever auto-finalized — requires explicit doctor/human review
- Every AI output shown to doctor/patient carries visible basis/confidence indicator
- Emergency/red-flag symptoms bypass normal triage flow
- Every access to patient/health data is logged (audit_logs table)
- No secrets in source control — read from environment variables
- All patient data in transit uses TLS 1.2+; at rest uses AES-256
- Every external AI capability called through provider adapter (M19)