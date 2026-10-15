# AI-HOS Project Charter & Governance

## 1. Vision & Strategic Mission
The **AI Healthcare Operating System (AI-HOS)** is designed as an end-to-end hospital operating platform that unites patient care, physician workflows, administrative management, and national interoperability into a single modern web application.

The core objective is to drastically reduce physician administrative burden—especially manual documentation and repetitive data entry—while maintaining rigorous patient safety, strict regulatory compliance, and seamless multi-facility scaling.

---

## 2. Core Pillars

```
┌─────────────────────────────────────────────────────────────────┐
│                    AI-HOS CORE PILLARS                          │
├─────────────────┬─────────────────┬─────────────┬───────────────┤
│   Clinical AI   │   Virtual Care  │ Inter-op    │ Governance    │
│   Assistance    │   & Telehealth  │ & Standards │ & Security    │
├─────────────────┼─────────────────┼─────────────┼───────────────┤
│ • Ambient Scribe│ • WebRTC Video  │ • ABDM M1-M3│ • Multi-tenant│
│ • Copilot SOAP  │ • Coturn STUN   │ • FHIR R4   │ • RBAC Matrix │
│ • Drug Check    │ • WebSocket Rel.│ • NHCX Claim│ • Audit Logs  │
│ • HITL Approval │ • PIP Previews  │ • ABHA ID   │ • K8s Ready   │
└─────────────────┴─────────────────┴─────────────┴───────────────┘
```

1. **Clinical AI Under Human Supervision**:
   - AI draft generation for SOAP notes, prescriptions, and triage summaries is strictly assistive.
   - A qualified, licensed physician must review, modify, and officially sign every generated record before persistence into permanent patient records.
2. **Encrypted Telehealth Consultation**:
   - Zero-plugin browser WebRTC video calls connecting patients and physicians with automated ICE/STUN/TURN negotiation for traversal through hospital firewalls.
3. **National Health Interoperability (India ABDM & NHCX)**:
   - Full support for the Ayushman Bharat Digital Mission (Milestones 1, 2, and 3) allowing patients to link ABHA numbers and securely consent to record sharing.
   - National Health Claims Exchange (NHCX) claim life-cycle processing for electronic pre-authorization and reimbursement settlement.
4. **Multi-Tenancy & Operational Sovereignty**:
   - Logical multi-tenant data architecture allowing multiple hospital networks, clinics, or departments to operate securely on a single managed deployment.

---

## 3. Operational Roles & Boundaries

| Role | Operational Scope & Responsibilities |
| :--- | :--- |
| **System Administrator (`ADMIN`)** | Platform configuration, staff provisioning, organization onboarding, system health monitoring, and claim reconciliation. |
| **Head Physician (`HEAD_PHYSICIAN`)** | Clinical governance, departmental oversight, prescription protocol management, and peer review. |
| **Attending Doctor (`DOCTOR`)** | Outpatient consultations, virtual telehealth calls, clinical SOAP drafting, electronic prescriptions, and diagnostic ordering. |
| **Staff Nurse (`NURSE`)** | Inpatient ward rounds, triage intake, vital signs telemetry capture, and patient queue flow management. |
| **Patient (`PATIENT`)** | Self-service appointment booking, teleconsultation room attendance, health records access, and ABHA consent management. |

---

## 4. Architectural Boundaries

- **Assisted Decision Making, Not Autonomous Treatment**: The AI models generate diagnostic hypotheses and interaction alerts, but never execute prescriptive decisions without doctor approval.
- **Strict Data Segregation**: Every database query scoped to clinical data is filtered by `organization_id` to prevent cross-facility data leakage.
- **Standardized API Contracts**: All data exchange adheres to Pydantic v2 schemas and JSON REST conventions, with bidirectional translation to FHIR-R4.