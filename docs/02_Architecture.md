# AI-HOS System Architecture & Topology

## 1. High-Level Architectural Topology

AI-HOS is structured as a **modular micro-monolith** leveraging asynchronous Python on the backend and modern React Server / Client components on the frontend.

```
                           [ Internet / Hospital WAN ]
                                       │
                                ┌──────▼──────┐
                                │ NGINX Ingress│ (SSL/TLS Termination)
                                └──────┬──────┘
                                       │
              ┌────────────────────────┴────────────────────────┐
              │                                                 │
       ┌──────▼────────┐                                ┌───────▼──────┐
       │ Next.js 14 App│                                │ FastAPI Async│
       │   Frontend    │                                │   Backend    │
       │  (Port 3000)  │ ─── API Rewrites (/api/v1) ───▶│  (Port 8000) │
       └──────┬────────┘                                └───────┬──────┘
              │                                                 │
              │                                      ┌──────────┼──────────┐
              │ (WebRTC Signalling WebSocket)        │          │          │
              └──────────────────────────────────────┘          │          │
                                                                │          │
                                    ┌───────────────────────────┘          │
                                    │                                      │
                             ┌──────▼───────┐                       ┌──────▼───────┐
                             │ PostgreSQL / │                       │ Coturn STUN/ │
                             │ SQLite Async │                       │ TURN Server  │
                             │ (DB Storage) │                       │ (NAT Bypass) │
                             └──────────────┘                       └──────────────┘
```

---

## 2. Subsystem Architecture

### 2.1 Backend Layer (FastAPI Asynchronous Core)
- **Framework**: FastAPI with asynchronous route handlers (`async def`).
- **ORM & Database Engine**: SQLAlchemy 2.0 with `asyncpg` for PostgreSQL in production and `aiosqlite` for lightweight/local development.
- **Validation**: Pydantic v2 schemas providing strict compile-time and runtime validation.
- **Security & Session**: JWT-based bearer authentication with Argon2id password hashing and role-based dependency injection (`Depends(get_current_active_user)`).
- **Relay Signalling**: In-memory WebSocket connection manager (`_signalling_rooms`) for low-latency peer rendezvous during WebRTC consultations.

### 2.2 Frontend Layer (Next.js 14 App Router)
- **Framework**: Next.js 14 utilizing the App Router directory structure (`src/app/`).
- **Styling**: Tailwind CSS with unified dark/light theme tokens and glassmorphic elevated panels.
- **Domain Portals**:
  - `/doctor`: Outpatient calendar, patient summary, clinical encounter copilot, SOAP note editor.
  - `/patient`: Appointment booking wizard, self-preview telehealth room, clinical records, prescription list.
  - `/nurse`: Inpatient ward management, bed tracking, live triage vitals capture, telemetry queue.
  - `/admin`: Staff provisioning, organization metrics, insurance claim tracking, audit logs.
- **Resilient API Client**: Centralized `api` fetch wrapper in `src/lib/api/client.ts` with automatic bearer token injection, timeout handling, and unified error mapping.

### 2.3 Real-Time Telehealth Engine (WebRTC + Coturn)
```
[ Patient Browser ]               [ FastAPI Signaller ]              [ Doctor Browser ]
        │                                  │                                  │
        │─── GET /telehealth/room/token ──▶│                                  │
        │◀── { ws_url, ice_servers } ──────│                                  │
        │                                  │◀── GET /telehealth/room/token ───│
        │                                  │─── { ws_url, ice_servers } ─────▶│
        │─── WS Connect (/ws/room-id) ────▶│                                  │
        │◀── { type: "room_joined" } ──────│                                  │
        │                                  │◀─── WS Connect (/ws/room-id) ────│
        │◀── { type: "peer_joined" } ──────│─── { type: "peer_joined" } ─────▶│
        │                                  │                                  │
        │─── SDP Offer ───────────────────▶│─── SDP Offer ───────────────────▶│
        │◀── SDP Answer ───────────────────│◀── SDP Answer ───────────────────│
        │─── ICE Candidates ──────────────▶│─── ICE Candidates ──────────────▶│
        │                                  │                                  │
        │═════════════════ P2P Encrypted WebRTC Audio / Video ════════════════│
        │                        (via Coturn STUN/TURN)                       │
```

1. **Token Acquisition**: Both participants fetch credentials and HMAC-SHA1 authenticated TURN tokens from `/api/v1/telehealth/room/{id}/token`.
2. **WebSocket Rendezvous**: Both participants connect to `/api/v1/telehealth/ws/room-{id}`.
3. **P2P Negotiation**: SDP Offers and Answers are routed transparently between peers.
4. **NAT Traversal**: If Direct P2P is blocked by institutional firewalls, media automatically relays via Coturn TURN.

---

## 3. Multi-Tenancy Architecture

All operational database tables incorporate an `organization_id` foreign key referencing the `organizations` table:
- Data queries implicitly or explicitly filter by `organization_id`.
- Indices on `(organization_id, ...)` optimize multi-tenant query plans.
- Tenant isolation prevents cross-clinic data leakage in shared database environments.