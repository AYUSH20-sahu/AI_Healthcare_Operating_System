# AI-HOS Deployment, Kubernetes & DevOps Guide

## 1. Deployment Topology Options

AI-HOS supports both containerized local/development setups via Docker Compose and enterprise high-availability orchestration via production Kubernetes manifests located in `k8s/`.

---

## 2. Local & Development Deployment (Docker Compose)

The root repository contains `docker-compose.yml` defining the core services:
- `backend`: FastAPI Python service on port `8000`.
- `frontend`: Next.js 14 App on port `3000`.
- `db`: PostgreSQL database with health checks on port `5432`.
- `coturn`: RFC 5766 STUN/TURN server on port `3478` (UDP/TCP).

### Launching Services:
```bash
docker-compose up --build -d
```

---

## 3. Production Kubernetes Manifests (`k8s/`)

The platform includes production-ready Kubernetes specifications organized for Kustomize deployment:

```
k8s/
├── namespace.yaml                # ai-hos dedicated namespace
├── configmap.yaml                # Environment parameters & service URLs
├── backend-deployment.yaml       # FastAPI Deployment & Service (Port 8000)
├── frontend-deployment.yaml      # Next.js 14 Deployment & Service (Port 3000)
├── ingress.yaml                  # NGINX Ingress Controller with SSL/TLS
└── kustomization.yaml            # Declarative resource manifest bundle
```

### 3.1 Applying Manifests:
```bash
kubectl apply -k k8s/
```

### 3.2 Resource & Health Probe Architecture:
- **Backend Deployment**:
  - Replicas: 2 (auto-scalable via HPA).
  - Liveness Probe: `GET /health` with initial delay of 15 seconds.
  - Readiness Probe: `GET /health` with 5-second interval.
  - Memory Requests/Limits: `256Mi` / `512Mi`.
  - CPU Requests/Limits: `250m` / `1000m`.
- **Frontend Deployment**:
  - Replicas: 2.
  - Liveness Probe: `GET /` with initial delay of 20 seconds.
  - Memory Requests/Limits: `256Mi` / `512Mi`.

### 3.3 Ingress Routing:
- `http://hospital.example.com/api/v1/*` $\to$ `backend-service:8000` (WebSocket support enabled).
- `http://hospital.example.com/*` $\to$ `frontend-service:3000`.

---

## 4. Coturn STUN/TURN Setup

To ensure uninterrupted WebRTC telehealth calls across restrictive corporate and hospital firewalls:

1. **Coturn Installation**:
   ```bash
   sudo apt-get install coturn
   ```
2. **Configuration (`/etc/turnserver.conf`)**:
   ```conf
   listening-port=3478
   tls-listening-port=5349
   fingerprint
   use-auth-secret
   static-auth-secret=ENTERPRISE_HOSPITAL_SECRET_KEY
   realm=hospital.ai-hos.org
   total-quota=100
   stale-nonce
   ```
3. **Backend Integration**: Set `COTURN_STATIC_SECRET` in `configmap.yaml` or `.env` so `/api/v1/telehealth/ice-servers` generates valid time-limited HMAC-SHA1 tokens.

---

## 5. Environment Configuration Reference

| Environment Variable | Description | Default (Dev) |
| :--- | :--- | :--- |
| `DATABASE_URL` | SQLAlchemy async connection URI | `sqlite+aiosqlite:///./ai_hos.db` |
| `SECRET_KEY` | JWT HMAC secret key | `supersecretkey_dev_only` |
| `NEXT_PUBLIC_API_URL` | Frontend client target API base | `http://localhost:8000/api/v1` |
| `NEXT_PUBLIC_APP_URL` | Frontend origin URL | `http://localhost:3000` |
| `BACKEND_INTERNAL_URL` | Next.js server-side API proxy target | `http://localhost:8000` |
| `COTURN_STATIC_SECRET` | Secret key for TURN token generation | `coturn_development_secret` |
| `COTURN_REALM` | Domain realm for TURN server | `ai-hos.telehealth.local` |