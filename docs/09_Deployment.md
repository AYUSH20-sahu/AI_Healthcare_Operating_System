# Deployment — AI-HOS

## Local Development
```bash
docker compose up
```

## Environment Separation
- `.env.dev` — local development
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