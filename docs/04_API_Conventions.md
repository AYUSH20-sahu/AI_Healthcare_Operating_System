# AI-HOS API Design & Conventions

## 1. RESTful Standards

All AI-HOS HTTP endpoints adhere to predictable REST conventions rooted at `/api/v1`.

### 1.1 HTTP Method Conventions
- `GET`: Idempotent retrieval of resources. Never alters server state.
- `POST`: Creation of subordinate resources, submission of intake sessions, or triggering workflows (e.g. signing a clinical note).
- `PUT`: Complete idempotent replacement of an existing resource.
- `PATCH`: Partial modification of resource fields.
- `DELETE`: Safe soft-deletion or decommissioning of resources.

### 1.2 Status Codes
- `200 OK`: Request succeeded; response payload contains data.
- `201 Created`: Resource successfully persisted; returns newly created entity.
- `400 Bad Request`: Validation failure or malformed payload.
- `401 Unauthorized`: Missing, expired, or invalid JWT bearer token.
- `403 Forbidden`: Authenticated user lacks RBAC permissions for the action.
- `404 Not Found`: Target resource does not exist in the tenant scope.
- `409 Conflict`: Resource state conflict (e.g., appointment slot double-booking).
- `500 Internal Server Error`: Unhandled server exception with structured request ID.

---

## 2. Standardized Error Payload Format

All non-2xx responses return a consistent JSON schema:

```json
{
  "detail": "Descriptive human-readable error explanation",
  "code": "SLOT_CONFLICT",
  "request_id": "req-98af12d3",
  "timestamp": "2026-10-15T14:30:00Z"
}
```

---

## 3. Pagination & Query Conventions

Collection endpoints support standard query parameters:
- `page`: 1-based page index (default: `1`).
- `page_size`: Number of records per page (default: `50`, maximum: `200`).
- `sort_by`: Field name to sort against (e.g. `scheduled_at`).
- `order`: `asc` or `desc` (default: `desc`).

### Standard Paginated Envelope
```json
{
  "items": [...],
  "total": 142,
  "page": 1,
  "page_size": 50,
  "total_pages": 3
}
```

---

## 4. Real-Time WebSocket Conventions

### Telehealth Signalling (`/api/v1/telehealth/ws/{room_id}`)
- Framing: UTF-8 JSON text messages.
- Format:
  ```json
  {
    "type": "offer" | "answer" | "ice-candidate" | "bye" | "room_joined" | "peer_joined",
    "payload": { ... }
  }
  ```
- Authentication: Validated via `?token=<jwt_bearer_token>` query parameter during WebSocket handshake.