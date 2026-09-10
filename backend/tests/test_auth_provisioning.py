"""Full-stack test suite for Global Authentication & Account Provisioning Rule.

Validates all 16 acceptance criteria defined in lines 670-686 of Master Prompt v6:
1. Patient can register successfully.
2. Patient registration automatically creates PATIENT role.
3. Public registration cannot create DOCTOR.
4. Public registration cannot create ADMIN.
5. Public registration cannot create other privileged roles.
6. Doctor cannot access Admin APIs.
7. Patient cannot access Doctor APIs.
8. Patient cannot access Admin APIs.
9. Admin can provision Doctor accounts.
10. Admin can provision authorized staff accounts.
11. Unauthorized users cannot access provisioning endpoints.
12. Direct API manipulation cannot escalate privileges.
13. JWT tampering is rejected.
14. Admin can activate/deactivate user accounts.
15. Inactive user cannot authenticate/login.
16. Administrative actions are logged in immutable audit_logs.
"""

from uuid import uuid4

import pytest
from sqlalchemy import select

from app.models import AuditLog, Doctor, Patient, User, UserRole


@pytest.mark.asyncio
class TestGlobalAuthAndProvisioningRules:
    """Test suite strictly enforcing lines 480-686 of Master Prompt v6."""

    async def test_patient_can_register_successfully(self, client):
        """1. Patient can register successfully through public signup."""
        payload = {
            "email": "freshpatient@test.com",
            "password": "patientPassword123",
            "full_name": "Fresh Patient",
        }
        res = await client.post("/api/v1/auth/signup", json=payload)
        assert res.status_code == 201
        data = res.json()
        assert data["email"] == "freshpatient@test.com"
        assert data["role"] == "patient"
        assert data["is_active"] is True

    async def test_patient_registration_automatically_creates_patient_role_and_profile(
        self, client, db_session
    ):
        """2. Patient registration automatically creates PATIENT role and DB profile."""
        payload = {
            "email": "autopatient@test.com",
            "password": "patientPassword123",
            "full_name": "Auto Patient Profile",
        }
        res = await client.post("/api/v1/auth/signup", json=payload)
        assert res.status_code == 201
        data = res.json()
        assert data["role"] == "patient"

        # Verify DB role is strictly UserRole.PATIENT
        user_res = await db_session.execute(
            select(User).where(User.email == "autopatient@test.com")
        )
        user = user_res.scalar_one()
        assert user.role == UserRole.PATIENT

        # Verify patient demographic profile created
        patient_res = await db_session.execute(
            select(Patient).where(Patient.user_id == user.user_id)
        )
        patient_prof = patient_res.scalar_one_or_none()
        assert patient_prof is not None
        assert patient_prof.full_name == "Auto Patient Profile"

    async def test_public_registration_cannot_create_doctor(self, client, db_session):
        """3. Public registration cannot create DOCTOR even when client sends role=doctor."""
        payload = {
            "email": "hacker_doctor@test.com",
            "password": "hackerPassword123",
            "full_name": "Attacker Trying Doctor",
            "role": "doctor",  # Attacker attempts privilege escalation
        }
        res = await client.post("/api/v1/auth/signup", json=payload)
        assert res.status_code == 201
        data = res.json()
        # MUST be sanitized and forced to patient
        assert data["role"] == "patient"

        user_res = await db_session.execute(
            select(User).where(User.email == "hacker_doctor@test.com")
        )
        user = user_res.scalar_one()
        assert user.role == UserRole.PATIENT

    async def test_public_registration_cannot_create_admin(self, client, db_session):
        """4. Public registration cannot create ADMIN even when client sends role=admin."""
        payload = {
            "email": "hacker_admin@test.com",
            "password": "hackerPassword123",
            "full_name": "Attacker Trying Admin",
            "role": "admin",  # Attacker attempts privilege escalation
        }
        res = await client.post("/api/v1/auth/signup", json=payload)
        assert res.status_code == 201
        data = res.json()
        # MUST be sanitized and forced to patient
        assert data["role"] == "patient"

        user_res = await db_session.execute(
            select(User).where(User.email == "hacker_admin@test.com")
        )
        user = user_res.scalar_one()
        assert user.role == UserRole.PATIENT

    async def test_public_registration_cannot_create_other_privileged_roles(
        self, client, db_session
    ):
        """5. Public registration cannot create other privileged roles like nurse or receptionist."""
        for priv_role in ["nurse", "receptionist", "superadmin", "operator"]:
            payload = {
                "email": f"hacker_{priv_role}@test.com",
                "password": "hackerPassword123",
                "full_name": f"Attacker {priv_role}",
                "role": priv_role,
            }
            res = await client.post("/api/v1/auth/signup", json=payload)
            assert res.status_code == 201
            assert res.json()["role"] == "patient"

    async def test_doctor_cannot_access_admin_apis(self, client, doctor_token):
        """6. Doctor cannot access Admin APIs."""
        headers = {"Authorization": f"Bearer {doctor_token}"}
        res = await client.get("/api/v1/admin/users/", headers=headers)
        assert res.status_code == 403

    async def test_patient_cannot_access_doctor_apis(self, client, patient_token):
        """7. Patient cannot access Doctor creation/management APIs."""
        headers = {"Authorization": f"Bearer {patient_token}"}
        payload = {
            "full_name": "Dr. Patient Impersonator",
            "email": "impersonator@test.com",
            "specialty": "Neurology",
            "license_number": "MED-FAKE-001",
        }
        res = await client.post("/api/v1/doctors/", json=payload, headers=headers)
        assert res.status_code == 403

    async def test_patient_cannot_access_admin_apis(self, client, patient_token):
        """8. Patient cannot access Admin APIs."""
        headers = {"Authorization": f"Bearer {patient_token}"}
        res = await client.get("/api/v1/admin/users/", headers=headers)
        assert res.status_code == 403

    async def test_admin_can_provision_doctor_account(self, client, admin_token, db_session):
        """9. Admin can provision Doctor accounts with license and specialty."""
        headers = {"Authorization": f"Bearer {admin_token}"}
        payload = {
            "full_name": "Dr. Sunita Rao, MD",
            "email": "sunita.rao@hospital.org",
            "password": "clinicianSecurePassword123",
            "role": "doctor",
            "specialty": "Cardiology",
            "license_number": "MED-IND-778899",
            "hospital_affiliation": "AI-HOS Apollo Clinical Center",
            "phone": "+91-9876543210",
        }
        res = await client.post("/api/v1/admin/users/", json=payload, headers=headers)
        assert res.status_code == 201
        data = res.json()
        assert data["role"] == "doctor"
        assert data["email"] == "sunita.rao@hospital.org"
        assert data["doctor_profile"] is not None
        assert data["doctor_profile"]["specialty"] == "Cardiology"
        assert data["doctor_profile"]["license_number"] == "MED-IND-778899"

        # Verify DB records
        doc_res = await db_session.execute(
            select(Doctor).where(Doctor.license_number == "MED-IND-778899")
        )
        doc = doc_res.scalar_one_or_none()
        assert doc is not None
        assert doc.specialty == "Cardiology"

    async def test_admin_can_provision_authorized_staff_accounts(self, client, admin_token):
        """10. Admin can provision authorized staff accounts (Nurse, Receptionist)."""
        headers = {"Authorization": f"Bearer {admin_token}"}
        # Nurse
        nurse_payload = {
            "full_name": "Nurse Anjali Nair",
            "email": "anjali.nurse@hospital.org",
            "password": "nursePassword123",
            "role": "nurse",
        }
        res_nurse = await client.post("/api/v1/admin/users/", json=nurse_payload, headers=headers)
        assert res_nurse.status_code == 201
        assert res_nurse.json()["role"] == "nurse"

        # Receptionist
        receptionist_payload = {
            "full_name": "Rohan Deshmukh",
            "email": "rohan.frontdesk@hospital.org",
            "password": "staffPassword123",
            "role": "receptionist",
        }
        res_rec = await client.post("/api/v1/admin/users/", json=receptionist_payload, headers=headers)
        assert res_rec.status_code == 201
        assert res_rec.json()["role"] == "receptionist"

    async def test_unauthorized_users_cannot_access_provisioning_endpoints(
        self, client, doctor_token, patient_token
    ):
        """11. Unauthorized users (Doctor, Patient) cannot access provisioning endpoints."""
        payload = {
            "full_name": "Illegal User",
            "email": "illegal@hospital.org",
            "password": "illegalPassword123",
            "role": "doctor",
        }
        # Doctor attempt
        res_doc = await client.post(
            "/api/v1/admin/users/",
            json=payload,
            headers={"Authorization": f"Bearer {doctor_token}"},
        )
        assert res_doc.status_code == 403

        # Patient attempt
        res_pat = await client.post(
            "/api/v1/admin/users/",
            json=payload,
            headers={"Authorization": f"Bearer {patient_token}"},
        )
        assert res_pat.status_code == 403

    async def test_direct_api_manipulation_cannot_escalate_privileges(self, client):
        """12. Unauthenticated direct API call cannot provision accounts."""
        payload = {
            "full_name": "Direct Attacker",
            "email": "direct@hospital.org",
            "password": "directPassword123",
            "role": "admin",
        }
        res = await client.post("/api/v1/admin/users/", json=payload)
        assert res.status_code == 401

    async def test_jwt_tampering_is_rejected(self, client, patient_token):
        """13. JWT tampering is rejected."""
        # Corrupt the signature of the token
        tampered_token = patient_token[:-5] + "XXXXX"
        headers = {"Authorization": f"Bearer {tampered_token}"}
        res = await client.get("/api/v1/auth/me", headers=headers)
        assert res.status_code == 401

    async def test_admin_can_activate_and_deactivate_user_and_blocks_login(
        self, client, admin_token, db_session
    ):
        """14 & 15. Admin can deactivate user; deactivated user cannot authenticate."""
        # 1. Create a user to test deactivation
        reg_payload = {
            "email": "user_to_suspend@test.com",
            "password": "validPassword123",
            "full_name": "To Be Suspended",
        }
        signup_res = await client.post("/api/v1/auth/signup", json=reg_payload)
        assert signup_res.status_code == 201
        target_user_id = signup_res.json()["user_id"]

        # 2. Login works initially
        login_res = await client.post(
            "/api/v1/auth/login",
            json={"email": "user_to_suspend@test.com", "password": "validPassword123"},
        )
        assert login_res.status_code == 200

        # 3. Admin deactivates account
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        deactivate_res = await client.patch(
            f"/api/v1/admin/users/{target_user_id}/status",
            json={"is_active": False},
            headers=admin_headers,
        )
        assert deactivate_res.status_code == 200
        assert deactivate_res.json()["is_active"] is False

        # 4. Inactive user CANNOT login
        failed_login = await client.post(
            "/api/v1/auth/login",
            json={"email": "user_to_suspend@test.com", "password": "validPassword123"},
        )
        assert failed_login.status_code == 401

        # 5. Admin reactivates account
        reactivate_res = await client.patch(
            f"/api/v1/admin/users/{target_user_id}/status",
            json={"is_active": True},
            headers=admin_headers,
        )
        assert reactivate_res.status_code == 200
        assert reactivate_res.json()["is_active"] is True

        # 6. Login succeeds again
        ok_login = await client.post(
            "/api/v1/auth/login",
            json={"email": "user_to_suspend@test.com", "password": "validPassword123"},
        )
        assert ok_login.status_code == 200

    async def test_administrative_account_provisioning_logged_in_audit_logs(
        self, client, admin_token, db_session
    ):
        """16. Privileged account-management actions are recorded in audit_logs."""
        headers = {"Authorization": f"Bearer {admin_token}"}
        payload = {
            "full_name": "Dr. Audited Clinician",
            "email": "audited.clinician@hospital.org",
            "password": "auditedPassword123",
            "role": "doctor",
            "specialty": "Oncology",
            "license_number": "MED-AUDIT-999000",
        }
        res = await client.post("/api/v1/admin/users/", json=payload, headers=headers)
        assert res.status_code == 201

        # Query audit_logs table for action ADMIN_PROVISION_USER
        audit_res = await db_session.execute(
            select(AuditLog).where(AuditLog.action == "ADMIN_PROVISION_USER")
        )
        audits = audit_res.scalars().all()
        assert len(audits) > 0
        matched = any(
            a.details and a.details.get("provisioned_email") == "audited.clinician@hospital.org"
            for a in audits
        )
        assert matched is True
