# AI-HOS Clinical AI Agents & Workflows

## 1. Overview of Assistive AI Agents

AI-HOS integrates specialized assistive AI agents designed to automate clinical documentation, symptom extraction, and patient safety checks. All agents operate strictly under **Human-in-the-Loop (HITL)** governance.

```
       ┌────────────────────────────────────────────────────────┐
       │             AI-HOS ASSISTIVE AI AGENTS                 │
       ├─────────────────┬────────────────────┬─────────────────┤
       │ Ambient Scribe  │  Clinical Copilot  │  Safety & Triage │
       ├─────────────────┼────────────────────┼─────────────────┤
       │• Audio pipeline │• Real-time SOAP    │• Drug-Drug Alert│
       │• Transcription  │• ICD-10 Code hints │• Allergy Checks │
       │• Structured SOAP│• Diff. Diagnoses   │• Red Flag Alerts│
       │• Draft Rx items │• Follow-up Recs    │• Intake Triage  │
       └─────────────────┴────────────────────┴─────────────────┘
                                   │
                     ┌─────────────▼─────────────┐
                     │ Human-in-the-Loop Review  │
                     │  (Attending Doctor Sign)  │
                     └───────────────────────────┘
```

---

## 2. Specialized Clinical Agents

### 2.1 Ambient Clinical Scribe
- **Endpoint**: `/api/v1/voice-notes/`, `/api/v1/doctors/scribe`
- **Function**: Processes physician-patient audio recordings into structured medical documentation.
- **Output Schema**:
  - `subjective`: Patient's history of present illness (HPI) and symptoms.
  - `objective`: Documented vital signs and physical exam findings.
  - `assessment`: Primary clinical impression and ICD-10 suggestions.
  - `plan`: Medications, diagnostic lab orders, and dietary/activity advice.
- **Drafting Workflow**: The scribe populates an editable draft in the Doctor Consultation Copilot. The physician retains complete editorial control before signing.

### 2.2 Clinical Copilot & Differential Diagnosis
- **Endpoint**: `/api/v1/copilot/differential`, `/api/v1/copilot/icd10`
- **Function**: Analyzes patient age, gender, chronic history, and acute symptoms to produce differential diagnostic considerations ranked by likelihood and clinical urgency.
- **Safety Rule**: Suggestions are presented with confidence badges and must never automatically update permanent diagnoses without doctor confirmation.

### 2.3 Drug Interaction & Allergy Contraindication Checker
- **Module**: `backend/app/services/drug_safety.py`
- **Function**: Automatically invoked whenever medications are added to an electronic prescription draft.
- **Check Dimensions**:
  1. **Drug-Drug Interactions (DDI)**: High-risk contraindications (e.g. Sildenafil + Nitrates, SSRIs + MAOIs, Warfarin + NSAIDs).
  2. **Drug-Allergy Contraindications**: Cross-referencing patient documented allergies (e.g. Penicillin allergy vs. Amoxicillin prescription).
  3. **Dosage & Route Sanity**: Verification of frequency (`OD`, `BD`, `TDS`, `QID`, `PRN`).

### 2.4 Patient Voice & Chat Triage Intake
- **Endpoint**: `/api/v1/patient/intake`, `/api/v1/patient/login`
- **Function**: Conversational concierge assisting patients prior to consultation.
- **Safety Logic**:
  - Extracts chief complaint, symptom duration, and severity score (1–10).
  - Evaluates for critical red flags (chest pain, acute dyspnea, stroke signs, severe hemorrhage).
  - When red flags are triggered, the agent immediately displays emergency directives (call 112 / visit nearest emergency department) and blocks regular outpatient self-booking.

---

## 3. Human-in-the-Loop (HITL) Medical Safeguards

1. **Explicit Doctor Sign-Off**: No AI-generated SOAP note or prescription is persisted into the patient's legal electronic health record without the attending doctor's digital signature (`signed_by_doctor_id`, `signed_at`).
2. **Deterministic Cryptographic Hashing**: Every approved encounter note computes a SHA-256 hash. Any subsequent alteration creates a mismatch against audit records.
3. **Auditability**: All AI prompts and generated suggestions are logged with session IDs to maintain clinical accountability.