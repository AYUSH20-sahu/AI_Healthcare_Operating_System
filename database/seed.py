#!/usr/bin/env python3
"""
Seed script for AI-HOS development database.

Populates the dev database with realistic-but-fake data:
- Doctors across specialties
- Sample patients
- Appointments
- Medical record + prescription in draft status

Run via: python -m database.seed
Or: make seed (if Makefile exists)
"""

import asyncio
import json
import uuid
from datetime import date, datetime, timedelta

from passlib.context import CryptContext
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

# Import models (with fallback)
import sys
from pathlib import Path
backend_dir = Path(__file__).parent.parent / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

try:
    from app.models import Base
except ImportError:
    Base = None

import bcrypt

def hash_password(password: str) -> str:
    """Hash password using native bcrypt matching auth service."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")



# Database URL - use environment variable or default to Nhost
import os
from pathlib import Path

# Load .env first, then .env.local (if it exists, overriding .env)
env_file = Path(__file__).parent.parent / ".env"
env_local = Path(__file__).parent.parent / ".env.local"
try:
    from dotenv import load_dotenv
    if env_file.exists():
        load_dotenv(env_file, override=True)
    if env_local.exists():
        load_dotenv(env_local, override=True)
except ImportError:
    pass


DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/ai_hos"
)

# Detect available async PostgreSQL driver (asyncpg or psycopg)
try:
    import asyncpg
    DRIVER_PREFIX = "postgresql+asyncpg://"
except ImportError:
    try:
        import psycopg
        DRIVER_PREFIX = "postgresql+psycopg://"
    except ImportError:
        DRIVER_PREFIX = "postgresql+asyncpg://"

import urllib.parse


def _sanitize_db_url(url: str) -> str:
    if not url:
        return url
    url = str(url).strip()
    if "://" in url:
        scheme, rest = url.split("://", 1)
        if rest.count("@") > 1:
            userinfo, host_part = rest.rsplit("@", 1)
            if ":" in userinfo:
                username, password = userinfo.split(":", 1)
                encoded_password = urllib.parse.quote(urllib.parse.unquote(password), safe="")
                rest = f"{username}:{encoded_password}@{host_part}"
                url = f"{scheme}://{rest}"
    return url


DATABASE_URL = _sanitize_db_url(DATABASE_URL)

# Ensure async driver prefix
if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", DRIVER_PREFIX, 1)
elif DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", DRIVER_PREFIX, 1)


async def seed_database():
    """Seed the database with development data."""
    connect_args = {'command_timeout': 10}
    if "localhost" not in DATABASE_URL and "127.0.0.1" not in DATABASE_URL:
        connect_args['ssl'] = True

    engine = create_async_engine(
        DATABASE_URL,
        connect_args=connect_args,
        echo=True
    )
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        try:
            # Check if tables exist (they will after M7 migration)
            result = await session.execute(text("""
                SELECT table_name FROM information_schema.tables 
                WHERE table_schema = 'public'
            """))
            tables = [row[0] for row in result.fetchall()]
            
            if not tables or "users" not in tables:
                print("Core schema tables not yet created in public schema.")
                if Base is not None:
                    print("⚙️ Auto-creating all database tables from SQLAlchemy models...")
                    async with engine.begin() as conn:
                        await conn.run_sync(Base.metadata.create_all)
                    print("✅ Tables created successfully!")
                else:
                    print("⚠️ Models could not be imported. Run Alembic migrations first (M7).")
                    return


            # Re-fetch tables to confirm
            result = await session.execute(text("""
                SELECT table_name FROM information_schema.tables 
                WHERE table_schema = 'public'
            """))
            tables = [row[0] for row in result.fetchall()]
            print(f"Found {len(tables)} tables: {tables}")

            # Seed users
            users = await seed_users(session)
            print(f"Seeded {len(users)} users")

            # Fetch actual user_ids from DB (so FKs are 100% consistent across reruns)
            user_rows = (await session.execute(text("SELECT email, user_id FROM users"))).fetchall()
            user_map = {row[0]: row[1] for row in user_rows}

            # Seed doctors
            doctors = await seed_doctors(session, user_map)
            print(f"Seeded {len(doctors)} doctors")

            # Seed patients
            patients = await seed_patients(session, user_map)
            print(f"Seeded {len(patients)} patients")


            # Seed appointments
            appointments = await seed_appointments(session, doctors, patients)
            print(f"Seeded {len(appointments)} appointments")

            # Seed medical records
            medical_records = await seed_medical_records(session, doctors, patients, appointments)
            print(f"Seeded {len(medical_records)} medical records")

            # Seed prescriptions
            prescriptions = await seed_prescriptions(session, doctors, patients, medical_records)
            print(f"Seeded {len(prescriptions)} prescriptions")

            # Seed consents
            consents = await seed_consents(session, patients, doctors)
            print(f"Seeded {len(consents)} consents")

            await session.commit()
            print("\n✅ Database seeded successfully!")

        except Exception as e:
            await session.rollback()
            err_msg = str(e)
            print(f"\n❌ Error seeding database: {e}")
            if "11001" in err_msg or "getaddrinfo" in err_msg:
                print("\n💡 DIAGNOSTIC: DNS host resolution failed ([Errno 11001]).")
                print("   • If using Nhost: Cloud projects pause after a period of inactivity.")
                print("     Log into https://app.nhost.io, open your project, and click 'Resume Project' / 'Wake Up'.")
                print("   • Also ensure your internet connection is active.")
            elif "SASL" in err_msg or "authentication failed" in err_msg.lower():
                print("\n💡 DIAGNOSTIC: SASL authentication failed.")
                print("   • The database was reached, but the password was rejected.")
                print("   • Check your database password in Nhost Dashboard -> Settings -> Database.")
            raise
        finally:
            await engine.dispose()


async def seed_users(session: AsyncSession):
    """Seed test persona users for authentication."""
    users_data = [
        {
            "user_id": uuid.uuid4(),
            "email": "doctor@test.com",
            "hashed_password": hash_password("doctorpassword123"),
            "full_name": "Dr. Rajesh Sharma",
            "role": "doctor",
            "is_active": True,
        },
        {
            "user_id": uuid.uuid4(),
            "email": "patient@test.com",
            "hashed_password": hash_password("patientpassword123"),
            "full_name": "Amit Kumar",
            "role": "patient",
            "is_active": True,
        },
        {
            "user_id": uuid.uuid4(),
            "email": "admin@test.com",
            "hashed_password": hash_password("adminpassword123"),
            "full_name": "Institutional Admin",
            "role": "admin",
            "is_active": True,
        },
    ]


    for user in users_data:
        await session.execute(text("""
            INSERT INTO users (user_id, email, hashed_password, full_name, role, is_active, created_at, updated_at)
            VALUES (:user_id, :email, :hashed_password, :full_name, :role, :is_active, NOW(), NOW())
            ON CONFLICT (email) DO NOTHING
        """), user)

    return users_data


async def seed_doctors(session: AsyncSession, user_map: dict | None = None):
    """Seed doctors across specialties."""
    if user_map is None:
        user_map = {}
    doctor_user_id = user_map.get("doctor@test.com")

    doctors_data = [
        {
            "doctor_id": uuid.uuid4(),
            "user_id": doctor_user_id,
            "specialty": "Cardiology",
            "license_number": "MD-CARD-001",
            "hospital_affiliation": "City General Hospital",
            "email": "doctor@test.com",
            "full_name": "Dr. Rajesh Sharma",
            "phone": "+91-98765-43210",
        },
        {
            "doctor_id": uuid.uuid4(),
            "user_id": None,
            "specialty": "Neurology",
            "license_number": "MD-NEURO-002",
            "hospital_affiliation": "City General Hospital",
            "email": "dr.patel@citygeneral.com",
            "full_name": "Dr. Priya Patel",
            "phone": "+91-98765-43211",
        },
        {
            "doctor_id": uuid.uuid4(),
            "user_id": None,
            "specialty": "Pediatrics",
            "license_number": "MD-PED-003",
            "hospital_affiliation": "Children's Medical Center",
            "email": "dr.kumar@childrensmc.com",
            "full_name": "Dr. Arjun Kumar",
            "phone": "+91-98765-43212",
        },
        {
            "doctor_id": uuid.uuid4(),
            "user_id": None,
            "specialty": "Orthopedics",
            "license_number": "MD-ORTHO-004",
            "hospital_affiliation": "City General Hospital",
            "email": "dr.singh@citygeneral.com",
            "full_name": "Dr. Kavya Singh",
            "phone": "+91-98765-43213",
        },
        {
            "doctor_id": uuid.uuid4(),
            "user_id": None,
            "specialty": "Dermatology",
            "license_number": "MD-DERM-005",
            "hospital_affiliation": "Skin & Hair Clinic",
            "email": "dr.reddy@skinhair.com",
            "full_name": "Dr. Vikram Reddy",
            "phone": "+91-98765-43214",
        },
    ]

    for doc in doctors_data:
        await session.execute(text("""
            INSERT INTO doctors (doctor_id, user_id, specialty, license_number, 
                               hospital_affiliation, email, full_name, phone, created_at, updated_at)
            VALUES (:doctor_id, :user_id, :specialty, :license_number,
                    :hospital_affiliation, :email, :full_name, :phone, NOW(), NOW())
            ON CONFLICT (license_number) DO NOTHING
        """), doc)

    return doctors_data



async def seed_patients(session: AsyncSession, user_map: dict | None = None):
    """Seed sample patients."""
    if user_map is None:
        user_map = {}
    patient_user_id = user_map.get("patient@test.com")

    patients_data = [
        {
            "patient_id": uuid.uuid4(),
            "user_id": patient_user_id,
            "abha_address": "patient1@abdm",
            "full_name": "Amit Kumar",
            "date_of_birth": date(1985, 3, 15),
            "gender": "male",
            "phone": "+91-98765-11111",
            "email": "patient@test.com",
            "address": "123 MG Road, Bangalore, Karnataka 560001",
            "emergency_contact_name": "Sunita Kumar",
            "emergency_contact_phone": "+91-98765-11112",
        },
        {
            "patient_id": uuid.uuid4(),
            "user_id": None,
            "abha_address": "patient2@abdm",
            "full_name": "Priya Sharma",
            "date_of_birth": date(1990, 7, 22),
            "gender": "female",
            "phone": "+91-98765-22222",
            "email": "priya.sharma@email.com",
            "address": "456 Park Street, Mumbai, Maharashtra 400001",
            "emergency_contact_name": "Rajesh Sharma",
            "emergency_contact_phone": "+91-98765-22223",
        },
        {
            "patient_id": uuid.uuid4(),
            "user_id": None,
            "abha_address": "patient3@abdm",
            "full_name": "Rahul Singh",
            "date_of_birth": date(1978, 11, 5),
            "gender": "male",
            "phone": "+91-98765-33333",
            "email": "rahul.singh@email.com",
            "address": "789 Sector 17, Chandigarh 160017",
            "emergency_contact_name": "Meena Singh",
            "emergency_contact_phone": "+91-98765-33334",
        },
        {
            "patient_id": uuid.uuid4(),
            "user_id": None,
            "abha_address": "patient4@abdm",
            "full_name": "Anjali Gupta",
            "date_of_birth": date(1995, 1, 30),
            "gender": "female",
            "phone": "+91-98765-44444",
            "email": "anjali.gupta@email.com",
            "address": "321 Banjara Hills, Hyderabad, Telangana 500034",
            "emergency_contact_name": "Vikram Gupta",
            "emergency_contact_phone": "+91-98765-44445",
        },
        {
            "patient_id": uuid.uuid4(),
            "user_id": None,
            "abha_address": "patient5@abdm",
            "full_name": "Suresh Nair",
            "date_of_birth": date(1965, 9, 12),
            "gender": "male",
            "phone": "+91-98765-55555",
            "email": "suresh.nair@email.com",
            "address": "555 Marine Drive, Kochi, Kerala 682001",
            "emergency_contact_name": "Lakshmi Nair",
            "emergency_contact_phone": "+91-98765-55556",
        },
    ]

    for pat in patients_data:
        await session.execute(text("""
            INSERT INTO patients (patient_id, user_id, abha_address, full_name, date_of_birth,
                                gender, phone, email, address, emergency_contact_name,
                                emergency_contact_phone, created_at, updated_at)
            VALUES (:patient_id, :user_id, :abha_address, :full_name, :date_of_birth,
                    :gender, :phone, :email, :address, :emergency_contact_name,
                    :emergency_contact_phone, NOW(), NOW())
            ON CONFLICT (abha_address) DO NOTHING
        """), pat)

    return patients_data


async def seed_appointments(session: AsyncSession, doctors, patients):
    """Seed appointments."""
    appointments_data = []
    base_date = datetime.now().replace(hour=10, minute=0, second=0, microsecond=0)

    # Create a few appointments
    appointment_configs = [
        (0, 0, base_date + timedelta(days=1), 30, "SCHEDULED"),  # Amit with Dr. Sharma
        (1, 1, base_date + timedelta(days=2), 30, "SCHEDULED"),  # Priya with Dr. Patel
        (2, 2, base_date + timedelta(days=3), 20, "SCHEDULED"),  # Rahul with Dr. Kumar
        (3, 3, base_date + timedelta(days=1, hours=2), 30, "SCHEDULED"),  # Anjali with Dr. Singh
        (4, 4, base_date + timedelta(days=2, hours=1), 20, "SCHEDULED"),  # Suresh with Dr. Reddy
        (0, 1, base_date + timedelta(days=5), 30, "COMPLETED"),  # Amit with Dr. Patel (past)
    ]


    for i, (pat_idx, doc_idx, scheduled_at, duration, status) in enumerate(appointment_configs):
        appt_id = uuid.uuid4()
        appointments_data.append({
            "appointment_id": appt_id,
            "patient_id": patients[pat_idx]["patient_id"],
            "doctor_id": doctors[doc_idx]["doctor_id"],
            "scheduled_at": scheduled_at,
            "duration_minutes": duration,
            "status": status,
            "notes": f"Appointment {i+1}",
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        })

    for appt in appointments_data:
        await session.execute(text("""
            INSERT INTO appointments (appointment_id, patient_id, doctor_id, scheduled_at,
                                    duration_minutes, status, notes, created_at, updated_at)
            VALUES (:appointment_id, :patient_id, :doctor_id, :scheduled_at,
                    :duration_minutes, :status, :notes, :created_at, :updated_at)
            ON CONFLICT (appointment_id) DO NOTHING
        """), appt)

    return appointments_data



async def seed_medical_records(session: AsyncSession, doctors, patients, appointments):
    """Seed medical records."""
    records_data = []

    # One completed appointment gets a medical record
    completed_appt = next((a for a in appointments if a["status"] == "COMPLETED"), None)
    if completed_appt:
        record_id = uuid.uuid4()
        records_data.append({
            "record_id": record_id,
            "patient_id": completed_appt["patient_id"],
            "doctor_id": completed_appt["doctor_id"],
            "appointment_id": completed_appt["appointment_id"],
            "content": {
                "chief_complaint": "Persistent headache for 2 weeks",
                "history_of_present_illness": "Patient reports throbbing headache, worse in mornings, associated with nausea. No visual changes. Pain scale 7/10.",
                "past_medical_history": "Hypertension (controlled), no prior neurological issues",
                "medications": ["Amlodipine 5mg daily"],
                "allergies": ["Penicillin"],
                "physical_exam": "BP 130/85, HR 72, Neuro exam non-focal, no papilledema",
                "assessment": "Tension-type headache, likely stress-related. Rule out secondary causes.",
                "plan": "1. Lifestyle modifications - stress management, regular sleep\n2. Ibuprofen 400mg PRN for breakthrough pain\n3. Follow-up in 2 weeks\n4. If worsening, consider neuroimaging",
            },
            "status": "FINALIZED",
            "created_at": completed_appt["scheduled_at"],
            "updated_at": completed_appt["scheduled_at"] + timedelta(hours=1),
            "finalized_at": completed_appt["scheduled_at"] + timedelta(hours=1),
        })

    # One upcoming appointment gets a draft medical record
    upcoming_appt = next((a for a in appointments if a["status"] == "SCHEDULED"), None)
    if upcoming_appt:
        record_id = uuid.uuid4()
        records_data.append({
            "record_id": record_id,
            "patient_id": upcoming_appt["patient_id"],
            "doctor_id": upcoming_appt["doctor_id"],
            "appointment_id": upcoming_appt["appointment_id"],
            "content": {
                "chief_complaint": "Follow-up for hypertension",
                "history_of_present_illness": "Patient here for routine BP check. Reports good compliance with medication. Occasional dizziness on standing.",
                "past_medical_history": "Hypertension x 3 years, Type 2 diabetes x 1 year",
                "medications": ["Amlodipine 5mg daily", "Metformin 500mg BID"],
                "allergies": ["None known"],
                "physical_exam": "BP 138/88 (sitting), 128/82 (standing), HR 76, BMI 27.2",
                "assessment": "Hypertension - borderline controlled. Orthostatic hypotension noted.",
                "plan": "1. Continue current medications\n2. Monitor home BP readings\n3. Consider dose adjustment if BP > 140/90 consistently\n4. Follow-up in 3 months",
            },
            "status": "DRAFT",
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
            "finalized_at": None,
        })

    for rec in records_data:
        # Serialize JSON fields
        rec_copy = rec.copy()
        rec_copy['content'] = json.dumps(rec_copy['content'])
        await session.execute(text("""
            INSERT INTO medical_records (record_id, patient_id, doctor_id, appointment_id,
                                       content, status, created_at, updated_at, finalized_at)
            VALUES (:record_id, :patient_id, :doctor_id, :appointment_id,
                    :content, :status, :created_at, :updated_at, :finalized_at)
            ON CONFLICT (record_id) DO NOTHING
        """), rec_copy)

    return records_data


async def seed_prescriptions(session: AsyncSession, doctors, patients, medical_records):
    """Seed prescriptions."""
    prescriptions_data = []

    # Prescription for the finalized medical record
    finalized_record = next((r for r in medical_records if r["status"] == "FINALIZED"), None)
    if finalized_record:
        presc_id = uuid.uuid4()
        prescriptions_data.append({
            "prescription_id": presc_id,
            "medical_record_id": finalized_record["record_id"],
            "patient_id": finalized_record["patient_id"],
            "doctor_id": finalized_record["doctor_id"],
            "medications": [
                {
                    "name": "Ibuprofen",
                    "dosage": "400mg",
                    "frequency": "Every 6-8 hours as needed",
                    "duration": "5 days",
                    "instructions": "Take with food. Do not exceed 1200mg/day.",
                }
            ],
            "status": "FINALIZED",
            "created_at": finalized_record["finalized_at"],
            "updated_at": finalized_record["finalized_at"],
            "finalized_at": finalized_record["finalized_at"],
        })

    # Draft prescription for the draft medical record
    draft_record = next((r for r in medical_records if r["status"] == "DRAFT"), None)
    if draft_record:
        presc_id = uuid.uuid4()
        prescriptions_data.append({
            "prescription_id": presc_id,
            "medical_record_id": draft_record["record_id"],
            "patient_id": draft_record["patient_id"],
            "doctor_id": draft_record["doctor_id"],
            "medications": [
                {
                    "name": "Amlodipine",
                    "dosage": "5mg",
                    "frequency": "Once daily",
                    "duration": "90 days",
                    "instructions": "Take in the morning. Monitor for ankle swelling.",
                },
                {
                    "name": "Metformin",
                    "dosage": "500mg",
                    "frequency": "Twice daily with meals",
                    "duration": "90 days",
                    "instructions": "Take with breakfast and dinner.",
                }
            ],
            "status": "DRAFT",
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
            "finalized_at": None,
        })

    for presc in prescriptions_data:
        # Serialize JSON fields
        presc_copy = presc.copy()
        presc_copy['medications'] = json.dumps(presc_copy['medications'])
        await session.execute(text("""
            INSERT INTO prescriptions (prescription_id, medical_record_id, patient_id, doctor_id,
                                     medications, status, created_at, updated_at, finalized_at)
            VALUES (:prescription_id, :medical_record_id, :patient_id, :doctor_id,
                    :medications, :status, :created_at, :updated_at, :finalized_at)
            ON CONFLICT (prescription_id) DO NOTHING
        """), presc_copy)

    return prescriptions_data


async def seed_consents(session: AsyncSession, patients, doctors):
    """Seed consents."""
    consents_data = []

    # Each patient consents to their primary doctor
    for i, patient in enumerate(patients[:3]):  # First 3 patients
        consent_id = uuid.uuid4()
        consents_data.append({
            "consent_id": consent_id,
            "patient_id": patient["patient_id"],
            "provider_id": doctors[i]["doctor_id"],
            "record_scope": "FULL_ACCESS",
            "granted_at": datetime.now() - timedelta(days=30),
            "revoked_at": None,
        })


    for consent in consents_data:
        await session.execute(text("""
            INSERT INTO consents (consent_id, patient_id, provider_id, record_scope,
                                granted_at, revoked_at, created_at, updated_at)
            VALUES (:consent_id, :patient_id, :provider_id, :record_scope,
                    :granted_at, :revoked_at, NOW(), NOW())
            ON CONFLICT (consent_id) DO NOTHING
        """), consent)

    return consents_data


if __name__ == "__main__":
    asyncio.run(seed_database())