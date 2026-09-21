"""RBAC (Role-Based Access Control) module."""

from enum import Enum

from fastapi import Depends, HTTPException, status

from app.models import User, UserRole
from app.services.auth.service import get_current_active_user


class Permission(str, Enum):
    """System permissions."""
    # Patient permissions
    PATIENT_READ_OWN = "patient:read_own"
    PATIENT_UPDATE_OWN = "patient:update_own"
    PATIENT_CREATE_OWN = "patient:create_own"
    
    # Doctor permissions
    DOCTOR_READ_PATIENTS = "doctor:read_patients"
    DOCTOR_CREATE_MEDICAL_RECORDS = "doctor:create_medical_records"
    DOCTOR_UPDATE_MEDICAL_RECORDS = "doctor:update_medical_records"
    DOCTOR_CREATE_PRESCRIPTIONS = "doctor:create_prescriptions"
    DOCTOR_READ_APPOINTMENTS = "doctor:read_appointments"
    DOCTOR_UPDATE_APPOINTMENTS = "doctor:update_appointments"
    
    # Admin permissions
    ADMIN_READ_ALL = "admin:read_all"
    ADMIN_WRITE_ALL = "admin:write_all"
    ADMIN_MANAGE_USERS = "admin:manage_users"
    ADMIN_VIEW_AUDIT_LOGS = "admin:view_audit_logs"
    ADMIN_MANAGE_CONSENTS = "admin:manage_consents"
    
    # Nurse permissions
    NURSE_READ_PATIENTS = "nurse:read_patients"
    NURSE_UPDATE_PATIENTS = "nurse:update_patients"
    NURSE_READ_APPOINTMENTS = "nurse:read_appointments"
    
    # Receptionist permissions
    RECEPTIONIST_READ_APPOINTMENTS = "receptionist:read_appointments"
    RECEPTIONIST_CREATE_APPOINTMENTS = "receptionist:create_appointments"
    RECEPTIONIST_UPDATE_APPOINTMENTS = "receptionist:update_appointments"
    RECEPTIONIST_READ_PATIENTS = "receptionist:read_patients"

    # Super Admin permissions (Multi-Tenant Cross-Organization Governance)
    SUPER_ADMIN_MANAGE_ORGS = "super_admin:manage_orgs"
    SUPER_ADMIN_DELETE_ORGS = "super_admin:delete_orgs"
    SUPER_ADMIN_ALL = "super_admin:all"


# Central permissions matrix: role -> set of permissions
ROLE_PERMISSIONS: dict[UserRole, set[Permission]] = {
    UserRole.PATIENT: {
        Permission.PATIENT_READ_OWN,
        Permission.PATIENT_UPDATE_OWN,
        Permission.PATIENT_CREATE_OWN,
    },
    UserRole.DOCTOR: {
        Permission.DOCTOR_READ_PATIENTS,
        Permission.DOCTOR_CREATE_MEDICAL_RECORDS,
        Permission.DOCTOR_UPDATE_MEDICAL_RECORDS,
        Permission.DOCTOR_CREATE_PRESCRIPTIONS,
        Permission.DOCTOR_READ_APPOINTMENTS,
        Permission.DOCTOR_UPDATE_APPOINTMENTS,
        # Doctors can also read their own patient data
        Permission.PATIENT_READ_OWN,
    },
    UserRole.HEAD_PHYSICIAN: {
        Permission.DOCTOR_READ_PATIENTS,
        Permission.DOCTOR_CREATE_MEDICAL_RECORDS,
        Permission.DOCTOR_UPDATE_MEDICAL_RECORDS,
        Permission.DOCTOR_CREATE_PRESCRIPTIONS,
        Permission.DOCTOR_READ_APPOINTMENTS,
        Permission.DOCTOR_UPDATE_APPOINTMENTS,
        Permission.PATIENT_READ_OWN,
    },
    UserRole.ADMIN: {
        # Strict Administrative Governance boundary (HIPAA & ABDM principle of least privilege)
        Permission.ADMIN_READ_ALL,
        Permission.ADMIN_WRITE_ALL,
        Permission.ADMIN_MANAGE_USERS,
        Permission.ADMIN_VIEW_AUDIT_LOGS,
        Permission.ADMIN_MANAGE_CONSENTS,
    },
    UserRole.SUPER_ADMIN: {
        Permission.ADMIN_READ_ALL,
        Permission.ADMIN_WRITE_ALL,
        Permission.ADMIN_MANAGE_USERS,
        Permission.ADMIN_VIEW_AUDIT_LOGS,
        Permission.ADMIN_MANAGE_CONSENTS,
        Permission.SUPER_ADMIN_MANAGE_ORGS,
        Permission.SUPER_ADMIN_DELETE_ORGS,
        Permission.SUPER_ADMIN_ALL,
    },
    UserRole.NURSE: {
        Permission.NURSE_READ_PATIENTS,
        Permission.NURSE_UPDATE_PATIENTS,
        Permission.NURSE_READ_APPOINTMENTS,
        Permission.PATIENT_READ_OWN,
    },
    UserRole.HEAD_NURSE: {
        Permission.NURSE_READ_PATIENTS,
        Permission.NURSE_UPDATE_PATIENTS,
        Permission.NURSE_READ_APPOINTMENTS,
        Permission.PATIENT_READ_OWN,
    },
    UserRole.RECEPTIONIST: {
        Permission.RECEPTIONIST_READ_APPOINTMENTS,
        Permission.RECEPTIONIST_CREATE_APPOINTMENTS,
        Permission.RECEPTIONIST_UPDATE_APPOINTMENTS,
        Permission.RECEPTIONIST_READ_PATIENTS,
        Permission.PATIENT_READ_OWN,
    },
}


def get_user_permissions(user: User) -> set[Permission]:
    """Get all permissions for a user based on their role."""
    return ROLE_PERMISSIONS.get(user.role, set())


def has_permission(user: User, permission: Permission) -> bool:
    """Check if user has a specific permission."""
    user_permissions = get_user_permissions(user)
    return permission in user_permissions


def require_permission(permission: Permission):
    """FastAPI dependency that requires a specific permission."""
    async def permission_checker(current_user: User = Depends(get_current_active_user)) -> User:
        if not has_permission(current_user, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required: {permission.value}",
            )
        return current_user
    return permission_checker


def require_roles(*roles: UserRole):
    """FastAPI dependency that requires one of the specified roles."""
    async def role_checker(current_user: User = Depends(get_current_active_user)) -> User:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required roles: {[r.value for r in roles]}",
            )
        return current_user
    return role_checker


# Convenience dependencies for common role requirements
require_patient = require_roles(UserRole.PATIENT)
require_doctor = require_roles(UserRole.DOCTOR, UserRole.HEAD_PHYSICIAN)
require_head_physician = require_roles(UserRole.HEAD_PHYSICIAN)
require_head_nurse = require_roles(UserRole.HEAD_NURSE)
require_clinical_lead = require_roles(UserRole.HEAD_PHYSICIAN, UserRole.HEAD_NURSE, UserRole.ADMIN, UserRole.SUPER_ADMIN)
require_super_admin = require_roles(UserRole.SUPER_ADMIN)
require_admin = require_roles(UserRole.ADMIN, UserRole.SUPER_ADMIN)
require_nurse = require_roles(UserRole.NURSE, UserRole.HEAD_NURSE)
require_receptionist = require_roles(UserRole.RECEPTIONIST)

# Doctor or admin
require_doctor_or_admin = require_roles(UserRole.DOCTOR, UserRole.HEAD_PHYSICIAN, UserRole.ADMIN, UserRole.SUPER_ADMIN)

# Medical staff (doctor, nurse, admin)
require_medical_staff = require_roles(UserRole.DOCTOR, UserRole.HEAD_PHYSICIAN, UserRole.NURSE, UserRole.HEAD_NURSE, UserRole.ADMIN, UserRole.SUPER_ADMIN)

# Staff (doctor, nurse, admin, receptionist)
require_staff = require_roles(UserRole.DOCTOR, UserRole.HEAD_PHYSICIAN, UserRole.NURSE, UserRole.HEAD_NURSE, UserRole.ADMIN, UserRole.RECEPTIONIST, UserRole.SUPER_ADMIN)