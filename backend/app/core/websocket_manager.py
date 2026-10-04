"""
WebSocket Connection Manager for AI-HOS Real-Time Telemetry and Queue Broadcasting.

Provides robust multi-channel WebSocket management with optional Redis Pub/Sub
distribution for horizontal multi-worker scaling, with automatic in-memory fallback.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Dict, Set
from fastapi import WebSocket

logger = logging.getLogger("ai_hos.websockets")


class ConnectionManager:
    """Manages active WebSocket connections grouped by logical channels with optional Redis Pub/Sub."""

    def __init__(self, name: str = "default"):
        self.name = name
        # channel_name -> set of active WebSockets
        self.active_channels: Dict[str, Set[WebSocket]] = {}
        self._lock = asyncio.Lock()
        self._redis = None

    async def _get_redis(self):
        """Lazy async Redis client resolution with graceful degradation."""
        if self._redis is None:
            try:
                import importlib
                aioredis = importlib.import_module("redis.asyncio")
                from app.core.config import settings

                redis_url = getattr(settings, "REDIS_URL", "redis://localhost:6379/0")
                client = aioredis.from_url(redis_url, decode_responses=True)
                await asyncio.wait_for(client.ping(), timeout=0.5)
                self._redis = client
                logger.info(f"[{self.name}] Redis Pub/Sub backend connected successfully.")
            except Exception:
                self._redis = False  # Mark as unavailable to prevent repeated reconnection overhead
        return self._redis if self._redis is not False else None

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
        Publishes to Redis if available, while delivering to local in-memory subscribers.
        """
        message_text = json.dumps(message)

        # Distribute across cluster via Redis if available
        r = await self._get_redis()
        if r:
            try:
                redis_channel = f"ai_hos:{self.name}:{channel}"
                await r.publish(redis_channel, message_text)
            except Exception as e:
                logger.warning(f"[{self.name}] Redis publish fallback notice: {e}")

        return await self._local_broadcast(channel, message_text)

    async def _local_broadcast(self, channel: str, message_text: str) -> int:
        recipients: list[WebSocket] = []

        async with self._lock:
            if channel in self.active_channels:
                recipients = list(self.active_channels[channel])

        if not recipients:
            return 0

        sent_count = 0
        dead_connections: list[WebSocket] = []

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
            "redis_enabled": self._redis not in (None, False),
        }


# Global singleton managers
telemetry_manager = ConnectionManager(name="telemetry")
queue_manager = ConnectionManager(name="queue")
