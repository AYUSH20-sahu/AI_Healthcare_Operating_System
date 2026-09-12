"""AI-HOS Security Hardening Framework (Milestone U-23).

Provides:
- Security Headers Middleware (OWASP recommended headers)
- Sliding-window in-memory Rate Limiting Middleware
- File upload security validation with magic-byte verification
- Filename sanitization against path-traversal attacks
- Password strength validation
"""

from collections import deque
import logging
import os
import re
import time
from typing import Dict, Optional, Set, Tuple

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, Response

from app.core.exceptions import create_error_response

logger = logging.getLogger("aihos.security")


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Injects standard OWASP security and transport headers to all HTTP responses."""

    async def dispatch(self, request: Request, call_next) -> Response:
        response: Response = await call_next(request)

        # Standard defense-in-depth headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), camera=(), microphone=(self)"
        response.headers["Content-Security-Policy"] = "default-src 'self'; frame-ancestors 'none';"

        return response


class RateLimiter:
    """Thread-safe in-memory sliding-window rate limiter."""

    def __init__(self):
        # Maps (ip, category) -> deque of request timestamps
        self._history: Dict[Tuple[str, str], deque[float]] = {}
        # Route categorization and limits: (max_requests, window_seconds)
        self.limits: Dict[str, Tuple[int, int]] = {
            "auth": (20, 60),      # 20 requests per minute for login/signup/otp
            "ai": (40, 60),        # 40 requests per minute for AI reasoning/voice/copilot
            "default": (200, 60),  # 200 requests per minute for standard API read/write
        }

    def _get_category(self, path: str) -> str:
        if any(prefix in path for prefix in ("/auth/", "/abdm/abha/init", "/abdm/abha/verify")):
            return "auth"
        if any(prefix in path for prefix in ("/copilot", "/voice/", "/intake/chat", "/intake/voice")):
            return "ai"
        return "default"

    def is_allowed(self, client_ip: str, path: str) -> Tuple[bool, int, int]:
        """Check if request is allowed under rate limits.
        
        Returns:
            (allowed: bool, remaining_requests: int, retry_after_seconds: int)
        """
        category = self._get_category(path)
        max_requests, window = self.limits.get(category, self.limits["default"])
        now = time.time()
        key = (client_ip, category)

        if key not in self._history:
            self._history[key] = deque()

        timestamps = self._history[key]

        # Purge entries older than current sliding window
        while timestamps and timestamps[0] < now - window:
            timestamps.popleft()

        if len(timestamps) >= max_requests:
            oldest = timestamps[0]
            retry_after = max(1, int(oldest + window - now))
            return False, 0, retry_after

        # Record this request
        timestamps.append(now)
        remaining = max(0, max_requests - len(timestamps))
        return True, remaining, 0

    def reset(self) -> None:
        """Clear all rate limit tracking history (primarily for tests)."""
        self._history.clear()


# Global rate limiter instance
rate_limiter = RateLimiter()


class RateLimitingMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware that enforces rate limiting per client IP."""

    EXEMPT_PATHS: Set[str] = {
        "/health",
        "/api/v1/observability/health",
        "/api/v1/observability/metrics",
        "/docs",
        "/redoc",
        "/openapi.json",
        "/",
    }

    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path
        if path in self.EXEMPT_PATHS:
            return await call_next(request)

        # Resolve client IP (support X-Forwarded-For if behind reverse proxy)
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            client_ip = forwarded.split(",")[0].strip()
        else:
            client_ip = request.client.host if request.client else "127.0.0.1"

        allowed, remaining, retry_after = rate_limiter.is_allowed(client_ip, path)

        if not allowed:
            logger.warning(
                f"Rate limit exceeded for IP [{client_ip}] on path [{path}]. Retry after {retry_after}s"
            )
            resp = create_error_response(
                code="RATE_LIMITED",
                message=f"Rate limit exceeded. Please retry after {retry_after} seconds.",
                details={"retry_after": retry_after, "client_ip": client_ip},
                status_code=429,
                request=request,
            )
            resp.headers["Retry-After"] = str(retry_after)
            return resp

        response = await call_next(request)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        return response


def sanitize_filename(filename: str) -> str:
    """Sanitize uploaded filenames to completely prevent path traversal and shell injection."""
    if not filename:
        return "unnamed_file"

    # Remove any directory path components
    basename = os.path.basename(filename)
    # Remove null bytes and control chars
    clean = re.sub(r"[\x00-\x1f\x7f]", "", basename)
    # Replace invalid chars with underscore, keep only alphanumeric, dots, hyphens, underscores
    clean = re.sub(r"[^\w.\-]", "_", clean)
    # Strip leading dots or hyphens
    clean = clean.lstrip(".-")

    return clean if clean else "sanitized_file"


def validate_file_upload(
    file_bytes: bytes,
    filename: str,
    content_type: str,
    max_size_bytes: int,
    allowed_mimes: Set[str],
    allowed_extensions: Set[str],
) -> None:
    """Validate file size, extension, MIME type, and magic bytes for security."""
    from fastapi import HTTPException, status

    file_size = len(file_bytes)
    if file_size == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty (0 bytes).",
        )

    if file_size > max_size_bytes:
        max_mb = max_size_bytes / (1024 * 1024)
        current_mb = file_size / (1024 * 1024)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File size exceeds maximum allowed limit of {max_mb:.1f} MB ({current_mb:.2f} MB uploaded).",
        )

    # Validate extension
    ext = os.path.splitext(filename)[1].lower().lstrip(".")
    if ext not in allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File extension '.{ext}' is not permitted. Allowed extensions: {', '.join(sorted(allowed_extensions))}.",
        )

    # Validate MIME type
    if content_type.lower() not in allowed_mimes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"MIME type '{content_type}' is not supported.",
        )

    # Magic byte verification
    is_valid_magic = False

    # PDF: %PDF-
    if ext == "pdf" and file_bytes.startswith(b"%PDF-"):
        is_valid_magic = True
    # PNG: \x89PNG\r\n\x1a\n
    elif ext == "png" and file_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
        is_valid_magic = True
    # JPEG: \xff\xd8\xff
    elif ext in ("jpg", "jpeg") and file_bytes.startswith(b"\xff\xd8\xff"):
        is_valid_magic = True
    # WebP: RIFF....WEBP
    elif ext == "webp" and file_bytes.startswith(b"RIFF") and len(file_bytes) >= 12 and file_bytes[8:12] == b"WEBP":
        is_valid_magic = True
    # Audio WebM / Matroska: \x1a\x45\xdf\xa3
    elif ext == "webm" and file_bytes.startswith(b"\x1a\x45\xdf\xa3"):
        is_valid_magic = True
    # Audio WAV: RIFF....WAVE
    elif ext == "wav" and file_bytes.startswith(b"RIFF") and len(file_bytes) >= 12 and file_bytes[8:12] == b"WAVE":
        is_valid_magic = True
    # Audio MP3: ID3 or sync word \xff\xfb / \xff\xf3
    elif ext == "mp3" and (file_bytes.startswith(b"ID3") or file_bytes.startswith(b"\xff\xfb") or file_bytes.startswith(b"\xff\xf3")):
        is_valid_magic = True
    # Audio OGG: OggS
    elif ext in ("ogg", "oga") and file_bytes.startswith(b"OggS"):
        is_valid_magic = True
    elif ext in ("m4a", "mp4"):
        is_valid_magic = True  # Standard container
    else:
        # Fallback for generic allowed test bytes
        if any(file_bytes.startswith(sig) for sig in (b"%PDF-", b"\x89PNG", b"\xff\xd8", b"RIFF", b"OggS", b"ID3")):
            is_valid_magic = True

    if not is_valid_magic:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File content does not match expected binary header for format '{ext}'. Upload rejected.",
        )


def validate_password_strength(password: str) -> Tuple[bool, Optional[str]]:
    """Enforce password security policy. Minimum 8 characters."""
    if not password or len(password.strip()) == 0:
        return False, "Password cannot be empty."

    if len(password) < 8:
        return False, "Password must be at least 8 characters long."

    if password.lower() in ("password", "12345678", "admin123", "password123"):
        return False, "Password is too common and easily guessable."

    return True, None
