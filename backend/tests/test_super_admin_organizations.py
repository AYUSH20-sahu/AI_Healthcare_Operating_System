"""Tests for Super Admin, Multi-Tenant Organizations, and Dual-Credential Patient Authentication."""

import uuid
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.main import app
from app.models import Organization, Patient, User, UserRole
from app.services.auth.service import (
    authenticate_user,
    create_access_token,
    create_user,
    get_password_hash,
    UserCreate,
)


@pytest.mark.asyncio
class TestMultiTenantSuperAdminAndPatientAuth:
    """Test suite verifying Super Admin multi-tenancy and separated patient authentication."""

    async def test_patient_registration_with_email_and_phone(self, db_session):
        """Verify patient registers with both email and phone, creating dual credentials."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            res = await ac.post(
                "/api/v1/auth/patient/register",
                json={
                    "full_name": "Deepak Patel",
                    "email": "deepak.patel@example.com",
                    "phone": "+919876543210",
                    "password": "patientpassword123",
                },
            )
            assert res.status_code == 201
            data = res.json()
            assert data["email"] == "deepak.patel@example.com"
            assert data["phone"] == "+919876543210"
            assert data["role"] == "patient"

            # Verify User and Patient records in DB
            user_res = await db_session.execute(
                select(User).where(User.email == "deepak.patel@example.com")
            )
            user = user_res.scalar_one_or_none()
            assert user is not None
            assert user.phone == "+919876543210"

            patient_res = await db_session.execute(
                select(Patient).where(Patient.user_id == user.user_id)
            )
            patient = patient_res.scalar_one_or_none()
            assert patient is not None
            assert patient.phone == "+919876543210"

    async def test_patient_login_with_email_and_phone(self, db_session):
        """Verify patient can log in using either email or mobile phone number."""
        # Create test patient
        user = await create_user(
            db_session,
            UserCreate(
                email="anita.sharma@example.com",
                password="securepassword123",
                full_name="Anita Sharma",
                phone="+919811122233",
                role="patient",
            ),
            role="patient",
        )
        patient_profile = Patient(
            user_id=user.user_id,
            full_name=user.full_name,
            email=user.email,
            phone=user.phone,
        )
        db_session.add(patient_profile)
        await db_session.commit()

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            # 1. Login with Email
            res_email = await ac.post(
                "/api/v1/auth/patient/login",
                json={
                    "identifier": "anita.sharma@example.com",
                    "password": "securepassword123",
                },
            )
            assert res_email.status_code == 200
            assert "access_token" in res_email.json()

            # 2. Login with Mobile Phone Number
            res_phone = await ac.post(
                "/api/v1/auth/patient/login",
                json={
                    "identifier": "+919811122233",
                    "password": "securepassword123",
                },
            )
            assert res_phone.status_code == 200
            assert "access_token" in res_phone.json()

            # 3. Invalid credentials rejected
            res_fail = await ac.post(
                "/api/v1/auth/patient/login",
                json={
                    "identifier": "+919811122233",
                    "password": "wrongpassword",
                },
            )
            assert res_fail.status_code == 401

    async def test_super_admin_create_and_delete_organization(self, db_session):
        """Verify Super Admin can create a new organization with an admin, and delete it."""
        # Provision a Super Admin
        super_admin = User(
            user_id=uuid.uuid4(),
            email="global.superadmin@aihos.org",
            hashed_password=get_password_hash("superadminsecret123"),
            full_name="Chief Operating Officer",
            role=UserRole.SUPER_ADMIN,
            is_active=True,
        )
        db_session.add(super_admin)
        await db_session.commit()

        token = create_access_token(
            {"sub": str(super_admin.user_id), "email": super_admin.email, "role": "super_admin"}
        )
        headers = {"Authorization": f"Bearer {token}"}

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            # 1. Create Organization with Admin
            create_res = await ac.post(
                "/api/v1/admin/organizations/",
                headers=headers,
                json={
                    "name": "St. Jude Neuro Center",
                    "code": "SJNC-01",
                    "description": "Specialty Neurology Hospital",
                    "admin_name": "Dr. Marcus Vance",
                    "admin_email": "marcus.vance@stjude.org",
                    "admin_password": "adminpassword123",
                    "admin_phone": "+919899988877",
                },
            )
            assert create_res.status_code == 201
            org_data = create_res.json()
            org_id = org_data["organization_id"]
            assert org_data["name"] == "St. Jude Neuro Center"
            assert org_data["code"] == "SJNC-01"
            assert org_data["admin"]["email"] == "marcus.vance@stjude.org"

            # Verify Org Admin can authenticate
            admin_user = await authenticate_user(db_session, "marcus.vance@stjude.org", "adminpassword123")
            assert admin_user is not None
            assert admin_user.role == UserRole.ADMIN
            assert str(admin_user.organization_id) == str(org_id)

            # 2. Super Admin Lists Organizations
            list_res = await ac.get("/api/v1/admin/organizations/", headers=headers)
            assert list_res.status_code == 200
            listed_ids = [o["organization_id"] for o in list_res.json()]
            assert org_id in listed_ids

            # 3. Super Admin Deletes Organization & Its Admin
            del_res = await ac.delete(f"/api/v1/admin/organizations/{org_id}", headers=headers)
            assert del_res.status_code == 200

            # Verify Organization is gone
            org_check = await db_session.execute(
                select(Organization).where(Organization.organization_id == uuid.UUID(org_id))
            )
            assert org_check.scalar_one_or_none() is None

            # Verify Admin User was also deleted
            user_check = await db_session.execute(
                select(User).where(User.email == "marcus.vance@stjude.org")
            )
            assert user_check.scalar_one_or_none() is None

    async def test_org_admin_registration_flow(self, db_session):
        """Verify new user registration on main portal creates their own organization and sets them as admin."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            reg_res = await ac.post(
                "/api/v1/auth/register-org",
                json={
                    "admin_name": "Dr. Sarah Jenkins",
                    "email": "sarah.jenkins@cityclinic.org",
                    "phone": "+919877766655",
                    "password": "clinicadminpass123",
                    "organization_name": "City Care Specialty Clinic",
                    "organization_code": "CCSC-01",
                    "organization_address": "77 Avenue Health District",
                },
            )
            assert reg_res.status_code == 201
            user_data = reg_res.json()
            assert user_data["role"] == "admin"
            assert user_data["organization_id"] is not None

            # Verify Org Admin can log in
            login_res = await ac.post(
                "/api/v1/auth/login",
                json={
                    "identifier": "sarah.jenkins@cityclinic.org",
                    "password": "clinicadminpass123",
                },
            )
            assert login_res.status_code == 200
            assert "access_token" in login_res.json()
