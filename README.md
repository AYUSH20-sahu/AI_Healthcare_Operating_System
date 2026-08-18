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
cp .env.example .env
# Edit .env with your API keys

# Start development environment
docker compose up
```

### Services
- **Frontend** (Next.js): http://localhost:3000
- **Backend** (FastAPI): http://localhost:8000
- **API Docs** (OpenAPI): http://localhost:8000/docs
- **PostgreSQL**: localhost:5432
- **Redis**: localhost:6379

## Monorepo Structure
```
AI-HOS/
├── docs/                    # Documentation (01-09)
├── frontend/                # Next.js + React + Tailwind
├── backend/                 # FastAPI (Python)
├── ai-services/             # AI agent services
├── database/                # Migrations, seeds
├── docker/                  # Docker configs
├── .github/workflows/       # CI/CD
├── .gitignore
├── .env.example
└── README.md
```

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