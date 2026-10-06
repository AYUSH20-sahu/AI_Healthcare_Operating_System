# AI-HOS — AI Healthcare Operating System

## Project Description
AI-HOS is an AI-powered platform connecting hospitals, clinics, doctors, and patients in one ecosystem. It is an intelligent assistant, **NOT a diagnostic authority** — a licensed clinician stays in control of every clinical decision.

## Architecture Summary (Five Layers)

1. **Client Layer**: Three separate apps — Patient (web+voice), Doctor (dense dashboard), Admin (ops/analytics)
2. **Gateway Layer**: Single API gateway — auth, routing, TLS termination only (no business logic)
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

## Milestone Status

| Milestone | Component | Status |
|-----------|-----------|--------|
| M0 | Prerequisites | ✅ Done |
| M1 | Repo setup, Docker Compose, FastAPI, Next.js | ✅ Done |
| M2 | Database schema (PostgreSQL + SQLAlchemy + Alembic) | ✅ Done |
| M3 | Auth (JWT, RBAC, password hashing) | ✅ Done |
| M4 | Consent management | ✅ Done |
| M5 | Patient CRUD + ABHA ID | ✅ Done |
| M6 | Doctor CRUD + license verification | ✅ Done |
| M7 | Appointment scheduling | ✅ Done |
| M8 | Medical Records API (draft/finalized/amended) | ✅ Done |
| M9 | Prescriptions API (draft/finalized/cancelled) | ✅ Done |
| M10 | Voice Notes API (upload/download) | ✅ Done |
| M11 | RBAC middleware + permissions | ✅ Done |
| M12 | Audit logging | ✅ Done |
| M13 | OpenAPI docs + validation | ✅ Done |
| M14 | CI/CD pipeline | ✅ Done |
| M15 | Drug interaction checking | ✅ Done |
| M16 | FHIR mapping utilities | ✅ Done |
| M17 | Patient app shell | ✅ Done |
| M18 | Voice note capture | ✅ Done |
| **M19** | **Provider Adapter** (NVIDIA primary, Gemini fallback, Groq STT, Mock TTS) | ✅ Done |
| **M20** | **Orchestrator** (routing, retry, fallback-to-human) | ✅ Done |
| **M21** | **Scribe Agent** (voice → clinical note draft) | ✅ Done |
| **M22** | **Prescription Agent** (note → prescription + interaction warnings) | ✅ Done |
| **M23** | **Doctor Review/Approval Gate** (mandatory human-in-the-loop) | ✅ Done |
| **U-07–U-11** | **Doctor Copilot & Workflow** (Voice notes, Scribe, Rx draft, Approval gate) | ✅ Done |
| **U-12–U-16** | **Patient Portal & Operations** (Intake, Triage, Telehealth, Scheduling, Reminders) | ✅ Done |
| **U-17–U-19** | **Admin Operations & Multi-lingual** (Multi-tenant orgs, staff provisioning, audio streaming) | ✅ Done |
| **U-20–U-21** | **Healthcare Interoperability** (HL7 FHIR R4 Bundle export, ABDM & ABHA tokenization) | ✅ Done |
| **U-22–U-24** | **Observability, Security & E2E** (Telemetry, zero dummy data baseline, full system E2E) | ✅ Done |

## Local Development Setup

### Prerequisites
- Git
- Node.js LTS (v20+)
- Python 3.11+
- Docker Desktop
- VS Code with GitHub Copilot Chat (Nemotron Ultra 3)

### Quick Start
```bash
# Clone the repository
git clone <your-repo-url>
cd AI_Healthcare_Operating_System

# Copy environment template
cp .env.example .env.local
# Edit .env.local with your API keys (see Environment Variables below)

# Start development environment (M2)
docker compose up
```

### Services (M2)
- **Frontend** (Next.js + Tailwind): http://localhost:3000
- **Backend** (FastAPI): http://localhost:8000
- **API Docs** (OpenAPI): http://localhost:8000/docs
- **PostgreSQL**: Managed Cloud PostgreSQL (Nhost)
- **Redis**: localhost:6379 (with healthcheck)

### Active Test Personas & Demo Credentials

To explore and test all portals across the Five-Layer Architecture, use the credentials below:

#### 1. Core Institutional & Patient Personas
| Role & Persona | Email | Phone | Password | Access Route & Portal | Primary Capabilities |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Global Super Administrator** | `superadmin@aihos.org` | `+919999000001` | `adminpassword123` | [`/admin/organizations`](http://localhost:3000/admin/organizations) | Multi-tenant hospital onboarding wizard, facility licensing & cross-tenant governance |
| **Hospital Administrator** | `admin@test.com` | `+919876500001` | `adminpassword123` | [`/admin`](http://localhost:3000/admin) | Clinician provisioning, staff shifts, ward management & immutable audit logs |
| **Attending Doctor (Cardiology)** | `doctor@test.com` | `+919876543210` | `doctorpassword123` | [`/doctor`](http://localhost:3000/doctor) | Consultations, Telehealth, and the **Doctor Review Gate** ([`/doctor/approvals`](http://localhost:3000/doctor/approvals)) |
| **Head Inpatient Nurse** | `nurse@test.com` | `+919876500005` | `nursepassword123` | [`/nurse`](http://localhost:3000/nurse) | Inpatient bed occupancy, bedside vitals telemetry logging & shift medication rounds |
| **Registered Patient** | `patient@test.com` | `+919876511111` | `patientpassword123` | [`/patient/login`](http://localhost:3000/patient/login) | Appointment booking, ABHA health records, medicine reminders & lab diagnostic reports |

---

#### 2. Departmental Specialists (10 Doctors — 2 for Each Department)
*All departmental doctors sign in at [`/doctor`](http://localhost:3000/doctor) (or [`/auth/login`](http://localhost:3000/auth/login)) with password:* `doctorpassword123`

| Department | Clinician Name | Email | License Number | Designation & Shift |
| :--- | :--- | :--- | :--- | :--- |
| **Cardiology** | Dr. Rajesh Sharma | `doc.cardio1@aihos.org` | `MCI-CARD-2015-8849` | Head of Cardiology (Morning 09:00 - 14:00) |
| **Cardiology** | Dr. Anita Desai | `doc.cardio2@aihos.org` | `MCI-CARD-2018-7721` | Consultant Cardiologist (Afternoon 14:00 - 19:00) |
| **Neurology** | Dr. Priya Patel | `doc.neuro1@aihos.org` | `MCI-NEUR-2018-4412` | Head of Neurology (Morning 09:00 - 14:00) |
| **Neurology** | Dr. Sameer Joshi | `doc.neuro2@aihos.org` | `MCI-NEUR-2020-5519` | Consultant Neurologist (Afternoon 14:00 - 19:00) |
| **Pediatrics** | Dr. Arjun Kumar | `doc.pedia1@aihos.org` | `MCI-PEDI-2016-9031` | Lead Pediatric Specialist (Morning 09:00 - 15:00) |
| **Pediatrics** | Dr. Neha Agarwal | `doc.pedia2@aihos.org` | `MCI-PEDI-2019-3824` | Consultant Pediatrician & Neonatologist (Afternoon) |
| **Orthopedics** | Dr. Kavya Singh | `doc.ortho1@aihos.org` | `MCI-ORTH-2014-3129` | Senior Orthopedic Surgeon (Morning 08:30 - 13:30) |
| **Orthopedics** | Dr. Rohan Mehta | `doc.ortho2@aihos.org` | `MCI-ORTH-2017-8890` | Consultant Spine & Joint Specialist (Afternoon) |
| **Dermatology** | Dr. Vikram Reddy | `doc.derm1@aihos.org` | `MCI-DERM-2015-6612` | Senior Dermatologist (Morning 09:00 - 14:00) |
| **Dermatology** | Dr. Pooja Chawla | `doc.derm2@aihos.org` | `MCI-DERM-2019-4458` | Consultant Dermatologist & Dermatosurgeon (Afternoon) |

---

#### 3. Specialized Physicians (20 Physicians across Clinical Disciplines)
*All physicians sign in at [`/doctor`](http://localhost:3000/doctor) (or [`/auth/login`](http://localhost:3000/auth/login)) with password:* `doctorpassword123`

| # | Physician Name | Email | Clinical Discipline / Specialty | License Number | Room / Location |
| :- | :--- | :--- | :--- | :--- | :--- |
| 1 | Dr. Sunita Rao | `physician1@aihos.org` | Internal Medicine (Lead Physician) | `MCI-MED-2012-7641` | Room 105 |
| 2 | Dr. Alok Verma | `physician2@aihos.org` | General Medicine | `MCI-MED-2014-1102` | Room 106 |
| 3 | Dr. Meera Nambiar | `physician3@aihos.org` | Critical Care & ICU Lead | `MCI-MED-2015-3341` | ICU Station |
| 4 | Dr. Harish Iyer | `physician4@aihos.org` | Pulmonology & Chest Medicine | `MCI-MED-2016-8921` | Room 205 |
| 5 | Dr. Divya Saxena | `physician5@aihos.org` | Gastroenterology & Hepatology | `MCI-MED-2013-4419` | Room 206 |
| 6 | Dr. Rakesh Kulkarni | `physician6@aihos.org` | Nephrology & Dialysis | `MCI-MED-2015-7728` | Dialysis Wing |
| 7 | Dr. Sangeeta Pillai | `physician7@aihos.org` | Medical Oncology | `MCI-MED-2014-9912` | Daycare Unit |
| 8 | Dr. Vivek Mathur | `physician8@aihos.org` | Endocrinology & Diabetology | `MCI-MED-2017-2234` | Room 305 |
| 9 | Dr. Ananya Sen | `physician9@aihos.org` | Rheumatology & Autoimmune Care | `MCI-MED-2018-6619` | Room 306 |
| 10 | Dr. Deepak Bhatt | `physician10@aihos.org` | Infectious Disease & Travel Health | `MCI-MED-2016-5521` | Isolation Ward |
| 11 | Dr. Shweta Ghosh | `physician11@aihos.org` | Geriatric Medicine & Elderly Care | `MCI-MED-2015-8832` | Room 405 |
| 12 | Dr. Manish Tiwari | `physician12@aihos.org` | Emergency Medicine & Trauma | `MCI-MED-2019-1192` | Trauma Bay 1 |
| 13 | Dr. Radhika Menon | `physician13@aihos.org` | Family Medicine & Primary Care | `MCI-MED-2017-3312` | OPD Desk 1 |
| 14 | Dr. Tarun Chopra | `physician14@aihos.org` | Preventive Health & Executive Wellness | `MCI-MED-2018-7744` | Health Center |
| 15 | Dr. Bhavna Shah | `physician15@aihos.org` | Clinical Hematology | `MCI-MED-2016-4481` | Room 505 |
| 16 | Dr. Nikhil Grover | `physician16@aihos.org` | Allergy & Clinical Immunology | `MCI-MED-2019-9923` | Room 506 |
| 17 | Dr. Tanvi Hegde | `physician17@aihos.org` | Palliative Care & Pain Management | `MCI-MED-2018-1123` | Hospice Wing |
| 18 | Dr. Saurabh Malhotra | `physician18@aihos.org` | General & Laparoscopic Surgery | `MCI-MED-2014-5591` | OT Complex |
| 19 | Dr. Ritu Kapoor | `physician19@aihos.org` | Clinical Pharmacology & Therapeutics | `MCI-MED-2017-6644` | Pharmacy Lab |
| 20 | Dr. Siddharth Jain | `physician20@aihos.org` | Neuro-Critical Care & Neuro-Trauma | `MCI-MED-2016-8819` | Neuro ICU |

---

#### 4. Inpatient Ward & Critical Care Nurses (20 Nurses)
*All nurses sign in at [`/nurse`](http://localhost:3000/nurse) (or [`/auth/login`](http://localhost:3000/auth/login)) with password:* `nursepassword123`

| # | Nurse Name | Email | Assigned Department / Unit | Role & Shift | Nursing Station |
| :- | :--- | :--- | :--- | :--- | :--- |
| 1 | Sister Sunita Verma | `nurse@test.com` | Inpatient Care | Head Nurse (Morning) | Station 1 |
| 2 | Sister Preeti Thomas | `nurse2@aihos.org` | Critical Care | Senior ICU Incharge (Morning) | ICU Desk |
| 3 | Nurse Rekha Nair | `nurse3@aihos.org` | Cardiology | Cardiac Care Unit (CCU) Nurse (Morning) | CCU Station |
| 4 | Nurse Anitha Kurien | `nurse4@aihos.org` | Pediatrics | Pediatric Ward Nurse (Afternoon) | Pediatric Desk |
| 5 | Nurse Mary Fernandez | `nurse5@aihos.org` | Emergency & Trauma | Emergency & Trauma Nurse (Night) | Trauma Desk |
| 6 | Nurse Geetha Krishnan | `nurse6@aihos.org` | Orthopedics | Orthopedic Post-Op Nurse (Morning) | Ortho Station |
| 7 | Nurse Shilpa Deshmukh | `nurse7@aihos.org` | Nephrology | Dialysis Unit Staff Nurse (Morning) | Dialysis Wing |
| 8 | Nurse Kavita Rawat | `nurse8@aihos.org` | Oncology | Oncology Daycare Nurse (Morning) | Daycare Station |
| 9 | Nurse Blessy Mathew | `nurse9@aihos.org` | General Surgery | Surgical Step-Down Nurse (Afternoon) | Surgery Station |
| 10 | Nurse Pooja Negi | `nurse10@aihos.org` | Emergency & Trauma | Triage Screening Nurse (Morning) | Triage Desk |
| 11 | Nurse Deepa Swaminathan | `nurse11@aihos.org` | Critical Care | Night Shift ICU Incharge (Night) | ICU Central |
| 12 | Nurse Mini Joseph | `nurse12@aihos.org` | Pediatrics | Neonatal ICU (NICU) Nurse (Night) | NICU Station |
| 13 | Nurse Sarita Yadav | `nurse13@aihos.org` | General Medicine | General Medical Ward Nurse (Afternoon) | Ward 2 Desk |
| 14 | Nurse Lissy Varghese | `nurse14@aihos.org` | Administration | Infection Control Liaison Nurse (Morning) | Infection Office |
| 15 | Nurse Usha Rani | `nurse15@aihos.org` | Neurology | Stroke Care Unit Nurse (Morning) | Neuro Desk |
| 16 | Nurse Sneha Patil | `nurse16@aihos.org` | Outpatient Care | Infusion Clinic Nurse (Morning) | Infusion Wing |
| 17 | Nurse Bindu Samuel | `nurse17@aihos.org` | Inpatient Care | Wound & Catheter Care Nurse (Afternoon) | Ward 3 Desk |
| 18 | Nurse Ancy Philip | `nurse18@aihos.org` | Critical Care | High Dependency Unit (HDU) Nurse (Night) | HDU Desk |
| 19 | Nurse Reena George | `nurse19@aihos.org` | General Surgery | Pre-Op Holding Nurse (Morning) | Pre-Op Area |
| 20 | Nurse Jancy Abraham | `nurse20@aihos.org` | Inpatient Care | Palliative & Elderly Care Nurse (Morning) | Geriatric Desk |

---

### Populating the Clinical Dummy Dataset

The project includes an idempotent seeder (`database/seed.py`) that populates the complete clinical ecosystem:
- **Flagship Facility**: Apex Multi-Specialty Hospital & Research Center (`APEX-HOSP-01`, 150 Beds, 30 ICU Beds, NABH licensed, ABDM `IN-DL-AIHOS-001`).
- **Clinicians**: 10 Departmental Specialists + 20 Physicians across disciplines with verified medical licenses.
- **Nursing Staff**: 20 Inpatient Ward, ICU, and Trauma Nurses with role-based workstation credentials.
- **Patient Cohort**: 5 Patients with verified ABHA addresses (`amit.kumar@abdm`, `priya.sharma@abdm`, etc.).
- **Consultations & Telehealth**: Scheduled upcoming visits, active video consultations, and completed encounters.
- **Medical Records & Approvals**: Finalized SOAP records plus drafts queued in the clinician review gate ([`/doctor/approvals`](http://localhost:3000/doctor/approvals)).
- **Prescriptions**: Formatted medication regimens with drug-drug and allergy interaction screening.
- **Inpatient Beds & Nursing Telemetry**: Step-down and ICU bed matrices with historical vitals (BP, SpO2, Pulse) and due medication rounds.
- **Patient Adherence**: Daily scheduled dosage reminders and uploaded diagnostic PDF reports.

**To run the seeder:**
```powershell
# From the project root:
python run_seed.py
# Or double-click the helper script:
.\seed.bat
```

> [!NOTE]
> - **Idempotent Seeder**: `run_seed.py` uses `ON CONFLICT DO UPDATE`. You can run it safely at any time to refresh mock records.
> - **Isolated Patient Authentication**: Patients sign in exclusively at `/patient/login` with zero access to the institutional staff portal.
> - **Staff Provisioning Boundary**: New doctors, nurses, and staff accounts must be provisioned by a facility Administrator via `/admin/users`.
> - **Production Guardrail**: In `APP_ENV=production`, mock user seeding is strictly disabled by default. All production credentials must be securely provisioned via environment variables or vault secret managers.

### Docker Compose Services
- `redis` — Redis 7 with persistence and named volume `redis_data`
- `backend` — FastAPI with hot-reload (uvicorn --reload)
- `frontend` — Next.js with hot-reload (npm run dev)

## Environment Variables

Create `.env` or `.env.local` and configure:

### Required API Keys
```bash
# LLM Providers (M19)
LLM_PROVIDER=nvidia          # or "gemini"
NVIDIA_API_KEY=your_nvidia_key
NVIDIA_BASE_URL=https://integrate.api.nvidia.com/v1
NVIDIA_MODEL=nvidia/nemotron-3-ultra-550b-a55b
GEMINI_API_KEY=your_gemini_key

# STT Provider (M19)
STT_PROVIDER=groq
GROQ_API_KEY=your_groq_key

# TTS Provider (M34 - stub for now)
TTS_PROVIDER=mock

# Database (PostgreSQL)
DATABASE_URL=postgresql+asyncpg://postgres:your_secure_password@localhost:5432/ai_hos
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_secure_password
POSTGRES_DB=ai_hos

# Redis
REDIS_URL=redis://localhost:6379/0

# JWT
JWT_SECRET_KEY=your_32_char_secret_key
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# Application
APP_ENV=development
APP_HOST=0.0.0.0
APP_PORT=8000

# Frontend
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
NEXT_PUBLIC_APP_URL=http://localhost:3000
```

### Database Deployment Architecture (SEC-M01)
- **Local Development**: Uses local Docker Compose PostgreSQL (`localhost:5432`). In-memory/file-based SQLite engines are strictly utilized for isolated unit test runs.
- **Staging & Production**: Uses managed cloud PostgreSQL (e.g., Nhost, Supabase, or AWS RDS). No credentials are committed to version control; connection strings are injected dynamically via GitHub Secrets / Kubernetes secret mounts (`${{ secrets.DATABASE_URL }}`).

### Getting API Keys
- **NVIDIA NIM**: https://build.nvidia.com (Nemotron 3 Ultra free tier)
- **Google Gemini**: https://aistudio.google.com (Flash models free tier)
- **Groq**: https://console.groq.com (Whisper STT free tier)

> [!WARNING]
> **DEVELOPMENT & TEST PERSONAS ONLY (SEC-07 & SEC-M02)**:
> Any test credentials referenced in local automated tests or development seeds (`admin@test.com`, `doctor@test.com`, `patient@test.com`) are strictly intended for local mock development (`APP_ENV=development`). They must **NEVER** be provisioned, configured, or utilized in staging or production environments. Production systems enforce strict administrative provisioning for staff, public self-registration for patients, and environment-injected cryptographic secrets.

## Running Tests

### Backend Tests
```bash
cd backend
python -m pytest tests/ -v
# Or specific test file
python -m pytest tests/test_approval.py -v
```

### AI Services Tests
```bash
cd ai-services
python -m pytest providers/test_providers.py -v
python -m pytest orchestrator/test_orchestrator.py -v
python -m pytest agents/test_scribe_agent.py -v
python -m pytest agents/test_prescription_agent.py -v
```

### All Tests
```bash
# From root
python -m pytest backend/tests/ ai-services/ -v
```

## API Usage Examples

### Authentication
```bash
# Login (returns access_token and refresh_token)
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@test.com", "password": "adminpassword123"}'

# Access protected Admin API
export TOKEN="your_access_token"
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/v1/admin/users/
```

### Voice Note → Clinical Note (M18→M21)
```bash
# 1. Upload voice note
curl -X POST http://localhost:8000/api/v1/voice-notes/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@recording.webm" \
  -F "appointment_id=<uuid>"

# 2. Trigger scribe agent via orchestrator
curl -X POST http://localhost:8000/api/v1/voice-notes/<voice_note_id>/scribe \
  -H "Authorization: Bearer $TOKEN"

# Or analyze consultation transcript directly via Copilot Orchestrator:
# curl -X POST http://localhost:8000/api/v1/copilot/analyze \
#   -H "Authorization: Bearer $TOKEN" \
#   -H "Content-Type: application/json" \
#   -d '{"transcription": "...", "patient_id": "<uuid>"}'
```

### Doctor Review/Approval (M23)
```bash
# List drafts pending review
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/approval/drafts

# Approve medical record
curl -X POST http://localhost:8000/api/v1/approval/medical-records/<record_id>/review \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"action": "approve", "reviewer_notes": "Looks good"}'

# Request changes on prescription
curl -X POST http://localhost:8000/api/v1/approval/prescriptions/<rx_id>/review \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"action": "request_changes", "reviewer_notes": "Adjust dosage", "edited_medications": [...]}'
```

## Monorepo Structure
```
AI-HOS/
├── docs/                    # Documentation (01-09)
├── frontend/                # Next.js + React + Tailwind
├── backend/                 # FastAPI (Python)
│   ├── app/
│   │   ├── api/            # API routes (auth, patients, doctors, appointments, medical_records, prescriptions, voice_notes, approval)
│   │   ├── core/           # Config, exceptions
│   │   ├── models/         # SQLAlchemy models
│   │   ├── services/       # Auth, audit, consent
│   │   └── database.py     # DB session
│   ├── tests/              # 214 tests
│   └── alembic/            # Migrations
├── ai-services/             # AI agent services
│   ├── providers/          # Provider adapter (M19) - 59 tests
│   ├── orchestrator/       # Task orchestrator (M20) - 19 tests
│   ├── agents/             # Scribe (M21), Prescription (M22) agents - 31 tests
│   └── __init__.py
├── database/                # Migrations, seeds
├── docker/                  # Docker configs
├── .github/workflows/       # CI/CD (M14)
├── .gitignore
├── .env.example             # Template with variable names
├── .env.dev                 # Development template
├── .env.staging             # Staging template with secret refs
├── .env.prod                # Production template with secret refs
└── README.md
```

## CI/CD (M14)
- **GitHub Actions**: `.github/workflows/ci.yml`
- On every push/PR: backend lint (ruff) + test (pytest), frontend lint + build + test, Docker builds
- Secrets injected via GitHub Actions secrets for staging/prod

## Documentation
- [01 Project Charter](docs/01_Project_Charter.md)
- [02 Architecture](docs/02_Architecture.md)
- [03 Tech Stack](docs/03_Tech_Stack.md)
- [04 API Conventions](docs/04_API_Conventions.md)
- [05 Data Model](docs/05_Data_Model.md)
- [06 Auth, RBAC, Consent](docs/06_Auth_RBAC_Consent.md)
- [07 AI Agents](docs/07_AI_Agents.md)
- [08 Compliance](docs/08_Compliance.md)
- [09 Deployment](docs/09_Deployment.md)

## Compliance
- India: DPDP Act 2023, ABDM ecosystem
- HIPAA (if U.S. data processed)
- HL7 FHIR R4 canonical format
- TLS 1.2+ in transit, AES-256 at rest
- No raw national IDs stored (tokenized ABHA addresses)

## License
Proprietary — All rights reserved
