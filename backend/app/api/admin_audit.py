"""Administrative Audit Log Query API (Milestone U-18).

Provides read-only, paginated, multi-filter inspection of the immutable audit trail.
Complies with FHIR-R4 AuditEvent specification, HIPAA security rules, and ABDM governance.
Access is strictly restricted to system administrators.
"""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import AuditLog, AuditOutcome, User, UserRole
from app.services.auth.rbac import require_admin

router = APIRouter(prefix="/admin/audit", tags=["admin-audit"])


# =============================================================================
# Schemas
# =============================================================================

class AuditLogItemResponse(BaseModel):
    """Detailed audit log item with operator metadata."""
    log_id: UUID
    user_id: Optional[UUID] = None
    user_email: Optional[str] = None
    user_name: Optional[str] = None
    user_role: Optional[str] = None
    action: str
    resource_type: str
    resource_id: Optional[UUID] = None
    timestamp: datetime
    outcome: str
    details: Optional[Dict[str, Any]] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None

    class Config:
        from_attributes = True


class AuditLogListResponse(BaseModel):
    """Paginated list of immutable audit log entries."""
    logs: List[AuditLogItemResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


# =============================================================================
# Endpoints (Strictly Read-Only)
# =============================================================================

@router.get("", response_model=AuditLogListResponse)
async def list_audit_logs(
    user_id: Optional[UUID] = Query(None, description="Filter by operator user ID"),
    action: Optional[str] = Query(None, description="Filter by event action (e.g. LOGIN, GRANT_CONSENT)"),
    resource_type: Optional[str] = Query(None, description="Filter by resource (users, appointments, consents, etc.)"),
    resource_id: Optional[UUID] = Query(None, description="Filter by specific resource ID"),
    outcome: Optional[str] = Query(None, description="Filter by outcome: SUCCESS, FAILURE, DENIED, ERROR"),
    start_date: Optional[datetime] = Query(None, description="Filter events after this timestamp"),
    end_date: Optional[datetime] = Query(None, description="Filter events before this timestamp"),
    search: Optional[str] = Query(None, description="Search across action, resource, operator email, or IP"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(require_admin),
):
    """Query the immutable system audit trail with multi-dimensional filtering and pagination."""
    query = (
        select(AuditLog, User)
        .outerjoin(User, AuditLog.user_id == User.user_id)
    )

    if user_id:
        query = query.where(AuditLog.user_id == user_id)

    if action and action.lower() != "all":
        query = query.where(AuditLog.action.ilike(f"%{action}%"))

    if resource_type and resource_type.lower() != "all":
        query = query.where(AuditLog.resource_type.ilike(resource_type.strip()))

    if resource_id:
        query = query.where(AuditLog.resource_id == resource_id)

    if outcome and outcome.lower() != "all":
        try:
            outcome_enum = AuditOutcome(outcome.lower())
            query = query.where(AuditLog.outcome == outcome_enum)
        except ValueError:
            pass

    if start_date:
        query = query.where(AuditLog.timestamp >= start_date)

    if end_date:
        query = query.where(AuditLog.timestamp <= end_date)

    if search:
        search_pattern = f"%{search}%"
        query = query.where(
            or_(
                AuditLog.action.ilike(search_pattern),
                AuditLog.resource_type.ilike(search_pattern),
                AuditLog.ip_address.ilike(search_pattern),
                User.email.ilike(search_pattern),
                User.full_name.ilike(search_pattern),
            )
        )

    # 1. Total count query
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar_one() or 0

    # 2. Paginated results sorted by timestamp descending
    offset = (page - 1) * page_size
    query = query.order_by(AuditLog.timestamp.desc()).offset(offset).limit(page_size)
    results = (await db.execute(query)).all()

    log_items = []
    for log, usr in results:
        log_items.append(
            AuditLogItemResponse(
                log_id=log.log_id,
                user_id=log.user_id,
                user_email=usr.email if usr else None,
                user_name=usr.full_name if usr else None,
                user_role=usr.role.value if usr and hasattr(usr.role, "value") else str(usr.role) if usr else None,
                action=log.action,
                resource_type=log.resource_type,
                resource_id=log.resource_id,
                timestamp=log.timestamp,
                outcome=log.outcome.value if hasattr(log.outcome, "value") else str(log.outcome),
                details=log.details,
                ip_address=log.ip_address,
                user_agent=log.user_agent,
            )
        )

    total_pages = (total + page_size - 1) // page_size if total > 0 else 1

    return AuditLogListResponse(
        logs=log_items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/{log_id}", response_model=AuditLogItemResponse)
async def get_audit_log_detail(
    log_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(require_admin),
):
    """Retrieve complete metadata and payload details for a single immutable audit entry."""
    query = (
        select(AuditLog, User)
        .outerjoin(User, AuditLog.user_id == User.user_id)
        .where(AuditLog.log_id == log_id)
    )
    res = (await db.execute(query)).first()
    if not res:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Audit log record not found",
        )

    log, usr = res
    return AuditLogItemResponse(
        log_id=log.log_id,
        user_id=log.user_id,
        user_email=usr.email if usr else None,
        user_name=usr.full_name if usr else None,
        user_role=usr.role.value if usr and hasattr(usr.role, "value") else str(usr.role) if usr else None,
        action=log.action,
        resource_type=log.resource_type,
        resource_id=log.resource_id,
        timestamp=log.timestamp,
        outcome=log.outcome.value if hasattr(log.outcome, "value") else str(log.outcome),
        details=log.details,
        ip_address=log.ip_address,
        user_agent=log.user_agent,
    )
