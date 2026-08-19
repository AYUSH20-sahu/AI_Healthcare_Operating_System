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
]