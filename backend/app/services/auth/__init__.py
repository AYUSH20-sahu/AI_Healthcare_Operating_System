"""Auth service package."""

from app.services.auth.audit import (
    AuditLogger,
    AuditLoggingMiddleware,
)
from app.services.auth.consent import (
    get_active_consents_for_patient,
    get_all_consents_for_patient,
    get_consent_by_id,
    grant_consent,
    revoke_consent,
)
from app.services.auth.rbac import (
    ROLE_PERMISSIONS,
    Permission,
    get_user_permissions,
    has_permission,
    require_admin,
    require_doctor,
    require_doctor_or_admin,
    require_medical_staff,
    require_nurse,
    require_patient,
    require_permission,
    require_receptionist,
    require_roles,
    require_staff,
)

__all__ = [
    "ROLE_PERMISSIONS",
    "AuditLogger",
    "AuditLoggingMiddleware",
    "Permission",
    "get_active_consents_for_patient",
    "get_all_consents_for_patient",
    "get_consent_by_id",
    "get_user_permissions",
    "grant_consent",
    "has_permission",
    "require_admin",
    "require_doctor",
    "require_doctor_or_admin",
    "require_medical_staff",
    "require_nurse",
    "require_patient",
    "require_permission",
    "require_receptionist",
    "require_roles",
    "require_staff",
    "revoke_consent",
]