"""Comprehensive Security Hardening Test Suite (Milestone U-23)."""

from datetime import timedelta
import pytest
from httpx import AsyncClient

from app.core.security import (
    rate_limiter,
    sanitize_filename,
    validate_file_upload,
    validate_password_strength,
)
from app.main import app
from app.services.auth.service import create_refresh_token


@pytest.fixture(autouse=True)
def reset_limiter():
    """Reset in-memory rate limiter state before each test."""
    rate_limiter.reset()
    yield
    rate_limiter.reset()


@pytest.mark.asyncio
async def test_security_headers_present():
    """Verify standard defense-in-depth OWASP security headers on all responses."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        res = await client.get("/health")
        assert res.status_code == 200
        headers = res.headers
        assert headers.get("X-Content-Type-Options") == "nosniff"
        assert headers.get("X-Frame-Options") == "DENY"
        assert headers.get("X-XSS-Protection") == "1; mode=block"
        assert "Strict-Transport-Security" in headers
        assert "Referrer-Policy" in headers
        assert "Permissions-Policy" in headers
        assert "Content-Security-Policy" in headers


@pytest.mark.asyncio
async def test_cors_preflight_and_headers():
    """Verify CORS middleware responds with authorized origin and exposed headers."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        res = await client.options(
            "/api/v1/patients/",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "authorization,content-type",
            },
        )
        assert res.status_code == 200
        assert res.headers.get("Access-Control-Allow-Origin") == "http://localhost:3000"
        assert res.headers.get("Access-Control-Allow-Credentials") == "true"
        exposed = res.headers.get("Access-Control-Expose-Headers", "")
        assert "X-Request-ID" in exposed


@pytest.mark.asyncio
async def test_rate_limiting_enforcement():
    """Verify rate limiter middleware triggers HTTP 429 when threshold exceeded."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Auth limit is 20 requests per minute
        # Send 25 rapid requests from the same test client
        hit_429 = False
        retry_header = None

        for _ in range(25):
            res = await client.post(
                "/api/v1/auth/login",
                json={"email": "nonexistent@test.com", "password": "wrongpassword123"},
            )
            if res.status_code == 429:
                hit_429 = True
                retry_header = res.headers.get("Retry-After")
                data = res.json()
                assert "error" in data
                assert data["error"]["code"] == "RATE_LIMITED"
                break

        assert hit_429 is True
        assert retry_header is not None
        assert int(retry_header) >= 1


@pytest.mark.asyncio
async def test_password_strength_enforcement():
    """Verify registration endpoint rejects short or trivial passwords."""
    # 1. Short password (< 8 chars)
    valid, msg = validate_password_strength("short")
    assert valid is False
    assert "8 characters" in msg

    # 2. Trivial password
    valid_triv, msg_triv = validate_password_strength("password123")
    assert valid_triv is False
    assert "too common" in msg_triv

    # 3. Secure password
    valid_ok, _ = validate_password_strength("StrongClinicalP@ssw0rd99!")
    assert valid_ok is True

    # 4. API level test
    async with AsyncClient(app=app, base_url="http://test") as client:
        res = await client.post(
            "/api/v1/auth/signup",
            json={
                "email": "weakpass_user@test.com",
                "password": "123",  # Too short
                "full_name": "Test Weak Password",
            },
        )
        assert res.status_code == 400
        assert "8 characters" in res.json().get("detail", "")


@pytest.mark.asyncio
async def test_jwt_token_type_hardening():
    """Verify refresh token cannot be used to authenticate access-protected endpoints."""
    # Generate a refresh token
    refresh_tok = create_refresh_token(data={"sub": "00000000-0000-0000-0000-000000000001", "role": "patient"})

    async with AsyncClient(app=app, base_url="http://test") as client:
        # Attempt to access /auth/me with refresh token
        res = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {refresh_tok}"},
        )
        # Must be rejected because token type is 'refresh', not 'access'
        assert res.status_code == 401
        assert "Could not validate credentials" in res.json().get("detail", "")


def test_filename_sanitization_defense():
    """Verify sanitize_filename blocks directory traversal, null bytes, and dangerous characters."""
    # Directory traversal
    assert sanitize_filename("../../../etc/passwd") == "passwd"
    assert sanitize_filename("..\\..\\windows\\system32\\cmd.exe") == "windows_system32_cmd.exe"
    
    # Null byte injection
    assert sanitize_filename("malicious\x00file.exe.pdf") == "maliciousfile.exe.pdf"
    
    # Leading hidden file attempt
    assert sanitize_filename("...hidden.png") == "hidden.png"
    assert sanitize_filename("normal_report_2026.pdf") == "normal_report_2026.pdf"


def test_file_upload_validation_and_magic_bytes():
    """Verify validate_file_upload enforces size, extension, MIME, and binary magic bytes."""
    from fastapi import HTTPException

    # 1. Valid PDF with proper magic bytes
    valid_pdf = b"%PDF-1.4\n%test pdf content"
    validate_file_upload(
        file_bytes=valid_pdf,
        filename="report.pdf",
        content_type="application/pdf",
        max_size_bytes=10 * 1024 * 1024,
        allowed_mimes={"application/pdf"},
        allowed_extensions={"pdf"},
    )  # Should not raise

    # 2. Spoofed PDF (has .pdf extension but binary content is plain text script)
    fake_pdf = b"<html><script>alert('xss')</script></html>"
    with pytest.raises(HTTPException) as exc_spoof:
        validate_file_upload(
            file_bytes=fake_pdf,
            filename="spoofed.pdf",
            content_type="application/pdf",
            max_size_bytes=10 * 1024 * 1024,
            allowed_mimes={"application/pdf"},
            allowed_extensions={"pdf"},
        )
    assert exc_spoof.value.status_code == 400
    assert "binary header" in exc_spoof.value.detail

    # 3. Oversized file
    oversized = b"0" * (11 * 1024 * 1024)
    with pytest.raises(HTTPException) as exc_size:
        validate_file_upload(
            file_bytes=oversized,
            filename="large.pdf",
            content_type="application/pdf",
            max_size_bytes=10 * 1024 * 1024,
            allowed_mimes={"application/pdf"},
            allowed_extensions={"pdf"},
        )
    assert exc_size.value.status_code == 400
    assert "maximum allowed limit" in exc_size.value.detail
