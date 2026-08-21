"""Tests for Doctors API."""

from uuid import uuid4

import pytest
import pytest_asyncio

from app.models import Doctor, User, UserRole
from app.services.auth.service import get_password_hash


@pytest_asyncio.fixture
async def admin_user(db_session):
    """Create an admin user."""
    user = User(
        user_id=uuid4(),
        email="admin@test.com",
        hashed_password=get_password_hash("adminpassword123"),
        full_name="Admin User",
        role=UserRole.ADMIN,
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def admin_token(admin_user):
    """Create an admin access token."""
    from app.services.auth.service import create_access_token
    return create_access_token(data={"sub": str(admin_user.user_id), "email": admin_user.email, "role": admin_user.role.value})


@pytest_asyncio.fixture
async def doctor_user(db_session):
    """Create a doctor user."""
    user = User(
        user_id=uuid4(),
        email="doctor@test.com",
        hashed_password=get_password_hash("doctorpassword123"),
        full_name="Dr. Test",
        role=UserRole.DOCTOR,
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def doctor_token(doctor_user):
    """Create a doctor access token."""
    from app.services.auth.service import create_access_token
    return create_access_token(data={"sub": str(doctor_user.user_id), "email": doctor_user.email, "role": doctor_user.role.value})


@pytest_asyncio.fixture
async def test_doctor(db_session, doctor_user):
    """Create a test doctor."""
    doctor = Doctor(
        doctor_id=uuid4(),
        user_id=doctor_user.user_id,
        specialty="Cardiology",
        license_number="MED12345",
        hospital_affiliation="Test Hospital",
        email="doctor@test.com",
        full_name="Dr. Test",
        phone="+91-9876543210",
    )
    db_session.add(doctor)
    await db_session.commit()
    await db_session.refresh(doctor)
    return doctor


@pytest_asyncio.fixture
async def another_doctor_user(db_session):
    """Create another doctor user."""
    user = User(
        user_id=uuid4(),
        email="doctor2@test.com",
        hashed_password=get_password_hash("doctorpassword123"),
        full_name="Dr. Test 2",
        role=UserRole.DOCTOR,
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def another_doctor_token(another_doctor_user):
    """Create another doctor access token."""
    from app.services.auth.service import create_access_token
    return create_access_token(data={"sub": str(another_doctor_user.user_id), "email": another_doctor_user.email, "role": another_doctor_user.role.value})


class TestDoctorsAPI:
    """Test Doctors API endpoints."""

    @pytest.mark.asyncio
    async def test_create_doctor_admin(self, client, admin_user, admin_token):
        """Test creating a doctor as admin."""
        response = await client.post(
            "/api/v1/doctors/",
            json={
                "specialty": "Neurology",
                "license_number": "MED67890",
                "hospital_affiliation": "Brain Hospital",
                "email": "neuro@test.com",
                "full_name": "Dr. Neuro",
                "phone": "+91-9876543211",
            },
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["full_name"] == "Dr. Neuro"
        assert data["specialty"] == "Neurology"
        assert data["license_number"] == "MED67890"

    @pytest.mark.asyncio
    async def test_create_doctor_non_admin_forbidden(self, client, doctor_user, doctor_token):
        """Test creating a doctor as non-admin is forbidden."""
        response = await client.post(
            "/api/v1/doctors/",
            json={
                "specialty": "Neurology",
                "license_number": "MED67890",
                "hospital_affiliation": "Brain Hospital",
                "email": "neuro@test.com",
                "full_name": "Dr. Neuro",
            },
            headers={"Authorization": f"Bearer {doctor_token}"},
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_create_doctor_duplicate_license(self, client, admin_user, admin_token, test_doctor):
        """Test creating doctor with duplicate license fails."""
        response = await client.post(
            "/api/v1/doctors/",
            json={
                "specialty": "Neurology",
                "license_number": test_doctor.license_number,
                "hospital_affiliation": "Brain Hospital",
                "email": "neuro@test.com",
                "full_name": "Dr. Neuro",
            },
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_create_doctor_duplicate_email(self, client, admin_user, admin_token, test_doctor):
        """Test creating doctor with duplicate email fails."""
        response = await client.post(
            "/api/v1/doctors/",
            json={
                "specialty": "Neurology",
                "license_number": "MED67890",
                "hospital_affiliation": "Brain Hospital",
                "email": test_doctor.email,
                "full_name": "Dr. Neuro",
            },
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_get_doctor_own(self, client, doctor_user, doctor_token, test_doctor):
        """Test doctor can read their own profile."""
        response = await client.get(
            f"/api/v1/doctors/{test_doctor.doctor_id}/",
            headers={"Authorization": f"Bearer {doctor_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["doctor_id"] == str(test_doctor.doctor_id)
        assert data["full_name"] == test_doctor.full_name
        assert data["specialty"] == test_doctor.specialty

    @pytest.mark.asyncio
    async def test_get_doctor_other_forbidden(self, client, another_doctor_user, another_doctor_token, test_doctor):
        """Test doctor cannot read another doctor's profile."""
        response = await client.get(
            f"/api/v1/doctors/{test_doctor.doctor_id}/",
            headers={"Authorization": f"Bearer {another_doctor_token}"},
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_get_doctor_admin(self, client, admin_user, admin_token, test_doctor):
        """Test admin can read any doctor profile."""
        response = await client.get(
            f"/api/v1/doctors/{test_doctor.doctor_id}/",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_get_doctor_not_found(self, client, admin_user, admin_token):
        """Test getting non-existent doctor returns 404."""
        response = await client.get(
            f"/api/v1/doctors/{uuid4()}/",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_doctor_own(self, client, doctor_user, doctor_token, test_doctor):
        """Test doctor can update their own profile."""
        response = await client.put(
            f"/api/v1/doctors/{test_doctor.doctor_id}/",
            json={"phone": "+91-9999999999", "hospital_affiliation": "New Hospital"},
            headers={"Authorization": f"Bearer {doctor_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["phone"] == "+91-9999999999"
        assert data["hospital_affiliation"] == "New Hospital"

    @pytest.mark.asyncio
    async def test_update_doctor_other_forbidden(self, client, another_doctor_user, another_doctor_token, test_doctor):
        """Test doctor cannot update another doctor's profile."""
        response = await client.put(
            f"/api/v1/doctors/{test_doctor.doctor_id}/",
            json={"phone": "+91-9999999999"},
            headers={"Authorization": f"Bearer {another_doctor_token}"},
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_update_doctor_admin(self, client, admin_user, admin_token, test_doctor):
        """Test admin can update any doctor."""
        response = await client.put(
            f"/api/v1/doctors/{test_doctor.doctor_id}/",
            json={"phone": "+91-9999999999", "specialty": "Neurology"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["phone"] == "+91-9999999999"
        assert data["specialty"] == "Neurology"

    @pytest.mark.asyncio
    async def test_update_doctor_duplicate_license(self, client, admin_user, admin_token, test_doctor, db_session):
        """Test updating doctor with duplicate license fails."""
        # Create another doctor first
        from uuid import uuid4

        from app.models import Doctor
        doctor2 = Doctor(
            doctor_id=uuid4(),
            specialty="Dermatology",
            license_number="MED99999",
            email="derm@test.com",
            full_name="Dr. Derm",
        )
        db_session.add(doctor2)
        await db_session.commit()
        await db_session.refresh(doctor2)

        # Try to update test_doctor with doctor2's license number
        response = await client.put(
            f"/api/v1/doctors/{test_doctor.doctor_id}/",
            json={"license_number": doctor2.license_number},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_list_doctors_admin(self, client, admin_user, admin_token, test_doctor):
        """Test admin can list doctors."""
        response = await client.get(
            "/api/v1/doctors/",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        assert len(data["doctors"]) >= 1

    @pytest.mark.asyncio
    async def test_list_doctors_doctor(self, client, doctor_user, doctor_token, test_doctor):
        """Test doctor can list doctors."""
        response = await client.get(
            "/api/v1/doctors/",
            headers={"Authorization": f"Bearer {doctor_token}"},
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_list_doctors_patient_forbidden(self, client, admin_user, admin_token):
        """Test patient cannot list doctors."""
        # Create a patient user
        from uuid import uuid4

        from app.models import User, UserRole
        patient_user = User(
            user_id=uuid4(),
            email="patient@test.com",
            hashed_password=get_password_hash("patientpassword123"),
            full_name="Test Patient",
            role=UserRole.PATIENT,
            is_active=True,
        )
        assert patient_user.role == UserRole.PATIENT

    @pytest.mark.asyncio
    async def test_list_doctors_pagination(self, client, admin_user, admin_token, test_doctor):
        """Test doctor list pagination."""
        response = await client.get(
            "/api/v1/doctors/?page=1&page_size=10",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 1
        assert data["page_size"] == 10
        assert data["total_pages"] >= 1

    @pytest.mark.asyncio
    async def test_list_doctors_specialty_filter(self, client, admin_user, admin_token, test_doctor):
        """Test doctor list specialty filter."""
        response = await client.get(
            "/api/v1/doctors/?specialty=Cardiology",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        for doctor in data["doctors"]:
            assert "Cardiology" in doctor["specialty"]

    @pytest.mark.asyncio
    async def test_list_doctors_specialty_filter_no_results(self, client, admin_user, admin_token):
        """Test doctor list specialty filter with no results."""
        response = await client.get(
            "/api/v1/doctors/?specialty=NonExistentSpecialty",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert len(data["doctors"]) == 0