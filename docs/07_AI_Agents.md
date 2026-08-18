# AI Agents — AI-HOS

## Agent Groups (Three Scoped Groups)

### 1. Intake & Triage
- Symptom capture
- Urgency detection
- Department routing
- **Never** diagnoses or prescribes
- Emergency/red-flag patterns bypass normal flow → human/emergency pathway

### 2. Doctor Copilot
- Ambient scribing
- Prescription drafting
- Outputs are **always drafts** requiring explicit doctor review/approval
- Visible basis/confidence indicators on all outputs

### 3. Ops & Follow-up
- Reminders
- Follow-up messaging
- Admin record summaries

## Hard Rules for All Agents
- NEVER write directly to PostgreSQL
- NEVER call external HIE directly
- All writes go through Core API
- All external exchange goes through Integration Service
- Every AI output carries explainability (basis/confidence)
- Called through provider adapter (M19) — never direct SDK calls