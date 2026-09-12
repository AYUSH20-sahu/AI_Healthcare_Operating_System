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
| M24+ | Patient app, Intake, Triage, Voice, Deployment | 🔄 Planned |

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

### Default User Credentials & Personas

The system automatically provisions verified test personas on startup for local development and review:

| Role | Email (User ID) | Password | Clearance & Access Route |
| :--- | :--- | :--- | :--- |
| **System Administrator** | `admin@test.com` <br> *(Alt: `admin@aihos.org`)* | `adminpassword123` | **Level 4 Clearance** — Admin Console (`/admin`), User & Clinician Provisioning (`/admin/users`), Immutable Audit Logs (`/admin/audit`) |
| **Physician / Doctor** | `doctor@test.com` | `doctorpassword123` | **Clinical Clearance** — Doctor Cockpit (`/doctor`), Ambient Scribe (`/doctor/scribe`), Review Gate (`/doctor/review`) |
| **Patient** | `patient@test.com` | `patientpassword123` | **Patient Portal** — Care Dashboard (`/patient`), Appointment Booking, PHR Viewer |

> [!NOTE]
> - Public registration (`/auth/register`) is strictly for Patients.
> - Doctor, Nurse, and Staff accounts must be provisioned by an Administrator via `/admin/users`.
> - Login (`/auth/login`) determines the user's role from their server-issued JWT and automatically routes them to the corresponding workspace.

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
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/ai_hos
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

### Getting API Keys
- **NVIDIA NIM**: https://build.nvidia.com (Nemotron 3 Ultra free tier)
- **Google Gemini**: https://aistudio.google.com (Flash models free tier)
- **Groq**: https://console.groq.com (Whisper STT free tier)

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
curl -X POST http://localhost:8000/api/v1/approval/drafts \
  -H "Authorization: Bearer $TOKEN"
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
├── .github/workflows/       # CI/CD (M5)
├── .gitignore
├── .env.example             # Template with variable names
├── .env.dev                 # Development template (M5)
├── .env.staging             # Staging template with secret refs (M5)
├── .env.prod                # Production template with secret refs (M5)
└── README.md
```

## CI/CD (M5)
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
