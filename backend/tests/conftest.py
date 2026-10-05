from datetime import date, datetime, timedelta
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from app.database import override_db_engine
from app.main import app
from app.models import Appointment, AppointmentStatus, Base, Doctor, Patient, User, UserRole
from app.services.auth.service import create_access_token, get_password_hash


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    import asyncio
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def db_session():
    """Create a test database session using SQLite file-based for complete isolation."""
    # Use SQLite file-based for tests - complete isolation from Nhost PostgreSQL
    # File-based SQLite allows multiple connections to share the same database
    import os
    import tempfile
    
    # Create a temporary file for the database
    temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
    temp_db.close()
    temp_db_path = temp_db.name
    test_db_url = f"sqlite+aiosqlite:///{temp_db_path}"
    
    engine = create_async_engine(
        test_db_url,
        connect_args={"check_same_thread": False},
        poolclass=NullPool,
    )
    
    # Override the app's database engine for this test
    override_db_engine(engine)
    
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    AsyncSessionLocal = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with AsyncSessionLocal() as session:
        yield session
    
    # Drop tables after test
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()
    
    # Clean up temp file
    if os.path.exists(temp_db_path):
        os.unlink(temp_db_path)


@pytest_asyncio.fixture
async def client(db_session):
    """Create an async test client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def async_client(client: AsyncClient):
    """Alias for client fixture to support test suites requesting async_client."""
    yield client


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
    return create_access_token(data={"sub": str(doctor_user.user_id), "email": doctor_user.email, "role": doctor_user.role.value})


@pytest_asyncio.fixture
async def patient_user(db_session):
    """Create a patient user."""
    user = User(
        user_id=uuid4(),
        email="patient@test.com",
        hashed_password=get_password_hash("patientpassword123"),
        full_name="Test Patient",
        role=UserRole.PATIENT,
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def patient_token(patient_user):
    """Create a patient access token."""
    return create_access_token(data={"sub": str(patient_user.user_id), "email": patient_user.email, "role": patient_user.role.value})


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
    return create_access_token(data={"sub": str(another_doctor_user.user_id), "email": another_doctor_user.email, "role": another_doctor_user.role.value})


@pytest_asyncio.fixture
async def another_doctor(db_session, another_doctor_user):
    """Create another test doctor."""
    doctor = Doctor(
        doctor_id=uuid4(),
        user_id=another_doctor_user.user_id,
        specialty="Neurology",
        license_number="MED67890",
        hospital_affiliation="Brain Hospital",
        email="doctor2@test.com",
        full_name="Dr. Test 2",
        phone="+91-9876543211",
    )
    db_session.add(doctor)
    await db_session.commit()
    await db_session.refresh(doctor)
    return doctor


@pytest_asyncio.fixture
async def test_patient(db_session, patient_user):
    """Create a test patient."""
    patient = Patient(
        patient_id=uuid4(),
        user_id=patient_user.user_id,
        abha_address="patient@abdm",
        full_name="Test Patient",
        date_of_birth=date(1990, 1, 1),
        gender="female",
        phone="+91-9876543210",
        email="patient@test.com",
    )
    db_session.add(patient)
    await db_session.commit()
    await db_session.refresh(patient)
    return patient


@pytest_asyncio.fixture
async def another_patient_user(db_session):
    """Create another patient user."""
    user = User(
        user_id=uuid4(),
        email="patient2@test.com",
        hashed_password=get_password_hash("patientpassword123"),
        full_name="Test Patient 2",
        role=UserRole.PATIENT,
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def another_patient_token(another_patient_user):
    """Create another patient access token."""
    return create_access_token(data={"sub": str(another_patient_user.user_id), "email": another_patient_user.email, "role": another_patient_user.role.value})


@pytest_asyncio.fixture
async def another_patient(db_session, another_patient_user):
    """Create another test patient."""
    patient = Patient(
        patient_id=uuid4(),
        user_id=another_patient_user.user_id,
        abha_address="patient2@abdm",
        full_name="Test Patient 2",
        date_of_birth=date(1990, 1, 1),
        gender="male",
        phone="+91-9876543211",
        email="patient2@test.com",
    )
    db_session.add(patient)
    await db_session.commit()
    await db_session.refresh(patient)
    return patient


@pytest_asyncio.fixture
async def test_appointment(db_session, test_patient, test_doctor):
    """Create a test appointment."""
    appointment = Appointment(
        appointment_id=uuid4(),
        patient_id=test_patient.patient_id,
        doctor_id=test_doctor.doctor_id,
        scheduled_at=datetime.utcnow() + timedelta(days=1),
        duration_minutes=30,
        status=AppointmentStatus.SCHEDULED,
        notes="Test appointment notes",
    )
    db_session.add(appointment)
    await db_session.commit()
    await db_session.refresh(appointment)
    return appointment