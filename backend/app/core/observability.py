"""AI-HOS Observability & Telemetry Framework (Milestone U-22).

Provides:
- Contextual Request ID propagation via X-Request-ID
- Structured JSON log formatting
- Thread-safe rolling telemetry metrics for non-AI & AI calls (P50, P95, P99)
- AI provider invocation metrics (tokens, latency, fallback rate)
- Health check diagnostic utilities for DB, Cache, and AI mesh
- Clean separation from compliance audit_logs
"""

import asyncio
from collections import deque
from contextvars import ContextVar
from datetime import datetime, timezone
import json
import logging
import math
import os
import time
from typing import Any, Dict, List, Optional
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

# Context variable to hold request_id across async call chains
current_request_id: ContextVar[str] = ContextVar("current_request_id", default="system")

logger = logging.getLogger("aihos.observability")


class JSONLogFormatter(logging.Formatter):
    """Structured JSON formatter for application and access logs."""

    def format(self, record: logging.LogRecord) -> str:
        log_data: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": getattr(record, "request_id", current_request_id.get("system")),
        }

        # Include standard extra attributes if populated
        for attr in ("path", "method", "status_code", "latency_ms", "user_id", "provider", "model"):
            val = getattr(record, attr, None)
            if val is not None:
                log_data[attr] = val

        if record.exc_info:
            # We record exception type and message for structured log analyzers
            # Raw stack traces are captured here in backend internal logs only, NEVER sent to client
            log_data["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else "UnknownException",
                "message": str(record.exc_info[1]) if record.exc_info[1] else "",
            }

        return json.dumps(log_data)


class TelemetryCollector:
    """In-memory telemetry and latency aggregator for NFR tracking."""

    def __init__(self, max_samples: int = 1000):
        self._max_samples = max_samples
        self._start_time = time.time()

        # Non-AI API latency samples (in ms)
        self._api_latencies: deque[float] = deque(maxlen=max_samples)

        # AI Call latencies (in ms)
        self._ai_latencies: deque[float] = deque(maxlen=max_samples)
        self._stt_latencies: deque[float] = deque(maxlen=max_samples)
        self._tts_latencies: deque[float] = deque(maxlen=max_samples)

        # Counters
        self._total_requests: int = 0
        self._status_counts: Dict[str, int] = {"2xx": 0, "3xx": 0, "4xx": 0, "5xx": 0}
        self._total_errors: int = 0

        # AI metrics
        self._ai_total_calls: int = 0
        self._ai_fallback_count: int = 0
        self._ai_provider_counts: Dict[str, int] = {}
        self._ai_tokens: Dict[str, int] = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        self._ai_errors: Dict[str, int] = {}

    def record_request(self, method: str, path: str, status_code: int, latency_ms: float) -> None:
        """Record an incoming HTTP request."""
        self._total_requests += 1

        # Classify status code
        if 200 <= status_code < 300:
            self._status_counts["2xx"] += 1
        elif 300 <= status_code < 400:
            self._status_counts["3xx"] += 1
        elif 400 <= status_code < 500:
            self._status_counts["4xx"] += 1
            self._total_errors += 1
        else:
            self._status_counts["5xx"] += 1
            self._total_errors += 1

        # Record non-AI API latency if not an AI-specific endpoint
        is_ai_path = any(x in path for x in ("/copilot", "/voice", "/scribe", "/intake/chat", "/intake/voice"))
        if not is_ai_path:
            self._api_latencies.append(latency_ms)

    def record_ai_call(
        self,
        provider: str,
        provider_type: str,
        latency_ms: float,
        tokens: Optional[Dict[str, int]] = None,
        fallback_used: bool = False,
        success: bool = True,
        error: Optional[str] = None,
    ) -> None:
        """Record an AI provider call (LLM, STT, TTS)."""
        self._ai_total_calls += 1
        self._ai_provider_counts[provider] = self._ai_provider_counts.get(provider, 0) + 1

        if fallback_used:
            self._ai_fallback_count += 1

        if not success and error:
            self._ai_errors[provider] = self._ai_errors.get(provider, 0) + 1

        # Record latencies by type
        if provider_type == "stt":
            self._stt_latencies.append(latency_ms)
        elif provider_type == "tts":
            self._tts_latencies.append(latency_ms)
        else:
            self._ai_latencies.append(latency_ms)

        # Record token consumption
        if tokens:
            self._ai_tokens["prompt_tokens"] += tokens.get("prompt_tokens", 0)
            self._ai_tokens["completion_tokens"] += tokens.get("completion_tokens", 0)
            self._ai_tokens["total_tokens"] += tokens.get("total_tokens", 0)

    @staticmethod
    def _calc_percentiles(samples: deque[float]) -> Dict[str, float]:
        """Compute P50, P95, P99, min, max, avg for a list of samples."""
        if not samples:
            return {"p50": 0.0, "p95": 0.0, "p99": 0.0, "min": 0.0, "max": 0.0, "avg": 0.0, "samples": 0}

        sorted_vals = sorted(samples)
        n = len(sorted_vals)

        def percentile(p: float) -> float:
            idx = int(math.ceil(p * n)) - 1
            return round(sorted_vals[max(0, min(idx, n - 1))], 2)

        return {
            "p50": percentile(0.50),
            "p95": percentile(0.95),
            "p99": percentile(0.99),
            "min": round(sorted_vals[0], 2),
            "max": round(sorted_vals[-1], 2),
            "avg": round(sum(sorted_vals) / n, 2),
            "samples": n,
        }

    def get_metrics(self) -> Dict[str, Any]:
        """Return comprehensive telemetry payload including NFR validation targets."""
        uptime_seconds = round(time.time() - self._start_time, 1)
        api_lat = self._calc_percentiles(self._api_latencies)
        ai_lat = self._calc_percentiles(self._ai_latencies)
        stt_lat = self._calc_percentiles(self._stt_latencies)
        tts_lat = self._calc_percentiles(self._tts_latencies)

        # NFR Target Evaluation
        non_ai_p95_compliant = api_lat["p95"] <= 500.0 if api_lat["samples"] > 0 else True
        ai_p95_compliant = ai_lat["p95"] <= 3000.0 if ai_lat["samples"] > 0 else True

        error_rate = (
            round((self._total_errors / self._total_requests) * 100, 2)
            if self._total_requests > 0
            else 0.0
        )

        return {
            "uptime_seconds": uptime_seconds,
            "system_timestamp": datetime.now(timezone.utc).isoformat(),
            "http_requests": {
                "total": self._total_requests,
                "status_counts": self._status_counts,
                "error_rate_percent": error_rate,
            },
            "latency_metrics": {
                "non_ai_api": {
                    **api_lat,
                    "target_p95_ms": 500.0,
                    "target_met": non_ai_p95_compliant,
                },
                "ai_conversational_turn": {
                    **ai_lat,
                    "target_p95_ms": 3000.0,
                    "target_met": ai_p95_compliant,
                },
                "stt_voice_intake": stt_lat,
                "tts_speech_synthesis": tts_lat,
            },
            "ai_call_metrics": {
                "total_ai_calls": self._ai_total_calls,
                "fallback_count": self._ai_fallback_count,
                "fallback_rate_percent": (
                    round((self._ai_fallback_count / self._ai_total_calls) * 100, 2)
                    if self._ai_total_calls > 0
                    else 0.0
                ),
                "provider_distribution": self._ai_provider_counts,
                "token_usage": self._ai_tokens,
                "provider_errors": self._ai_errors,
            },
        }


# Global singleton collector
telemetry_collector = TelemetryCollector()


class ObservabilityMiddleware(BaseHTTPMiddleware):
    """Starlette middleware providing request correlation and latency telemetry."""

    async def dispatch(self, request: Request, call_next) -> Response:
        # 1. Resolve or generate Request ID
        req_id = request.headers.get("X-Request-ID")
        if not req_id:
            req_id = f"req_{uuid.uuid4().hex[:12]}"

        # Set in context variable and request.state
        token = current_request_id.set(req_id)
        request.state.request_id = req_id

        start_time = time.perf_counter()
        status_code = 500

        try:
            response: Response = await call_next(request)
            status_code = response.status_code
        except Exception:
            status_code = 500
            raise
        finally:
            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)

            # Record telemetry
            telemetry_collector.record_request(
                method=request.method,
                path=request.url.path,
                status_code=status_code,
                latency_ms=latency_ms,
            )

            # Log structured access event if not health check spam
            if request.url.path not in ("/health", "/api/v1/observability/health"):
                logger.info(
                    f"{request.method} {request.url.path} {status_code} ({latency_ms}ms)",
                    extra={
                        "request_id": req_id,
                        "method": request.method,
                        "path": request.url.path,
                        "status_code": status_code,
                        "latency_ms": latency_ms,
                    },
                )

            current_request_id.reset(token)

        # Inject correlation and timing headers into response
        response.headers["X-Request-ID"] = req_id
        response.headers["X-Response-Time"] = f"{latency_ms}ms"

        return response


async def check_database_health() -> Dict[str, Any]:
    """Execute a lightweight async ping against PostgreSQL database."""
    from app.database import AsyncSessionLocal
    from sqlalchemy import text

    if not AsyncSessionLocal:
        return {"status": "unhealthy", "latency_ms": 0.0, "details": "AsyncSessionLocal not configured"}

    t0 = time.perf_counter()
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        latency = round((time.perf_counter() - t0) * 1000, 2)
        return {"status": "healthy", "latency_ms": latency, "details": "PostgreSQL connection operational"}
    except Exception as exc:
        latency = round((time.perf_counter() - t0) * 1000, 2)
        return {"status": "unhealthy", "latency_ms": latency, "details": str(exc)}


def check_ai_mesh_health() -> Dict[str, Any]:
    """Inspect AI provider mesh status and environment keys."""
    has_nvidia = bool(os.getenv("NVIDIA_API_KEY") or os.getenv("LLM_API_KEY"))
    has_gemini = bool(os.getenv("GEMINI_API_KEY"))
    has_groq = bool(os.getenv("GROQ_API_KEY"))
    has_elevenlabs = bool(os.getenv("ELEVENLABS_API_KEY"))

    active_llm = "nvidia" if has_nvidia else ("gemini" if has_gemini else "mock_resilient")
    fallback_llm = "gemini" if (has_nvidia and has_gemini) else "mock"

    return {
        "status": "healthy",
        "primary_llm": active_llm,
        "fallback_llm": fallback_llm,
        "providers": {
            "nvidia_nim": {"configured": has_nvidia, "status": "active" if has_nvidia else "mock_fallback"},
            "gemini_flash": {"configured": has_gemini, "status": "active" if has_gemini else "mock_fallback"},
            "groq_whisper": {"configured": has_groq, "status": "active" if has_groq else "simulated_active"},
            "elevenlabs": {"configured": has_elevenlabs, "status": "active" if has_elevenlabs else "simulated_active"},
        },
        "resilience_mesh_ready": True,
    }
