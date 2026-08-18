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

## Environment Separation
- `.env.local` — local development (gitignored)
- `.env.staging` — staging environment
- `.env.prod` — production environment

## Secrets Management
- Never commit secrets to source control
- Inject via environment variables / secrets manager per environment
- CI/CD pipelines receive secrets at runtime

## CI/CD Pipeline (GitHub Actions)
- On every push:
  - Lint and run backend tests (pytest)
  - Lint and run frontend tests/build
- Separate workflows for staging/prod deployments

## Infrastructure
- Docker + Kubernetes
- Multi-tenant data isolation per hospital/clinic
- Health checks for all services