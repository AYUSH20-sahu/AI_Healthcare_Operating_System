# AI-HOS Technology Stack & Specifications

## 1. Backend Core

| Component | Technology | Version | Purpose |
| :--- | :--- | :--- | :--- |
| **Runtime** | Python | 3.11+ | Asynchronous core execution environment |
| **Web Framework** | FastAPI | >= 0.110.0 | High-performance asynchronous REST & WebSocket API |
| **ASGI Server** | Uvicorn | Standard | Production ASGI application server |
| **Database ORM** | SQLAlchemy | >= 2.0.0 | Declarative asynchronous database models and query builders |
| **DB Drivers** | `asyncpg` / `aiosqlite` | Latest | High-speed asynchronous PostgreSQL and SQLite drivers |
| **Validation** | Pydantic | >= 2.0.0 | Strict schema definition and JSON serialization |
| **Authentication** | `python-jose`, `passlib` | Latest | JWT bearer token creation and Argon2id/bcrypt hashing |
| **Networking** | `httpx` | Latest | Asynchronous HTTP client for external ABDM & NHCX APIs |
| **Test Runner** | `pytest`, `pytest-asyncio` | Latest | Comprehensive test execution and mock client fixtures |

---

## 2. Frontend Core

| Component | Technology | Version | Purpose |
| :--- | :--- | :--- | :--- |
| **Framework** | Next.js (App Router) | 14.2.0 | React framework for server/client rendering and routing |
| **UI Library** | React / React-DOM | 18.3.0 | Modern declarative component architecture |
| **Styling** | Tailwind CSS | Latest | Modern responsive utility classes and theme tokens |
| **WebRTC Client** | Native Browser WebRTC | W3C Standard | Encrypted peer-to-peer audio and video communication |
| **Real-time Client** | Native WebSocket | W3C Standard | Signalling relay and ward telemetry streams |
| **Language** | TypeScript | >= 5.0.0 | Type safety across API client models and UI components |

---

## 3. Infrastructure & Network

| Component | Technology | Purpose |
| :--- | :--- | :--- |
| **Container Engine** | Docker | Multi-stage production containerization |
| **Orchestration** | Kubernetes | High-availability pod deployments, rolling updates, health checks |
| **Reverse Proxy** | NGINX Ingress | SSL/TLS termination, rate limiting, and path routing |
| **NAT Traversal** | Coturn | RFC 5766 STUN & TURN server for enterprise hospital firewall bypass |
| **Database Engine** | PostgreSQL | Enterprise ACID relational storage with JSONB support |
| **Benchmarking** | k6 & Pytest Bench | P95 latency validation and high-concurrency load testing |