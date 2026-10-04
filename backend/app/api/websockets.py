"""
WebSocket API Endpoints for AI-HOS Real-Time Telemetry and Queue Broadcasting.

Provides:
- WS /api/v1/ws/telemetry/ward/{ward_name} (Bedside vitals & alarms stream)
- WS /api/v1/ws/queue/{organization_id} (Live OPD triage queue stream)
- GET /api/v1/ws/status (Connection health & diagnostics)
"""

from __future__ import annotations

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect, status
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.websocket_manager import queue_manager, telemetry_manager
from app.database import get_db
from app.models import User, UserRole

logger = logging.getLogger("ai_hos.websockets_api")

router = APIRouter(prefix="/ws", tags=["Real-Time WebSockets"])


async def authenticate_ws_token(token: Optional[str], db: AsyncSession) -> Optional[User]:
    """
    Authenticate a WebSocket connection via Bearer token query parameter.
    Returns the authenticated User or None if token is missing/invalid.
    """
    if not token:
        return None

    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
        token_type = payload.get("type")
        if token_type and token_type != "access":
            return None

        user_id_str = payload.get("sub")
        if not user_id_str:
            return None

        user_id = UUID(user_id_str)
        result = await db.execute(select(User).where(User.user_id == user_id))
        user = result.scalar_one_or_none()
        if user and user.is_active:
            return user
    except (JWTError, ValueError, Exception) as exc:
        logger.warning(f"WebSocket token authentication failure: {exc}")
        return None

    return None


@router.websocket("/telemetry/ward/{ward_name}")
async def ward_telemetry_websocket(
    websocket: WebSocket,
    ward_name: str,
    token: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """
    Real-time bedside telemetry stream for a specific inpatient ward.
    Broadcasts live vitals updates, critical thresholds, and medication rounds.
    Requires medical staff clearance (Nurse, Doctor, Admin).
    """
    user = await authenticate_ws_token(token, db)
    if not user:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Unauthorized")
        return

    # Enforce role clearance: must be medical staff or admin
    allowed_roles = {
        UserRole.NURSE,
        UserRole.HEAD_NURSE,
        UserRole.DOCTOR,
        UserRole.HEAD_PHYSICIAN,
        UserRole.ADMIN,
        UserRole.SUPER_ADMIN,
    }
    if user.role not in allowed_roles:
        await websocket.close(
            code=status.WS_1008_POLICY_VIOLATION,
            reason="Insufficient clearance for bedside telemetry",
        )
        return

    channel = f"telemetry:{ward_name.lower().strip()}"
    await telemetry_manager.connect(websocket, channel)

    # Send initial welcome payload with channel metadata
    await websocket.send_json({
        "event": "CONNECTED",
        "channel": channel,
        "ward": ward_name,
        "authenticated_as": user.full_name or user.email,
        "role": user.role.value if hasattr(user.role, "value") else str(user.role),
    })

    try:
        while True:
            # Handle client heartbeats or incoming pings
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        await telemetry_manager.disconnect(websocket, channel)
    except Exception as exc:
        logger.warning(f"Error in ward telemetry WebSocket ({channel}): {exc}")
        await telemetry_manager.disconnect(websocket, channel)


@router.websocket("/queue/{organization_id}")
async def queue_broadcast_websocket(
    websocket: WebSocket,
    organization_id: str,
    token: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """
    Real-time OPD triage queue stream for an organization.
    Broadcasts queue state changes, priority adjustments, and room call-ins.
    """
    user = await authenticate_ws_token(token, db)
    if not user:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Unauthorized")
        return

    channel = f"queue:{organization_id.lower().strip()}"
    await queue_manager.connect(websocket, channel)

    await websocket.send_json({
        "event": "CONNECTED",
        "channel": channel,
        "organization_id": organization_id,
        "authenticated_as": user.full_name or user.email,
    })

    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        await queue_manager.disconnect(websocket, channel)
    except Exception as exc:
        logger.warning(f"Error in queue WebSocket ({channel}): {exc}")
        await queue_manager.disconnect(websocket, channel)


@router.get("/status")
async def get_websocket_status():
    """Diagnostic health check returning active WebSocket channels and client counts."""
    return {
        "status": "healthy",
        "telemetry": telemetry_manager.get_stats(),
        "queue": queue_manager.get_stats(),
    }
