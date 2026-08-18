# Deployment — AI-HOS

## Local Development (M2)
```bash
docker compose up
```

### Services Started
- **postgres** — PostgreSQL 16 (port 5432) with healthcheck, named volume `postgres_data`
- **redis** — Redis 7 (port 6379) with persistence, healthcheck, named volume `redis_data`
- **backend** — FastAPI (port 8000) with hot-reload, depends on healthy postgres/redis
- **frontend** — Next.js (port 3000) with hot-reload, depends on backend

### Environment
Uses `.env.local` for development configuration (gitignored).

## Environment Separation (M5)
- `.env.local` — local development (gitignored, copy from `.env.dev`)
- `.env.dev` — development template with placeholder values
- `.env.staging` — staging template with GitHub Actions secret references
- `.env.prod` — production template with GitHub Actions secret references

### Required Secrets per Environment
| Secret | Dev | Staging | Prod |
|--------|-----|---------|------|
| `LLM_PROVIDER` | ✓ | ✓ | ✓ |
| `LLM_API_KEY` | ✓ | ✓ | ✓ |
| `DATABASE_URL` | ✓ | ✓ | ✓ |
| `POSTGRES_USER` | ✓ | ✓ | ✓ |
| `POSTGRES_PASSWORD` | ✓ | ✓ | ✓ |
| `POSTGRES_DB` | ✓ | ✓ | ✓ |
| `REDIS_URL` | ✓ | ✓ | ✓ |
| `JWT_SECRET_KEY` | ✓ | ✓ | ✓ |
| `NEXT_PUBLIC_API_URL` | ✓ | ✓ | ✓ |
| `NEXT_PUBLIC_APP_URL` | ✓ | ✓ | ✓ |
| `WHISPER_API_KEY` | Phase 6 | Phase 6 | Phase 6 |
| `ELEVENLABS_API_KEY` | Phase 6 | Phase 6 | Phase 6 |
| `ABDM_CLIENT_ID` | Phase 4+ | Phase 4+ | Phase 4+ |
| `ABDM_CLIENT_SECRET` | Phase 4+ | Phase 4+ | Phase 4+ |
| `FHIR_BASE_URL` | Phase 4+ | Phase 4+ | Phase 4+ |
| `SENTRY_DSN` | Optional | ✓ | ✓ |

## CI/CD Pipeline (GitHub Actions) — M5
**Workflow:** `.github/workflows/ci.yml`

### On every push to main / PR:
1. **Backend Lint & Test** (`backend-lint-and-test`):
   - Spins up PostgreSQL 16 + Redis 7 service containers
   - Installs Python 3.11 + dependencies (cached)
   - Runs `ruff` linting
   - Runs `pytest` with coverage
   - Uploads coverage to Codecov

2. **Frontend Lint & Build** (`frontend-lint-and-build`):
   - Installs Node.js 20 + dependencies (cached)
   - Runs `npm run lint` (ESLint)
   - Runs `npm run build` (Next.js production build)
   - Runs `npm test` (if configured)

3. **Docker Build** (`docker-build`):
   - Builds backend Docker image (`backend/Dockerfile.dev`)
   - Builds frontend Docker image (`frontend/Dockerfile.dev`)

### Secrets Injection
- **Development**: Uses `.env.local` (gitignored, not in CI)
- **Staging/Production**: Secrets injected via GitHub Actions `secrets` context
- Configure secrets in GitHub repo: Settings → Secrets and variables → Actions

## Infrastructure
- Docker + Kubernetes
- Multi-tenant data isolation per hospital/clinic
- Health checks for all services