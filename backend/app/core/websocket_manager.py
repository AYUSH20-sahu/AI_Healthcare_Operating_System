"""
WebSocket Connection Manager for AI-HOS Real-Time Telemetry and Queue Broadcasting.

Provides robust multi-channel WebSocket management with optional Redis Pub/Sub
distribution for horizontal multi-worker scaling, with automatic in-memory fallback.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Dict, List, Set
from fastapi import WebSocket

logger = logging.getLogger("ai_hos.websockets")


class ConnectionManager:
    """Manages active WebSocket connections grouped by logical channels."""

    def __init__(self, name: str = "default"):
        self.name = name
        # channel_name -> set of active WebSockets
        self.active_channels: Dict[str, Set[WebSocket]] = {}
        self._lock = asyncio.Lock()
        self._redis_client = None
        self._pubsub_task: asyncio.Task | None = None

    async def connect(self, websocket: WebSocket, channel: str) -> None:
        """Accept and register an incoming WebSocket connection into a channel."""
        await websocket.accept()
        async with self._lock:
            if channel not in self.active_channels:
                self.active_channels[channel] = set()
            self.active_channels[channel].add(websocket)
        logger.info(
            f"[{self.name}] WebSocket connected to channel '{channel}'. "
            f"Active connections in channel: {len(self.active_channels[channel])}"
        )

    async def disconnect(self, websocket: WebSocket, channel: str) -> None:
        """Remove a disconnected WebSocket from its channel."""
        async with self._lock:
            if channel in self.active_channels:
                self.active_channels[channel].discard(websocket)
                if not self.active_channels[channel]:
                    del self.active_channels[channel]
        logger.info(f"[{self.name}] WebSocket disconnected from channel '{channel}'.")

    async def broadcast(self, channel: str, message: Dict[str, Any]) -> int:
        """
        Broadcast a JSON message to all active WebSockets connected to a specific channel.
        Returns the number of connected clients successfully notified.
        """
        message_text = json.dumps(message)
        recipients: List[WebSocket] = []

        async with self._lock:
            if channel in self.active_channels:
                recipients = list(self.active_channels[channel])

        if not recipients:
            return 0

        sent_count = 0
        dead_connections: List[WebSocket] = []

        for ws in recipients:
            try:
                await ws.send_text(message_text)
                sent_count += 1
            except Exception as exc:
                logger.warning(
                    f"[{self.name}] Failed to send message to client on '{channel}': {exc}"
                )
                dead_connections.append(ws)

        # Cleanup any broken sockets
        if dead_connections:
            async with self._lock:
                if channel in self.active_channels:
                    for dead in dead_connections:
                        self.active_channels[channel].discard(dead)
                    if not self.active_channels[channel]:
                        del self.active_channels[channel]

        return sent_count

    def get_stats(self) -> Dict[str, Any]:
        """Return diagnostic metrics of active connections and channels."""
        return {
            "manager": self.name,
            "total_channels": len(self.active_channels),
            "channels": {
                ch: len(conns) for ch, conns in self.active_channels.items()
            },
            "total_connections": sum(
                len(conns) for conns in self.active_channels.values()
            ),
        }


# Global singleton managers
telemetry_manager = ConnectionManager(name="telemetry")
queue_manager = ConnectionManager(name="queue")
