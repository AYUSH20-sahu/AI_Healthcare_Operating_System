"""
Unit and integration tests for Real-Time WebSockets Engine (Horizon A).
Tests TelemetryConnectionManager, QueueConnectionManager, WebSocket token authentication,
live bedside telemetry broadcasts, and real-time OPD queue status events.
"""

from uuid import uuid4
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.testclient import TestClient

from app.core.websocket_manager import ConnectionManager, queue_manager, telemetry_manager
from app.main import app
from app.models import User, UserRole, InpatientBed
from app.services.auth.service import create_access_token, get_password_hash


@pytest.fixture
async def nurse_ws_user(db_session: AsyncSession):
    """Create a nurse user for WebSocket tests."""
    user = User(
        user_id=uuid4(),
        email="nurse.telemetry@aihos.org",
        hashed_password=get_password_hash("nursepass123"),
        full_name="Nurse Telemetry Operator",
        role=UserRole.NURSE,
        department="Intensive Care Unit (ICU)",
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
def nurse_ws_token(nurse_ws_user: User):
    return create_access_token(
        data={
            "sub": str(nurse_ws_user.user_id),
            "email": nurse_ws_user.email,
            "role": nurse_ws_user.role.value,
        }
    )


@pytest.fixture
async def patient_ws_user(db_session: AsyncSession):
    """Create a patient user (not cleared for ward telemetry)."""
    user = User(
        user_id=uuid4(),
        email="patient.visitor@aihos.org",
        hashed_password=get_password_hash("patientpass123"),
        full_name="Patient Visitor",
        role=UserRole.PATIENT,
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
def patient_ws_token(patient_ws_user: User):
    return create_access_token(
        data={
            "sub": str(patient_ws_user.user_id),
            "email": patient_ws_user.email,
            "role": patient_ws_user.role.value,
        }
    )


@pytest.mark.asyncio
async def test_websocket_status_endpoint(client: AsyncClient):
    """Verify GET /api/v1/ws/status returns active channel diagnostics."""
    resp = await client.get("/api/v1/ws/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert "telemetry" in data
    assert "queue" in data
    assert "total_channels" in data["telemetry"]
    assert "total_connections" in data["telemetry"]


@pytest.mark.asyncio
async def test_connection_manager_in_memory_broadcast():
    """Verify ConnectionManager handles channel registration, stats, and safe broadcasts."""
    mgr = ConnectionManager(name="test_mgr")
    stats = mgr.get_stats()
    assert stats["total_channels"] == 0
    assert stats["total_connections"] == 0

    # Broadcast to an empty channel should return 0 delivered
    sent = await mgr.broadcast("test_channel", {"test": "data"})
    assert sent == 0


def test_ward_telemetry_ws_unauthorized():
    """Verify WebSocket connection is rejected if no token or invalid token is provided."""
    client = TestClient(app)
    # No token
    with pytest.raises(Exception):
        with client.websocket_connect("/api/v1/ws/telemetry/ward/icu") as ws:
            ws.receive_json()

    # Invalid token
    with pytest.raises(Exception):
        with client.websocket_connect("/api/v1/ws/telemetry/ward/icu?token=invalid.jwt.token") as ws:
            ws.receive_json()


def test_ward_telemetry_ws_insufficient_role(patient_ws_token: str):
    """Verify Patient role is rejected from clinical ward telemetry."""
    client = TestClient(app)
    with pytest.raises(Exception):
        with client.websocket_connect(f"/api/v1/ws/telemetry/ward/icu?token={patient_ws_token}") as ws:
            ws.receive_json()


def test_ward_telemetry_ws_authorized_handshake(nurse_ws_token: str):
    """Verify Nurse user successfully connects, receives handshake, and exchanges heartbeats."""
    client = TestClient(app)
    with client.websocket_connect(f"/api/v1/ws/telemetry/ward/icu?token={nurse_ws_token}") as ws:
        data = ws.receive_json()
        assert data["event"] == "CONNECTED"
        assert data["channel"] == "telemetry:icu"
        assert data["ward"] == "icu"
        assert "Nurse Telemetry Operator" in data["authenticated_as"]

        # Send ping, expect pong
        ws.send_text("ping")
        resp = ws.receive_text()
        assert resp == "pong"


def test_queue_broadcast_ws_handshake(nurse_ws_token: str):
    """Verify OPD Queue WebSocket handshake and heartbeat."""
    client = TestClient(app)
    with client.websocket_connect(f"/api/v1/ws/queue/default_org?token={nurse_ws_token}") as ws:
        data = ws.receive_json()
        assert data["event"] == "CONNECTED"
        assert data["channel"] == "queue:default_org"
        assert data["organization_id"] == "default_org"

        ws.send_text("ping")
        assert ws.receive_text() == "pong"
