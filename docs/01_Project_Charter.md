# Project Charter — AI-HOS

## Vision
AI-HOS (AI Healthcare Operating System) is an AI-powered platform connecting hospitals, clinics, doctors, and patients in one ecosystem. It is an intelligent assistant, NOT a diagnostic authority — a licensed clinician stays in control of every clinical decision.

## MVP Scope
- AI Receptionist (voice intake)
- AI Triage (symptom collection + department recommendation)
- Appointment Booking
- Doctor Dashboard (AI Copilot, voice notes, medical scribe, prescription draft)
- Multilingual Voice Support

## Out of Scope for MVP
- Wearables
- Insurance/claims automation beyond basic billing
- Predictive analytics
- Digital-twin modeling

## Build Order
Get the Doctor Copilot vertical (ambient scribe + prescription draft) fully working end-to-end as the first pilot slice before completing the Patient and Admin apps.

## Architecture (Five Layers)
1. **Client Layer**: Three separate apps — Patient (web+voice), Doctor (dense dashboard), Admin (ops/analytics)
2. **Gateway Layer**: Single API gateway — auth, routing, TLS termination only
3. **Service Layer** (deterministic, testable):
   - Auth service: RBAC + consent management
   - Core API: Sole writer of clinical truth to PostgreSQL
   - Integration service: FHIR/ABDM/HIE
   - Orchestrator: Routes work to AI agents with timeouts, retries, fallback-to-human
4. **Agent Layer** (generative, non-deterministic):
   - Intake & triage: symptom capture, urgency detection, routing
   - Doctor copilot: ambient scribing + prescription drafting
   - Ops & follow-up: reminders, follow-up messaging, admin record summaries
5. **Data Layer**: PostgreSQL (system of record), Redis (session/cache only), ABDM/FHIR HIE (external)

## Compliance Context
- India: DPDP Act 2023; ABDM ecosystem (ABHA IDs, Consent Manager, HIE, HFR/HPR)
- HIPAA Privacy/Security Rules (if U.S. patient data processed)
- HL7 FHIR R4 as canonical interoperability format
- Data residency: production data should be able to be hosted in-region

## Non-Functional Targets
- API P95 latency < 500ms for non-AI endpoints; AI conversational turn < 3s
- 99.9% uptime target for patient-facing services
- Multi-tenant data isolation per hospital/clinic
- WCAG 2.1 AA for patient-facing interfaces
- Defined code coverage target; automated CI/CD; isolated dev/staging/prod