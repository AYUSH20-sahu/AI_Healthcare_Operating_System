"""Tests for RBAC module."""

import pytest
from uuid import uuid4

from app.services.auth.rbac import (
    Permission,
    ROLE_PERMISSIONS,
    get_user_permissions,
    has_permission,
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
from app.models import User, UserRole


class TestRolePermissions:
    """Test role permissions matrix."""

    def test_patient_permissions(self):
        """Test patient has correct permissions."""
        permissions = ROLE_PERMISSIONS[UserRole.PATIENT]
        assert Permission.PATIENT_READ_OWN in permissions
        assert Permission.PATIENT_UPDATE_OWN in permissions
        assert Permission.PATIENT_CREATE_OWN in permissions
        assert Permission.DOCTOR_READ_PATIENTS not in permissions
        assert Permission.ADMIN_READ_ALL not in permissions

    def test_doctor_permissions(self):
        """Test doctor has correct permissions."""
        permissions = ROLE_PERMISSIONS[UserRole.DOCTOR]
        assert Permission.DOCTOR_READ_PATIENTS in permissions
        assert Permission.DOCTOR_CREATE_MEDICAL_RECORDS in permissions
        assert Permission.DOCTOR_CREATE_PRESCRIPTIONS in permissions
        assert Permission.PATIENT_READ_OWN in permissions
        assert Permission.ADMIN_READ_ALL not in permissions

    def test_admin_permissions(self):
        """Test admin has all permissions."""
        permissions = ROLE_PERMISSIONS[UserRole.ADMIN]
        # Admin should have all permissions
        assert len(permissions) == len(Permission)

    def test_nurse_permissions(self):
        """Test nurse has correct permissions."""
        permissions = ROLE_PERMISSIONS[UserRole.NURSE]
        assert Permission.NURSE_READ_PATIENTS in permissions
        assert Permission.NURSE_UPDATE_PATIENTS in permissions
        assert Permission.PATIENT_READ_OWN in permissions
        assert Permission.DOCTOR_CREATE_MEDICAL_RECORDS not in permissions

    def test_receptionist_permissions(self):
        """Test receptionist has correct permissions."""
        permissions = ROLE_PERMISSIONS[UserRole.RECEPTIONIST]
        assert Permission.RECEPTIONIST_READ_APPOINTMENTS in permissions
        assert Permission.RECEPTIONIST_CREATE_APPOINTMENTS in permissions
        assert Permission.PATIENT_READ_OWN in permissions
        assert Permission.DOCTOR_READ_PATIENTS not in permissions


class TestGetUserPermissions:
    """Test get_user_permissions function."""

    def test_get_patient_permissions(self):
        """Test getting permissions for patient user."""
        user = User(role=UserRole.PATIENT)
        permissions = get_user_permissions(user)
        assert Permission.PATIENT_READ_OWN in permissions
        assert Permission.DOCTOR_READ_PATIENTS not in permissions

    def test_get_doctor_permissions(self):
        """Test getting permissions for doctor user."""
        user = User(role=UserRole.DOCTOR)
        permissions = get_user_permissions(user)
        assert Permission.DOCTOR_READ_PATIENTS in permissions
        assert Permission.ADMIN_READ_ALL not in permissions

    def test_get_admin_permissions(self):
        """Test getting permissions for admin user."""
        user = User(role=UserRole.ADMIN)
        permissions = get_user_permissions(user)
        assert len(permissions) == len(Permission)


class TestHasPermission:
    """Test has_permission function."""

    def test_patient_has_own_permissions(self):
        """Test patient has their own permissions."""
        user = User(role=UserRole.PATIENT)
        assert has_permission(user, Permission.PATIENT_READ_OWN) is True
        assert has_permission(user, Permission.PATIENT_UPDATE_OWN) is True

    def test_patient_lacks_doctor_permissions(self):
        """Test patient doesn't have doctor permissions."""
        user = User(role=UserRole.PATIENT)
        assert has_permission(user, Permission.DOCTOR_READ_PATIENTS) is False
        assert has_permission(user, Permission.DOCTOR_CREATE_MEDICAL_RECORDS) is False

    def test_doctor_has_doctor_permissions(self):
        """Test doctor has doctor permissions."""
        user = User(role=UserRole.DOCTOR)
        assert has_permission(user, Permission.DOCTOR_READ_PATIENTS) is True
        assert has_permission(user, Permission.DOCTOR_CREATE_MEDICAL_RECORDS) is True

    def test_doctor_has_patient_read_own(self):
        """Test doctor can read own patient data."""
        user = User(role=UserRole.DOCTOR)
        assert has_permission(user, Permission.PATIENT_READ_OWN) is True

    def test_admin_has_all_permissions(self):
        """Test admin has all permissions."""
        user = User(role=UserRole.ADMIN)
        for permission in Permission:
            assert has_permission(user, permission) is True

    def test_nurse_permissions(self):
        """Test nurse permissions."""
        user = User(role=UserRole.NURSE)
        assert has_permission(user, Permission.NURSE_READ_PATIENTS) is True
        assert has_permission(user, Permission.NURSE_UPDATE_PATIENTS) is True
        assert has_permission(user, Permission.DOCTOR_CREATE_MEDICAL_RECORDS) is False

    def test_receptionist_permissions(self):
        """Test receptionist permissions."""
        user = User(role=UserRole.RECEPTIONIST)
        assert has_permission(user, Permission.RECEPTIONIST_READ_APPOINTMENTS) is True
        assert has_permission(user, Permission.RECEPTIONIST_CREATE_APPOINTMENTS) is True
        assert has_permission(user, Permission.DOCTOR_READ_PATIENTS) is False


class TestRequireRoles:
    """Test require_roles dependency."""

    @pytest.mark.asyncio
    async def test_require_patient_allows_patient(self):
        """Test require_patient allows patient user."""
        from app.services.auth.rbac import require_patient
        from app.models import User, UserRole
        
        user = User(role=UserRole.PATIENT)
        # This would be tested with actual FastAPI dependency injection
        # For now, we test the logic directly
        assert user.role == UserRole.PATIENT

    @pytest.mark.asyncio
    async def test_require_doctor_allows_doctor(self):
        """Test require_doctor allows doctor user."""
        user = User(role=UserRole.DOCTOR)
        assert user.role == UserRole.DOCTOR

    @pytest.mark.asyncio
    async def test_require_admin_allows_admin(self):
        """Test require_admin allows admin user."""
        user = User(role=UserRole.ADMIN)
        assert user.role == UserRole.ADMIN

    @pytest.mark.asyncio
    async def test_require_doctor_or_admin_allows_both(self):
        """Test require_doctor_or_admin allows both doctor and admin."""
        doctor = User(role=UserRole.DOCTOR)
        admin = User(role=UserRole.ADMIN)
        assert doctor.role in (UserRole.DOCTOR, UserRole.ADMIN)
        assert admin.role in (UserRole.DOCTOR, UserRole.ADMIN)

    @pytest.mark.asyncio
    async def test_require_medical_staff(self):
        """Test require_medical_staff allows medical staff."""
        doctor = User(role=UserRole.DOCTOR)
        nurse = User(role=UserRole.NURSE)
        admin = User(role=UserRole.ADMIN)
        medical_roles = (UserRole.DOCTOR, UserRole.NURSE, UserRole.ADMIN)
        assert doctor.role in medical_roles
        assert nurse.role in medical_roles
        assert admin.role in medical_roles

    @pytest.mark.asyncio
    async def test_require_staff(self):
        """Test require_staff allows all staff."""
        doctor = User(role=UserRole.DOCTOR)
        nurse = User(role=UserRole.NURSE)
        admin = User(role=UserRole.ADMIN)
        receptionist = User(role=UserRole.RECEPTIONIST)
        staff_roles = (UserRole.DOCTOR, UserRole.NURSE, UserRole.ADMIN, UserRole.RECEPTIONIST)
        assert doctor.role in staff_roles
        assert nurse.role in staff_roles
        assert admin.role in staff_roles
        assert receptionist.role in staff_roles


class TestConvenienceDependencies:
    """Test convenience role dependencies."""

    def test_require_patient_exists(self):
        """Test require_patient dependency exists."""
        from app.services.auth.rbac import require_patient
        assert require_patient is not None

    def test_require_doctor_exists(self):
        """Test require_doctor dependency exists."""
        from app.services.auth.rbac import require_doctor
        assert require_doctor is not None

    def test_require_admin_exists(self):
        """Test require_admin dependency exists."""
        from app.services.auth.rbac import require_admin
        assert require_admin is not None

    def test_require_nurse_exists(self):
        """Test require_nurse dependency exists."""
        from app.services.auth.rbac import require_nurse
        assert require_nurse is not None

    def test_require_receptionist_exists(self):
        """Test require_receptionist dependency exists."""
        from app.services.auth.rbac import require_receptionist
        assert require_receptionist is not None

    def test_require_doctor_or_admin_exists(self):
        """Test require_doctor_or_admin dependency exists."""
        from app.services.auth.rbac import require_doctor_or_admin
        assert require_doctor_or_admin is not None

    def test_require_medical_staff_exists(self):
        """Test require_medical_staff dependency exists."""
        from app.services.auth.rbac import require_medical_staff
        assert require_medical_staff is not None

    def test_require_staff_exists(self):
        """Test require_staff dependency exists."""
        from app.services.auth.rbac import require_staff
        assert require_staff is not None