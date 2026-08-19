"""Auth service package."""

from app.services.auth.rbac import (
    Permission,
    ROLE_PERMISSIONS,
    get_user_permissions,
    has_permission,
    require_permission,
    require_roles,
    require_patient,
    require_doctor,
    require_admin,
    require_nurse,
    require_receptionist,
    require_doctor_or_admin,
    require_medical_staff,
    require_staff,
)

from app.services.auth.consent import (
    grant_consent,
    revoke_consent,
    get_active_consents_for_patient,
    get_all_consents_for_patient,
    get_consent_by_id,
)

from app.services.auth.audit import (
    AuditLogger,
    AuditLoggingMiddleware,
)

__all__ = [
    "Permission",
    "ROLE_PERMISSIONS",
    "get_user_permissions",
    "has_permission",
    "require_permission",
    "require_roles",
    "require_patient",
    "require_doctor",
    "require_admin",
    "require_nurse",
    "require_receptionist",
    "require_doctor_or_admin",
    "require_medical_staff",
    "require_staff",
    "grant_consent",
    "revoke_consent",
    "get_active_consents_for_patient",
    "get_all_consents_for_patient",
    "get_consent_by_id",
    "AuditLogger",
    "AuditLoggingMiddleware",
]