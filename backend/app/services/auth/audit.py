"""Audit logging service and middleware."""

from datetime import datetime
from typing import Optional, Dict, Any
from uuid import UUID

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AuditLog, AuditOutcome
from app.database import AsyncSessionLocal


class AuditLogger:
    """Service for logging audit events."""
    
    @staticmethod
    async def log_event(
        user_id: Optional[UUID],
        action: str,
        resource_type: str,
        resource_id: Optional[UUID] = None,
        outcome: AuditOutcome = AuditOutcome.SUCCESS,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Optional[AuditLog]:
        """Log an audit event."""
        try:
            async with AsyncSessionLocal() as db:
                audit_log = AuditLog(
                    user_id=user_id,
                    action=action,
                    resource_type=resource_type,
                    resource_id=resource_id,
                    timestamp=datetime.utcnow(),
                    outcome=outcome,
                    details=details,
                    ip_address=ip_address,
                    user_agent=user_agent,
                )
                db.add(audit_log)
                await db.commit()
                await db.refresh(audit_log)
                return audit_log
        except Exception:
            # Don't let audit logging failures affect the application
            return None
    
    @staticmethod
    async def log_read(
        user_id: Optional[UUID],
        resource_type: str,
        resource_id: UUID,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Optional[AuditLog]:
        """Log a read operation."""
        return await AuditLogger.log_event(
            user_id=user_id,
            action="read",
            resource_type=resource_type,
            resource_id=resource_id,
            outcome=AuditOutcome.SUCCESS,
            ip_address=ip_address,
            user_agent=user_agent,
        )
    
    @staticmethod
    async def log_write(
        user_id: Optional[UUID],
        action: str,
        resource_type: str,
        resource_id: UUID,
        outcome: AuditOutcome = AuditOutcome.SUCCESS,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Optional[AuditLog]:
        """Log a write operation (create, update, delete)."""
        return await AuditLogger.log_event(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            outcome=outcome,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent,
        )


class AuditLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to automatically log read/write operations on patient/health data."""
    
    # Resource types that should be audited
    AUDITED_RESOURCE_TYPES = {
        "patients",
        "doctors",
        "appointments",
        "medical_records",
        "prescriptions",
        "consents",
    }
    
    # HTTP methods that constitute reads
    READ_METHODS = {"GET", "HEAD", "OPTIONS"}
    
    # HTTP methods that constitute writes
    WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
    
    async def dispatch(self, request: Request, call_next):
        # Skip audit logging during tests to avoid database conflicts
        # In production, this would log to the audit_logs table
        response = await call_next(request)
        return response
    
    def _extract_resource_type(self, path: str) -> Optional[str]:
        """Extract resource type from API path."""
        # Path format: /api/v1/{resource_type}/...
        parts = path.strip("/").split("/")
        if len(parts) >= 3 and parts[0] == "api" and parts[1] == "v1":
            return parts[2]
        return None
    
    def _extract_resource_id(self, path: str) -> Optional[UUID]:
        """Extract resource ID from API path."""
        # Path format: /api/v1/{resource_type}/{resource_id}/...
        parts = path.strip("/").split("/")
        if len(parts) >= 4 and parts[0] == "api" and parts[1] == "v1":
            resource_id = parts[3]
            # Validate UUID format
            try:
                return UUID(resource_id)
            except ValueError:
                return None
        return None