#!/usr/bin/env python3
"""
Comprehensive Seed Script for AI-HOS (AI Healthcare Operating System).

Populates the database with realistic clinical dummy data across all system layers:
1. Multi-Tenant Organization (Apex Multi-Specialty Hospital)
2. Core Personas (Super Admin, Hospital Admin, Doctor, Nurse, Patient)
3. 10 Departmental Specialists (2 for each of 5 key departments: Cardiology, Neurology, Pediatrics, Orthopedics, Dermatology)
4. 20 Specialized Physicians across clinical disciplines
5. 20 Inpatient Ward & Critical Care Nurses
6. Patients with ABDM/ABHA IDs & Emergency Contacts
7. Clinical Appointments (Scheduled, In-Progress, Completed)
8. Medical Records (Finalized SOAP encounters + Drafts pending Doctor Approval Gate)
9. Prescriptions (Finalized Rx + Drafts with Drug Interaction warnings)
10. Patient Consents (Full Access & Active Care)
11. Inpatient Ward Beds, Telemetry Vitals & Nursing Shift Tasks
12. Patient Diagnostic Reports & Daily Medicine Reminders

Usage:
    python database/seed.py
    or:
    python run_seed.py
"""

import asyncio
import json
import os
from pathlib import Path
import sys
import uuid
from datetime import date, datetime, timedelta

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

# Setup import path
backend_dir = Path(__file__).resolve().parent.parent / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

# Load environment configuration (.env or .env.local)
root_dir = Path(__file__).resolve().parent.parent
env_file = root_dir / ".env"
env_local = root_dir / ".env.local"
try:
    from dotenv import load_dotenv
    if env_file.exists():
        load_dotenv(env_file, override=True)
    if env_local.exists():
        load_dotenv(env_local, override=True)
except ImportError:
    pass

import bcrypt

def hash_password(password: str) -> str:
    """Hash password using native bcrypt matching auth service."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/ai_hos"
)

# Convert url to asyncpg format
if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)
elif DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+asyncpg://", 1)


async def seed_database():
    """Seed the database with complete clinical dummy data."""
    print("=" * 75)
    print("AI-HOS: CLINICAL DUMMY DATA SEEDER (30 DOCTORS/PHYSICIANS, 20 NURSES)")
    print("=" * 75)

    connect_args = {"command_timeout": 35}
    if "localhost" not in DATABASE_URL and "127.0.0.1" not in DATABASE_URL:
        connect_args["ssl"] = True

    print(f"Connecting to database...")
    engine = create_async_engine(DATABASE_URL, connect_args=connect_args, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    try:
        from app.models import Base
    except ImportError:
        Base = None

    async with async_session() as session:
        try:
            # 1. Ensure enum values and schema tables exist
            print("\n[Step 1/11] Verifying database schema & enum values...")
            if "sqlite" not in str(engine.url):
                try:
                    async with engine.connect() as conn:
                        await conn.execution_options(isolation_level="AUTOCOMMIT")
                        enum_alterations = [
                            # userrole
                            "ALTER TYPE userrole ADD VALUE IF NOT EXISTS 'super_admin';",
                            "ALTER TYPE userrole ADD VALUE IF NOT EXISTS 'head_physician';",
                            "ALTER TYPE userrole ADD VALUE IF NOT EXISTS 'head_nurse';",
                            # appointmentstatus
                            "ALTER TYPE appointmentstatus ADD VALUE IF NOT EXISTS 'scheduled';",
                            "ALTER TYPE appointmentstatus ADD VALUE IF NOT EXISTS 'in_progress';",
                            "ALTER TYPE appointmentstatus ADD VALUE IF NOT EXISTS 'completed';",
                            "ALTER TYPE appointmentstatus ADD VALUE IF NOT EXISTS 'cancelled';",
                            "ALTER TYPE appointmentstatus ADD VALUE IF NOT EXISTS 'no_show';",
                            "ALTER TYPE appointmentstatus ADD VALUE IF NOT EXISTS 'SCHEDULED';",
                            "ALTER TYPE appointmentstatus ADD VALUE IF NOT EXISTS 'IN_PROGRESS';",
                            "ALTER TYPE appointmentstatus ADD VALUE IF NOT EXISTS 'COMPLETED';",
                            "ALTER TYPE appointmentstatus ADD VALUE IF NOT EXISTS 'CANCELLED';",
                            "ALTER TYPE appointmentstatus ADD VALUE IF NOT EXISTS 'NO_SHOW';",
                            # appointment_status
                            "ALTER TYPE appointment_status ADD VALUE IF NOT EXISTS 'scheduled';",
                            "ALTER TYPE appointment_status ADD VALUE IF NOT EXISTS 'in_progress';",
                            "ALTER TYPE appointment_status ADD VALUE IF NOT EXISTS 'completed';",
                            "ALTER TYPE appointment_status ADD VALUE IF NOT EXISTS 'cancelled';",
                            "ALTER TYPE appointment_status ADD VALUE IF NOT EXISTS 'no_show';",
                            # consentscope
                            "ALTER TYPE consentscope ADD VALUE IF NOT EXISTS 'full_access';",
                            "ALTER TYPE consentscope ADD VALUE IF NOT EXISTS 'records_only';",
                            "ALTER TYPE consentscope ADD VALUE IF NOT EXISTS 'appointments_only';",
                            "ALTER TYPE consentscope ADD VALUE IF NOT EXISTS 'notes_only';",
                            "ALTER TYPE consentscope ADD VALUE IF NOT EXISTS 'limited';",
                            "ALTER TYPE consentscope ADD VALUE IF NOT EXISTS 'emergency_only';",
                            # consent_scope
                            "ALTER TYPE consent_scope ADD VALUE IF NOT EXISTS 'full_access';",
                            "ALTER TYPE consent_scope ADD VALUE IF NOT EXISTS 'records_only';",
                            "ALTER TYPE consent_scope ADD VALUE IF NOT EXISTS 'appointments_only';",
                            "ALTER TYPE consent_scope ADD VALUE IF NOT EXISTS 'notes_only';",
                            "ALTER TYPE consent_scope ADD VALUE IF NOT EXISTS 'limited';",
                            "ALTER TYPE consent_scope ADD VALUE IF NOT EXISTS 'emergency_only';",
                            # medicalrecordstatus / medical_record_status
                            "ALTER TYPE medicalrecordstatus ADD VALUE IF NOT EXISTS 'DRAFT';",
                            "ALTER TYPE medicalrecordstatus ADD VALUE IF NOT EXISTS 'FINALIZED';",
                            "ALTER TYPE medicalrecordstatus ADD VALUE IF NOT EXISTS 'AMENDED';",
                            "ALTER TYPE medicalrecordstatus ADD VALUE IF NOT EXISTS 'draft';",
                            "ALTER TYPE medicalrecordstatus ADD VALUE IF NOT EXISTS 'finalized';",
                            "ALTER TYPE medicalrecordstatus ADD VALUE IF NOT EXISTS 'amended';",
                            "ALTER TYPE medical_record_status ADD VALUE IF NOT EXISTS 'DRAFT';",
                            "ALTER TYPE medical_record_status ADD VALUE IF NOT EXISTS 'FINALIZED';",
                            "ALTER TYPE medical_record_status ADD VALUE IF NOT EXISTS 'AMENDED';",
                            # prescriptionstatus / prescription_status
                            "ALTER TYPE prescriptionstatus ADD VALUE IF NOT EXISTS 'DRAFT';",
                            "ALTER TYPE prescriptionstatus ADD VALUE IF NOT EXISTS 'FINALIZED';",
                            "ALTER TYPE prescriptionstatus ADD VALUE IF NOT EXISTS 'APPROVED';",
                            "ALTER TYPE prescriptionstatus ADD VALUE IF NOT EXISTS 'CANCELLED';",
                            "ALTER TYPE prescriptionstatus ADD VALUE IF NOT EXISTS 'REJECTED';",
                            "ALTER TYPE prescriptionstatus ADD VALUE IF NOT EXISTS 'draft';",
                            "ALTER TYPE prescriptionstatus ADD VALUE IF NOT EXISTS 'finalized';",
                            "ALTER TYPE prescription_status ADD VALUE IF NOT EXISTS 'DRAFT';",
                            "ALTER TYPE prescription_status ADD VALUE IF NOT EXISTS 'FINALIZED';",
                            "ALTER TYPE prescription_status ADD VALUE IF NOT EXISTS 'APPROVED';",
                        ]
                        for ea in enum_alterations:
                            try:
                                await conn.execute(text(ea))
                            except Exception:
                                pass
                except Exception as e:
                    print(f"  - Enum update notice: {e}")

            if Base is not None:
                async with engine.begin() as conn:
                    await conn.run_sync(Base.metadata.create_all)
                    if "sqlite" not in str(engine.url):
                        alter_statements = [
                            "ALTER TABLE appointments ADD COLUMN IF NOT EXISTS reason VARCHAR(500);",
                            "ALTER TABLE appointments ADD COLUMN IF NOT EXISTS meeting_link VARCHAR(500);",
                            "ALTER TABLE appointments ADD COLUMN IF NOT EXISTS telehealth_room_id VARCHAR(100);",
                            "ALTER TABLE appointments ADD COLUMN IF NOT EXISTS telehealth_started_at TIMESTAMP;",
                            "ALTER TABLE appointments ADD COLUMN IF NOT EXISTS telehealth_ended_at TIMESTAMP;",
                            "ALTER TABLE users ADD COLUMN IF NOT EXISTS phone VARCHAR(50);",
                            "ALTER TABLE users ADD COLUMN IF NOT EXISTS organization_id UUID REFERENCES organizations(organization_id) ON DELETE SET NULL;",
                            "ALTER TABLE users ADD COLUMN IF NOT EXISTS department VARCHAR(100);",
                            "ALTER TABLE users ADD COLUMN IF NOT EXISTS designation VARCHAR(100);",
                            "ALTER TABLE users ADD COLUMN IF NOT EXISTS qualifications VARCHAR(255);",
                            "ALTER TABLE users ADD COLUMN IF NOT EXISTS experience_years INTEGER;",
                            "ALTER TABLE users ADD COLUMN IF NOT EXISTS room_number VARCHAR(50);",
                            "ALTER TABLE users ADD COLUMN IF NOT EXISTS shift VARCHAR(100);",
                            "ALTER TABLE users ADD COLUMN IF NOT EXISTS supervisor_id UUID REFERENCES users(user_id) ON DELETE SET NULL;",
                            "ALTER TABLE doctors ADD COLUMN IF NOT EXISTS department VARCHAR(100);",
                            "ALTER TABLE doctors ADD COLUMN IF NOT EXISTS designation VARCHAR(100);",
                            "ALTER TABLE doctors ADD COLUMN IF NOT EXISTS qualifications VARCHAR(255);",
                            "ALTER TABLE doctors ADD COLUMN IF NOT EXISTS experience_years INTEGER;",
                            "ALTER TABLE doctors ADD COLUMN IF NOT EXISTS room_number VARCHAR(50);",
                            "ALTER TABLE doctors ADD COLUMN IF NOT EXISTS shift VARCHAR(100);",
                            "ALTER TABLE doctors ADD COLUMN IF NOT EXISTS is_head_physician BOOLEAN DEFAULT FALSE;",
                            "ALTER TABLE doctors ADD COLUMN IF NOT EXISTS supervisor_id UUID REFERENCES users(user_id) ON DELETE SET NULL;",
                            "ALTER TABLE patients ADD COLUMN IF NOT EXISTS phone VARCHAR(50);",
                            "ALTER TABLE organizations ADD COLUMN IF NOT EXISTS facility_type VARCHAR(100);",
                            "ALTER TABLE organizations ADD COLUMN IF NOT EXISTS departments JSONB;",
                            "ALTER TABLE organizations ADD COLUMN IF NOT EXISTS total_beds INTEGER DEFAULT 0;",
                            "ALTER TABLE organizations ADD COLUMN IF NOT EXISTS icu_beds INTEGER DEFAULT 0;",
                            "ALTER TABLE organizations ADD COLUMN IF NOT EXISTS has_emergency BOOLEAN DEFAULT TRUE;",
                            "ALTER TABLE organizations ADD COLUMN IF NOT EXISTS has_ambulance BOOLEAN DEFAULT TRUE;",
                            "ALTER TABLE organizations ADD COLUMN IF NOT EXISTS license_number VARCHAR(100);",
                            "ALTER TABLE organizations ADD COLUMN IF NOT EXISTS abdm_facility_id VARCHAR(100);",
                            "ALTER TABLE organizations ADD COLUMN IF NOT EXISTS insurance_network_code VARCHAR(100);",
                            "ALTER TABLE organizations ADD COLUMN IF NOT EXISTS emergency_hotline VARCHAR(50);",
                            "ALTER TABLE organizations ADD COLUMN IF NOT EXISTS operating_hours VARCHAR(255);",
                            "ALTER TABLE organizations ADD COLUMN IF NOT EXISTS clinical_review_policy TEXT;",
                            "ALTER TABLE medical_records ADD COLUMN IF NOT EXISTS finalized_at TIMESTAMP;",
                            "ALTER TABLE prescriptions ADD COLUMN IF NOT EXISTS finalized_at TIMESTAMP;",
                            "ALTER TABLE prescriptions ADD COLUMN IF NOT EXISTS notes TEXT;",
                        ]
                        for stmt in alter_statements:
                            try:
                                await conn.execute(text(stmt))
                            except Exception as e:
                                pass
            print("  ✓ Schema tables verified.")

            # 2. Seed Organization
            print("\n[Step 2/11] Seeding Flagship Healthcare Organization...")
            org = await seed_organization(session)
            org_id = org["organization_id"]
            print(f"  ✓ Seeded Organization: {org['name']} ({org['code']})")

            # 3. Seed Core Users & Personas
            print("\n[Step 3/11] Seeding Core Users & Institutional Personas...")
            users = await seed_users(session, org_id)
            print(f"  ✓ Seeded {len(users)} Core Institutional Users")

            # 4. Seed 10 Departmental Doctors (2 per department across 5 departments)
            print("\n[Step 4/11] Seeding 10 Departmental Specialists (2 per department)...")
            dept_docs = await seed_department_doctors(session, org_id)
            print(f"  ✓ Seeded {len(dept_docs)} Departmental Specialist Doctors & Logins")

            # 5. Seed 20 Physicians across Clinical Disciplines
            print("\n[Step 5/11] Seeding 20 Specialized Physicians...")
            physicians = await seed_physicians(session, org_id)
            print(f"  ✓ Seeded {len(physicians)} Specialized Physicians & Clinician Profiles")

            # Combine all doctors for appointment/medical records linking
            all_doctors = dept_docs + physicians

            # 6. Seed 20 Nurses across Wards & ICU
            print("\n[Step 6/11] Seeding 20 Inpatient Ward & Critical Care Nurses...")
            nurses = await seed_nurses(session, org_id)
            print(f"  ✓ Seeded {len(nurses)} Staff & Head Nurses with Active Logins")

            # Fetch active user map
            user_rows = (await session.execute(text("SELECT email, user_id FROM users"))).fetchall()
            user_map = {row[0]: row[1] for row in user_rows}

            # 7. Seed Patients
            print("\n[Step 7/11] Seeding Patients with ABHA IDs...")
            patients = await seed_patients(session, user_map)
            print(f"  ✓ Seeded {len(patients)} Patients")

            # 8. Seed Appointments
            print("\n[Step 8/11] Seeding Consultations & Telehealth Appointments...")
            appointments = await seed_appointments(session, all_doctors, patients)
            print(f"  ✓ Seeded {len(appointments)} Appointments")

            # 9. Seed Medical Records (Drafts & Finalized)
            print("\n[Step 9/11] Seeding Medical Records & SOAP Encounters...")
            records = await seed_medical_records(session, all_doctors, patients, appointments)
            print(f"  ✓ Seeded {len(records)} Medical Records (including Approval Queue Drafts)")

            # 10. Seed Prescriptions (Drafts & Finalized)
            print("\n[Step 10/11] Seeding Prescriptions with Interaction Checks...")
            prescriptions = await seed_prescriptions(session, all_doctors, patients, records)
            print(f"  ✓ Seeded {len(prescriptions)} Prescriptions")

            # 11. Seed Consents, Inpatient Beds, Vitals & Reminders
            print("\n[Step 11/11] Seeding Consents, Inpatient Beds, Vitals & Medicine Reminders...")
            consents = await seed_consents(session, patients, all_doctors)
            beds_count = await seed_inpatient_workstation(session, org_id, patients)
            reminders_count = await seed_patient_extras(session, patients)
            print(f"  ✓ Seeded {len(consents)} Consents")
            print(f"  ✓ Seeded {beds_count} Inpatient Ward Beds & Bedside Vitals")
            print(f"  ✓ Seeded {reminders_count} Patient Medicine Reminders & Diagnostic Reports")

            await session.commit()
            print("\n" + "=" * 75)
            print("✅ SUCCESS: ALL 30 DOCTORS, 20 PHYSICIANS & 20 NURSES SEEDED SUCCESSFULLY!")
            print("=" * 75)

        except Exception as e:
            await session.rollback()
            print(f"\n❌ Error seeding database: {e}")
            raise
        finally:
            await engine.dispose()


async def seed_organization(session: AsyncSession) -> dict:
    """Seed the flagship healthcare organization."""
    org_id = uuid.UUID("11111111-1111-1111-1111-111111111111")
    org_data = {
        "organization_id": org_id,
        "name": "Apex Multi-Specialty Hospital & Research Center",
        "code": "APEX-HOSP-01",
        "description": "Premier tertiary care clinical center with 24/7 trauma care and digital ICU integration.",
        "address": "Plot 42, Health City Avenue, New Delhi, 110029, India",
        "contact_email": "apex.admin@aihos.org",
        "contact_phone": "+91-11-2659-0000",
        "facility_type": "Multi-Specialty Hospital",
        "departments": json.dumps([
            "Cardiology", "Neurology", "Pediatrics", "Orthopedics", "Dermatology",
            "Internal Medicine", "Emergency & Trauma", "Inpatient Care", "Critical Care",
            "Pulmonology", "Gastroenterology", "Nephrology", "Oncology", "Endocrinology"
        ]),
        "total_beds": 150,
        "icu_beds": 30,
        "has_emergency": True,
        "has_ambulance": True,
        "license_number": "NABH-DL-2026-089",
        "abdm_facility_id": "IN-DL-AIHOS-001",
        "insurance_network_code": "INS-APEX-NET-88",
        "emergency_hotline": "+91-11-2659-108",
        "operating_hours": "24/7 Emergency & Inpatient Care",
        "clinical_review_policy": "Strict Clinician Sign-Off Required",
        "is_active": True,
    }

    await session.execute(text("""
        INSERT INTO organizations (
            organization_id, name, code, description, address, contact_email, contact_phone,
            facility_type, departments, total_beds, icu_beds, has_emergency, has_ambulance,
            license_number, abdm_facility_id, insurance_network_code, emergency_hotline,
            operating_hours, clinical_review_policy, is_active, created_at, updated_at
        ) VALUES (
            :organization_id, :name, :code, :description, :address, :contact_email, :contact_phone,
            :facility_type, CAST(:departments AS json), :total_beds, :icu_beds, :has_emergency, :has_ambulance,
            :license_number, :abdm_facility_id, :insurance_network_code, :emergency_hotline,
            :operating_hours, :clinical_review_policy, :is_active, NOW(), NOW()
        )
        ON CONFLICT (name) DO UPDATE SET
            code = EXCLUDED.code,
            is_active = EXCLUDED.is_active,
            updated_at = NOW()
    """), org_data)

    return org_data


async def seed_users(session: AsyncSession, org_id: uuid.UUID) -> list:
    """Seed core login personas."""
    users_data = [
        {
            "user_id": uuid.UUID("22222222-2222-2222-2222-222222222222"),
            "email": "superadmin@aihos.org",
            "phone": "+919999000001",
            "hashed_password": hash_password("adminpassword123"),
            "full_name": "AI-HOS Global Super Administrator",
            "role": "super_admin",
            "organization_id": None,
            "department": "Global Governance",
            "designation": "Super Administrator",
            "is_active": True,
        },
        {
            "user_id": uuid.UUID("33333333-3333-3333-3333-333333333333"),
            "email": "admin@test.com",
            "phone": "+919876500001",
            "hashed_password": hash_password("adminpassword123"),
            "full_name": "Dr. Sunita Kapoor",
            "role": "admin",
            "organization_id": org_id,
            "department": "Hospital Administration",
            "designation": "Chief Medical Director",
            "is_active": True,
        },
        {
            "user_id": uuid.UUID("44444444-4444-4444-4444-444444444444"),
            "email": "doctor@test.com",
            "phone": "+919876543210",
            "hashed_password": hash_password("doctorpassword123"),
            "full_name": "Dr. Rajesh Sharma",
            "role": "doctor",
            "organization_id": org_id,
            "department": "Cardiology",
            "designation": "Senior Interventional Cardiologist",
            "is_active": True,
        },
        {
            "user_id": uuid.UUID("55555555-5555-5555-5555-555555555555"),
            "email": "nurse@test.com",
            "phone": "+919876500005",
            "hashed_password": hash_password("nursepassword123"),
            "full_name": "Sister Sunita Verma",
            "role": "nurse",
            "organization_id": org_id,
            "department": "Inpatient Care",
            "designation": "Head Inpatient Ward Nurse",
            "is_active": True,
        },
        {
            "user_id": uuid.UUID("66666666-6666-6666-6666-666666666666"),
            "email": "patient@test.com",
            "phone": "+919876511111",
            "hashed_password": hash_password("patientpassword123"),
            "full_name": "Amit Kumar",
            "role": "patient",
            "organization_id": None,
            "department": None,
            "designation": None,
            "is_active": True,
        },
    ]

    for u in users_data:
        await session.execute(text("""
            INSERT INTO users (
                user_id, email, phone, hashed_password, full_name, role, organization_id,
                department, designation, is_active, created_at, updated_at
            ) VALUES (
                :user_id, :email, :phone, :hashed_password, :full_name, :role, :organization_id,
                :department, :designation, :is_active, NOW(), NOW()
            )
            ON CONFLICT (email) DO UPDATE SET
                hashed_password = EXCLUDED.hashed_password,
                is_active = EXCLUDED.is_active,
                organization_id = EXCLUDED.organization_id,
                updated_at = NOW()
        """), u)

    return users_data


async def seed_department_doctors(session: AsyncSession, org_id: uuid.UUID) -> list:
    """Seed exactly 10 Departmental Doctors (2 doctors for each of 5 departments)."""
    dept_doctors_raw = [
        # Cardiology (2 doctors)
        ("Dr. Rajesh Sharma", "doc.cardio1@aihos.org", "+919876543210", "Cardiology", "MCI-CARD-2015-8849", "Head of Cardiology", "MBBS, MD, DM (Cardiology), FACC", 16, "Room 101", "Morning", True),
        ("Dr. Anita Desai", "doc.cardio2@aihos.org", "+919876543211", "Cardiology", "MCI-CARD-2018-7721", "Consultant Cardiologist", "MBBS, MD, DNB (Cardiology)", 10, "Room 102", "Afternoon", False),

        # Neurology (2 doctors)
        ("Dr. Priya Patel", "doc.neuro1@aihos.org", "+919876543212", "Neurology", "MCI-NEUR-2018-4412", "Head of Neurology", "MBBS, MD, DM (Neurology)", 12, "Room 201", "Morning", True),
        ("Dr. Sameer Joshi", "doc.neuro2@aihos.org", "+919876543213", "Neurology", "MCI-NEUR-2020-5519", "Consultant Neurologist", "MBBS, MD, DM (Neurology)", 8, "Room 202", "Afternoon", False),

        # Pediatrics (2 doctors)
        ("Dr. Arjun Kumar", "doc.pedia1@aihos.org", "+919876543214", "Pediatrics", "MCI-PEDI-2016-9031", "Lead Pediatric Specialist", "MBBS, DCH, DNB (Pediatrics)", 14, "Room 301", "Morning", True),
        ("Dr. Neha Agarwal", "doc.pedia2@aihos.org", "+919876543215", "Pediatrics", "MCI-PEDI-2019-3824", "Consultant Pediatrician & Neonatologist", "MBBS, MD (Pediatrics)", 7, "Room 302", "Afternoon", False),

        # Orthopedics (2 doctors)
        ("Dr. Kavya Singh", "doc.ortho1@aihos.org", "+919876543216", "Orthopedics", "MCI-ORTH-2014-3129", "Senior Orthopedic Surgeon", "MBBS, MS (Orthopedics), MCh", 15, "Room 401", "Morning", True),
        ("Dr. Rohan Mehta", "doc.ortho2@aihos.org", "+919876543217", "Orthopedics", "MCI-ORTH-2017-8890", "Consultant Spine & Joint Specialist", "MBBS, MS (Orthopedics)", 9, "Room 402", "Afternoon", False),

        # Dermatology (2 doctors)
        ("Dr. Vikram Reddy", "doc.derm1@aihos.org", "+919876543218", "Dermatology", "MCI-DERM-2015-6612", "Senior Dermatologist", "MBBS, MD (DVL)", 13, "Room 501", "Morning", True),
        ("Dr. Pooja Chawla", "doc.derm2@aihos.org", "+919876543219", "Dermatology", "MCI-DERM-2019-4458", "Consultant Dermatologist & Dermatosurgeon", "MBBS, DVD, DNB", 6, "Room 502", "Afternoon", False),
    ]

    doctors = []
    pwd_hash = hash_password("doctorpassword123")

    for i, (name, email, phone, dept, lic, desig, qual, exp, room, shift, is_head) in enumerate(dept_doctors_raw, 1):
        user_id = uuid.UUID(f"77777777-1000-0000-0000-{i:012d}")
        doc_id = uuid.UUID(f"77777777-2000-0000-0000-{i:012d}")

        # 1. Create User login account
        await session.execute(text("""
            INSERT INTO users (
                user_id, email, phone, hashed_password, full_name, role, organization_id,
                department, designation, qualifications, experience_years, room_number, shift,
                is_active, created_at, updated_at
            ) VALUES (
                :user_id, :email, :phone, :pwd_hash, :full_name, 'doctor', :org_id,
                :department, :designation, :qualifications, :experience_years, :room_number, :shift,
                True, NOW(), NOW()
            )
            ON CONFLICT (email) DO UPDATE SET
                full_name = EXCLUDED.full_name,
                hashed_password = EXCLUDED.hashed_password,
                department = EXCLUDED.department,
                is_active = True,
                updated_at = NOW()
        """), {
            "user_id": user_id, "email": email, "phone": phone, "pwd_hash": pwd_hash,
            "full_name": name, "org_id": org_id, "department": dept, "designation": desig,
            "qualifications": qual, "experience_years": exp, "room_number": room, "shift": shift,
        })

        # 2. Create Doctor profile
        doc_record = {
            "doctor_id": doc_id,
            "user_id": user_id,
            "specialty": dept,
            "license_number": lic,
            "hospital_affiliation": "Apex Multi-Specialty Hospital",
            "email": email,
            "full_name": name,
            "phone": phone,
            "department": dept,
            "designation": desig,
            "qualifications": qual,
            "experience_years": exp,
            "room_number": room,
            "shift": shift,
            "is_head_physician": is_head,
        }
        await session.execute(text("""
            INSERT INTO doctors (
                doctor_id, user_id, specialty, license_number, hospital_affiliation, email,
                full_name, phone, department, designation, qualifications, experience_years,
                room_number, shift, is_head_physician, created_at, updated_at
            ) VALUES (
                :doctor_id, :user_id, :specialty, :license_number, :hospital_affiliation, :email,
                :full_name, :phone, :department, :designation, :qualifications, :experience_years,
                :room_number, :shift, :is_head_physician, NOW(), NOW()
            )
            ON CONFLICT (license_number) DO UPDATE SET
                user_id = EXCLUDED.user_id,
                full_name = EXCLUDED.full_name,
                email = EXCLUDED.email,
                specialty = EXCLUDED.specialty,
                department = EXCLUDED.department,
                updated_at = NOW()
        """), doc_record)

        doctors.append(doc_record)

    return doctors


async def seed_physicians(session: AsyncSession, org_id: uuid.UUID) -> list:
    """Seed 20 Specialized Physicians across clinical disciplines."""
    physicians_raw = [
        ("Dr. Sunita Rao", "physician1@aihos.org", "+919877000001", "Internal Medicine", "MCI-MED-2012-7641", "Senior Consultant Physician", "MBBS, MD (General Medicine)", 17, "Room 105", True),
        ("Dr. Alok Verma", "physician2@aihos.org", "+919877000002", "General Medicine", "MCI-MED-2014-1102", "Consultant Physician", "MBBS, MD", 12, "Room 106", False),
        ("Dr. Meera Nambiar", "physician3@aihos.org", "+919877000003", "Critical Care", "MCI-MED-2015-3341", "Lead Intensivist", "MBBS, MD, IDCCM", 11, "ICU Station", True),
        ("Dr. Harish Iyer", "physician4@aihos.org", "+919877000004", "Pulmonology", "MCI-MED-2016-8921", "Consultant Pulmonologist", "MBBS, MD (Pulmonary Medicine)", 10, "Room 205", False),
        ("Dr. Divya Saxena", "physician5@aihos.org", "+919877000005", "Gastroenterology", "MCI-MED-2013-4419", "Consultant Gastroenterologist", "MBBS, MD, DM (Gastro)", 14, "Room 206", False),
        ("Dr. Rakesh Kulkarni", "physician6@aihos.org", "+919877000006", "Nephrology", "MCI-MED-2015-7728", "Consultant Nephrologist", "MBBS, MD, DNB (Nephrology)", 11, "Dialysis Unit", False),
        ("Dr. Sangeeta Pillai", "physician7@aihos.org", "+919877000007", "Oncology", "MCI-MED-2014-9912", "Medical Oncologist", "MBBS, MD, DM (Medical Oncology)", 13, "Daycare Unit", False),
        ("Dr. Vivek Mathur", "physician8@aihos.org", "+919877000008", "Endocrinology", "MCI-MED-2017-2234", "Consultant Endocrinologist", "MBBS, MD, DM (Endocrinology)", 9, "Room 305", False),
        ("Dr. Ananya Sen", "physician9@aihos.org", "+919877000009", "Rheumatology", "MCI-MED-2018-6619", "Consultant Rheumatologist", "MBBS, MD, Fellowship (Rheumatology)", 8, "Room 306", False),
        ("Dr. Deepak Bhatt", "physician10@aihos.org", "+919877000010", "Infectious Disease", "MCI-MED-2016-5521", "Infectious Disease Specialist", "MBBS, MD, FNB (Infectious Diseases)", 10, "Isolation Ward", False),
        ("Dr. Shweta Ghosh", "physician11@aihos.org", "+919877000011", "Geriatric Medicine", "MCI-MED-2015-8832", "Senior Geriatric Physician", "MBBS, MD (Geriatrics)", 11, "Room 405", False),
        ("Dr. Manish Tiwari", "physician12@aihos.org", "+919877000012", "Emergency Medicine", "MCI-MED-2019-1192", "Emergency Triage Incharge", "MBBS, MEM (Emergency Medicine)", 7, "Trauma Bay 1", False),
        ("Dr. Radhika Menon", "physician13@aihos.org", "+919877000013", "Family Medicine", "MCI-MED-2017-3312", "Primary Care Physician", "MBBS, DNB (Family Medicine)", 9, "OPD Desk 1", False),
        ("Dr. Tarun Chopra", "physician14@aihos.org", "+919877000014", "Preventive Health", "MCI-MED-2018-7744", "Wellness & Health Checkup Lead", "MBBS, MD (Community Medicine)", 8, "Health Center", False),
        ("Dr. Bhavna Shah", "physician15@aihos.org", "+919877000015", "Hematology", "MCI-MED-2016-4481", "Consultant Hematologist", "MBBS, MD, DM (Clinical Hematology)", 10, "Room 505", False),
        ("Dr. Nikhil Grover", "physician16@aihos.org", "+919877000016", "Allergy & Immunology", "MCI-MED-2019-9923", "Allergy Specialist", "MBBS, MD, Fellowship (Immunology)", 6, "Room 506", False),
        ("Dr. Tanvi Hegde", "physician17@aihos.org", "+919877000017", "Palliative Care", "MCI-MED-2018-1123", "Palliative Care Physician", "MBBS, MD (Palliative Medicine)", 8, "Hospice Wing", False),
        ("Dr. Saurabh Malhotra", "physician18@aihos.org", "+919877000018", "General Surgery", "MCI-MED-2014-5591", "General & Laparoscopic Surgeon", "MBBS, MS (General Surgery)", 13, "OT Complex", False),
        ("Dr. Ritu Kapoor", "physician19@aihos.org", "+919877000019", "Clinical Pharmacology", "MCI-MED-2017-6644", "Hospital Pharmacotherapy Lead", "MBBS, MD (Pharmacology)", 9, "Pharmacy Lab", False),
        ("Dr. Siddharth Jain", "physician20@aihos.org", "+919877000020", "Neuro-Critical Care", "MCI-MED-2016-8819", "Neuro-Intensivist", "MBBS, MD, DM (Neuro-Anaesthesia)", 10, "Neuro ICU", False),
    ]

    physicians = []
    pwd_hash = hash_password("doctorpassword123")

    for i, (name, email, phone, dept, lic, desig, qual, exp, room, is_head) in enumerate(physicians_raw, 1):
        user_id = uuid.UUID(f"88888888-1000-0000-0000-{i:012d}")
        doc_id = uuid.UUID(f"88888888-2000-0000-0000-{i:012d}")

        # 1. Create User login account
        await session.execute(text("""
            INSERT INTO users (
                user_id, email, phone, hashed_password, full_name, role, organization_id,
                department, designation, qualifications, experience_years, room_number, shift,
                is_active, created_at, updated_at
            ) VALUES (
                :user_id, :email, :phone, :pwd_hash, :full_name, 'doctor', :org_id,
                :department, :designation, :qualifications, :experience_years, :room_number, 'Rotational Shift',
                True, NOW(), NOW()
            )
            ON CONFLICT (email) DO UPDATE SET
                full_name = EXCLUDED.full_name,
                hashed_password = EXCLUDED.hashed_password,
                department = EXCLUDED.department,
                is_active = True,
                updated_at = NOW()
        """), {
            "user_id": user_id, "email": email, "phone": phone, "pwd_hash": pwd_hash,
            "full_name": name, "org_id": org_id, "department": dept, "designation": desig,
            "qualifications": qual, "experience_years": exp, "room_number": room,
        })

        # 2. Create Doctor profile
        doc_record = {
            "doctor_id": doc_id,
            "user_id": user_id,
            "specialty": dept,
            "license_number": lic,
            "hospital_affiliation": "Apex Multi-Specialty Hospital",
            "email": email,
            "full_name": name,
            "phone": phone,
            "department": dept,
            "designation": desig,
            "qualifications": qual,
            "experience_years": exp,
            "room_number": room,
            "shift": "Rotational 24/7",
            "is_head_physician": is_head,
        }
        await session.execute(text("""
            INSERT INTO doctors (
                doctor_id, user_id, specialty, license_number, hospital_affiliation, email,
                full_name, phone, department, designation, qualifications, experience_years,
                room_number, shift, is_head_physician, created_at, updated_at
            ) VALUES (
                :doctor_id, :user_id, :specialty, :license_number, :hospital_affiliation, :email,
                :full_name, :phone, :department, :designation, :qualifications, :experience_years,
                :room_number, :shift, :is_head_physician, NOW(), NOW()
            )
            ON CONFLICT (license_number) DO UPDATE SET
                user_id = EXCLUDED.user_id,
                full_name = EXCLUDED.full_name,
                email = EXCLUDED.email,
                specialty = EXCLUDED.specialty,
                department = EXCLUDED.department,
                updated_at = NOW()
        """), doc_record)

        physicians.append(doc_record)

    return physicians


async def seed_nurses(session: AsyncSession, org_id: uuid.UUID) -> list:
    """Seed exactly 20 Inpatient Ward & Critical Care Nurses."""
    nurses_raw = [
        ("Sister Sunita Verma", "nurse@test.com", "+919876500005", "Inpatient Care", "Head Inpatient Ward Nurse", "M.Sc Nursing, Critical Care", 14, "Nursing Station 1", "Morning", "head_nurse"),
        ("Sister Preeti Thomas", "nurse2@aihos.org", "+919878000002", "Critical Care", "Senior ICU Incharge Nurse", "B.Sc Nursing, Post-Basic ICU", 12, "ICU Central Desk", "Morning", "nurse"),
        ("Nurse Rekha Nair", "nurse3@aihos.org", "+919878000003", "Cardiology", "Cardiac Care Unit (CCU) Nurse", "B.Sc Nursing", 8, "CCU Station", "Morning", "nurse"),
        ("Nurse Anitha Kurien", "nurse4@aihos.org", "+919878000004", "Pediatrics", "Pediatric Ward Staff Nurse", "GNM, Pediatric Care", 7, "Pediatric Station", "Afternoon", "nurse"),
        ("Nurse Mary Fernandez", "nurse5@aihos.org", "+919878000005", "Emergency & Trauma", "Emergency Staff Nurse", "B.Sc Nursing, Trauma Life Support", 9, "Trauma Nursing Desk", "Night", "nurse"),
        ("Nurse Geetha Krishnan", "nurse6@aihos.org", "+919878000006", "Orthopedics", "Orthopedic Post-Op Nurse", "GNM", 6, "Ortho Ward Desk", "Morning", "nurse"),
        ("Nurse Shilpa Deshmukh", "nurse7@aihos.org", "+919878000007", "Nephrology", "Dialysis Unit Staff Nurse", "B.Sc Nursing, Nephrology Cert", 8, "Dialysis Wing", "Morning", "nurse"),
        ("Nurse Kavita Rawat", "nurse8@aihos.org", "+919878000008", "Oncology", "Oncology Daycare Nurse", "B.Sc Nursing, Chemo Admin Cert", 7, "Daycare Station", "Morning", "nurse"),
        ("Nurse Blessy Mathew", "nurse9@aihos.org", "+919878000009", "General Surgery", "Surgical Step-Down Nurse", "GNM", 5, "Surgery Station", "Afternoon", "nurse"),
        ("Nurse Pooja Negi", "nurse10@aihos.org", "+919878000010", "Emergency & Trauma", "Triage Screening Nurse", "B.Sc Nursing", 4, "Triage Desk", "Morning", "nurse"),
        ("Nurse Deepa Swaminathan", "nurse11@aihos.org", "+919878000011", "Critical Care", "Night Shift ICU Incharge", "M.Sc Nursing (Critical Care)", 10, "ICU Central Desk", "Night", "nurse"),
        ("Nurse Mini Joseph", "nurse12@aihos.org", "+919878000012", "Pediatrics", "Neonatal ICU (NICU) Nurse", "B.Sc Nursing, Neonatal Care", 8, "NICU Station", "Night", "nurse"),
        ("Nurse Sarita Yadav", "nurse13@aihos.org", "+919878000013", "General Medicine", "General Medical Ward Nurse", "GNM", 6, "Ward 2 Desk", "Afternoon", "nurse"),
        ("Nurse Lissy Varghese", "nurse14@aihos.org", "+919878000014", "Hospital Administration", "Infection Control Nurse", "B.Sc Nursing, CIC Cert", 11, "Infection Office", "Morning", "nurse"),
        ("Nurse Usha Rani", "nurse15@aihos.org", "+919878000015", "Neurology", "Stroke Care Unit Nurse", "GNM, Neuro Cert", 7, "Neuro Ward Desk", "Morning", "nurse"),
        ("Nurse Sneha Patil", "nurse16@aihos.org", "+919878000016", "Outpatient Care", "Infusion Clinic Nurse", "B.Sc Nursing", 5, "OPD Infusion Wing", "Morning", "nurse"),
        ("Nurse Bindu Samuel", "nurse17@aihos.org", "+919878000017", "Inpatient Care", "Wound & Catheter Care Nurse", "GNM, Wound Care Specialist", 9, "Ward 3 Desk", "Afternoon", "nurse"),
        ("Nurse Ancy Philip", "nurse18@aihos.org", "+919878000018", "Critical Care", "High Dependency Unit (HDU) Nurse", "B.Sc Nursing", 6, "HDU Desk", "Night", "nurse"),
        ("Nurse Reena George", "nurse19@aihos.org", "+919878000019", "General Surgery", "Pre-Op Holding Nurse", "GNM", 7, "Pre-Op Area", "Morning", "nurse"),
        ("Nurse Jancy Abraham", "nurse20@aihos.org", "+919878000020", "Inpatient Care", "Palliative & Elderly Care Nurse", "B.Sc Nursing", 8, "Geriatric Wing Desk", "Morning", "nurse"),
    ]

    nurses = []
    pwd_hash = hash_password("nursepassword123")

    for i, (name, email, phone, dept, desig, qual, exp, room, shift, role) in enumerate(nurses_raw, 1):
        user_id = uuid.UUID(f"99999999-1000-0000-0000-{i:012d}")

        await session.execute(text("""
            INSERT INTO users (
                user_id, email, phone, hashed_password, full_name, role, organization_id,
                department, designation, qualifications, experience_years, room_number, shift,
                is_active, created_at, updated_at
            ) VALUES (
                :user_id, :email, :phone, :pwd_hash, :full_name, :role, :org_id,
                :department, :designation, :qualifications, :experience_years, :room_number, :shift,
                True, NOW(), NOW()
            )
            ON CONFLICT (email) DO UPDATE SET
                full_name = EXCLUDED.full_name,
                hashed_password = EXCLUDED.hashed_password,
                department = EXCLUDED.department,
                role = EXCLUDED.role,
                is_active = True,
                updated_at = NOW()
        """), {
            "user_id": user_id, "email": email, "phone": phone, "pwd_hash": pwd_hash,
            "full_name": name, "role": role, "org_id": org_id, "department": dept,
            "designation": desig, "qualifications": qual, "experience_years": exp,
            "room_number": room, "shift": shift,
        })

        nurses.append({
            "user_id": user_id, "email": email, "full_name": name, "role": role, "department": dept
        })

    return nurses


async def seed_patients(session: AsyncSession, user_map: dict) -> list:
    """Seed patient cohort."""
    primary_pat_uid = user_map.get("patient@test.com")

    patients_data = [
        {
            "patient_id": uuid.UUID("aaaaaaaa-0000-0000-0000-000000000001"),
            "user_id": primary_pat_uid,
            "abha_address": "amit.kumar@abdm",
            "full_name": "Amit Kumar",
            "date_of_birth": date(1985, 3, 15),
            "gender": "male",
            "phone": "+91-98765-11111",
            "email": "patient@test.com",
            "address": "B-204, Green Park Heights, New Delhi 110016",
            "emergency_contact_name": "Sunita Kumar (Wife)",
            "emergency_contact_phone": "+91-98765-11112",
        },
        {
            "patient_id": uuid.UUID("aaaaaaaa-0000-0000-0000-000000000002"),
            "user_id": None,
            "abha_address": "priya.sharma@abdm",
            "full_name": "Priya Sharma",
            "date_of_birth": date(1992, 7, 22),
            "gender": "female",
            "phone": "+91-98765-22222",
            "email": "priya.sharma@example.com",
            "address": "Flat 502, Silver Oaks Apartments, Gurgaon, Haryana 122002",
            "emergency_contact_name": "Vikram Sharma (Brother)",
            "emergency_contact_phone": "+91-98765-22223",
        },
        {
            "patient_id": uuid.UUID("aaaaaaaa-0000-0000-0000-000000000003"),
            "user_id": None,
            "abha_address": "rahul.singh@abdm",
            "full_name": "Rahul Singh",
            "date_of_birth": date(1978, 11, 5),
            "gender": "male",
            "phone": "+91-98765-33333",
            "email": "rahul.singh@example.com",
            "address": "House 14, Sector 17, Chandigarh 160017",
            "emergency_contact_name": "Meena Singh (Spouse)",
            "emergency_contact_phone": "+91-98765-33334",
        },
        {
            "patient_id": uuid.UUID("aaaaaaaa-0000-0000-0000-000000000004"),
            "user_id": None,
            "abha_address": "anjali.gupta@abdm",
            "full_name": "Anjali Gupta",
            "date_of_birth": date(1995, 1, 30),
            "gender": "female",
            "phone": "+91-98765-44444",
            "email": "anjali.gupta@example.com",
            "address": "401 Royal Palms, Indiranagar, Bangalore 560038",
            "emergency_contact_name": "Deepak Gupta (Father)",
            "emergency_contact_phone": "+91-98765-44445",
        },
        {
            "patient_id": uuid.UUID("aaaaaaaa-0000-0000-0000-000000000005"),
            "user_id": None,
            "abha_address": "suresh.nair@abdm",
            "full_name": "Suresh Nair",
            "date_of_birth": date(1963, 9, 12),
            "gender": "male",
            "phone": "+91-98765-55555",
            "email": "suresh.nair@example.com",
            "address": "C-12, Palm Meadows, Kochi, Kerala 682001",
            "emergency_contact_name": "Lakshmi Nair (Daughter)",
            "emergency_contact_phone": "+91-98765-55556",
        },
    ]

    for p in patients_data:
        await session.execute(text("""
            INSERT INTO patients (
                patient_id, user_id, abha_address, full_name, date_of_birth, gender,
                phone, email, address, emergency_contact_name, emergency_contact_phone,
                created_at, updated_at
            ) VALUES (
                :patient_id, :user_id, :abha_address, :full_name, :date_of_birth, :gender,
                :phone, :email, :address, :emergency_contact_name, :emergency_contact_phone,
                NOW(), NOW()
            )
            ON CONFLICT (abha_address) DO UPDATE SET
                full_name = EXCLUDED.full_name,
                user_id = EXCLUDED.user_id,
                phone = EXCLUDED.phone,
                updated_at = NOW()
        """), p)

    return patients_data


async def seed_appointments(session: AsyncSession, doctors: list, patients: list) -> list:
    """Seed scheduled and completed appointments."""
    base_time = datetime.now().replace(minute=0, second=0, microsecond=0)

    appts = [
        # 1. Upcoming Cardiology Appointment (Amit Kumar with Dr. Rajesh Sharma)
        {
            "appointment_id": uuid.UUID("bbbbbbbb-0000-0000-0000-000000000001"),
            "patient_id": patients[0]["patient_id"],
            "doctor_id": doctors[0]["doctor_id"],
            "scheduled_at": base_time + timedelta(days=1, hours=2),
            "duration_minutes": 30,
            "status": "scheduled",
            "notes": "Follow-up consultation for blood pressure management and ECG evaluation.",
            "reason": "Chest tightness and routine BP check",
            "meeting_link": "https://meet.ai-hos.org/room-cardio-101",
            "telehealth_room_id": "apex-room-cardio-101",
        },
        # 2. Upcoming Neurology Appointment (Priya Sharma with Dr. Priya Patel)
        {
            "appointment_id": uuid.UUID("bbbbbbbb-0000-0000-0000-000000000002"),
            "patient_id": patients[1]["patient_id"],
            "doctor_id": doctors[2]["doctor_id"],
            "scheduled_at": base_time + timedelta(days=2, hours=4),
            "duration_minutes": 30,
            "status": "scheduled",
            "notes": "Recurring migraine headache evaluation with photophobia.",
            "reason": "Severe morning headaches",
            "meeting_link": "https://meet.ai-hos.org/room-neuro-201",
            "telehealth_room_id": "apex-room-neuro-201",
        },
        # 3. Completed Past Consultation (Amit Kumar with Dr. Rajesh Sharma)
        {
            "appointment_id": uuid.UUID("bbbbbbbb-0000-0000-0000-000000000003"),
            "patient_id": patients[0]["patient_id"],
            "doctor_id": doctors[0]["doctor_id"],
            "scheduled_at": base_time - timedelta(days=5, hours=3),
            "duration_minutes": 30,
            "status": "completed",
            "notes": "Initial diagnostic visit. ECG ordered, lifestyle modifications advised.",
            "reason": "Stage 1 Hypertension check",
            "meeting_link": None,
            "telehealth_room_id": None,
        },
        # 4. In-Progress Consultation (Rahul Singh with Dr. Arjun Kumar)
        {
            "appointment_id": uuid.UUID("bbbbbbbb-0000-0000-0000-000000000004"),
            "patient_id": patients[2]["patient_id"],
            "doctor_id": doctors[4]["doctor_id"],
            "scheduled_at": base_time,
            "duration_minutes": 25,
            "status": "in_progress",
            "notes": "Active clinical tele-consultation in room.",
            "reason": "Seasonal asthma flare-up",
            "meeting_link": "https://meet.ai-hos.org/room-pedi-301",
            "telehealth_room_id": "apex-room-pedi-301",
        },
    ]

    try:
        check_enum = await session.execute(text(
            "SELECT enumlabel FROM pg_enum JOIN pg_type ON pg_enum.enumtypid = pg_type.oid WHERE typname IN ('appointmentstatus', 'appointment_status');"
        ))
        valid_statuses = {r[0] for r in check_enum.fetchall()}
    except Exception:
        valid_statuses = set()

    for a in appts:
        st = a["status"]
        if valid_statuses and st not in valid_statuses:
            if st.upper() in valid_statuses:
                a["status"] = st.upper()
            elif st.lower() in valid_statuses:
                a["status"] = st.lower()

        await session.execute(text("""
            INSERT INTO appointments (
                appointment_id, patient_id, doctor_id, scheduled_at, duration_minutes,
                status, notes, reason, meeting_link, telehealth_room_id, created_at, updated_at
            ) VALUES (
                :appointment_id, :patient_id, :doctor_id, :scheduled_at, :duration_minutes,
                :status, :notes, :reason, :meeting_link, :telehealth_room_id, NOW(), NOW()
            )
            ON CONFLICT (appointment_id) DO UPDATE SET
                status = EXCLUDED.status,
                scheduled_at = EXCLUDED.scheduled_at,
                updated_at = NOW()
        """), a)

    return appts


async def seed_medical_records(session: AsyncSession, doctors: list, patients: list, appointments: list) -> list:
    """Seed finalized records and drafts for the Doctor Review Gate."""
    records = [
        # Record 1: Finalized Historical Encounter
        {
            "record_id": uuid.UUID("cccccccc-0000-0000-0000-000000000001"),
            "patient_id": patients[0]["patient_id"],
            "doctor_id": doctors[0]["doctor_id"],
            "appointment_id": appointments[2]["appointment_id"],
            "content": json.dumps({
                "chief_complaint": "Persistent elevated blood pressure with occasional morning dizziness.",
                "history_present_illness": "Patient reports blood pressure readings fluctuating around 145/95 mmHg over the past 3 weeks. Low-sodium diet compliance confirmed.",
                "physical_examination": "BP: 142/92 mmHg, Pulse: 78 bpm, SpO2: 98% on room air, BMI: 26.4. Cardiovascular: Normal S1/S2, no murmurs. Lungs clear.",
                "assessment": "Essential Primary Hypertension (Stage 1), un-optimized on current single-agent therapy.",
                "plan": "1. Increase Telmisartan to 40mg daily.\n2. Add Amlodipine 5mg morning.\n3. Daily morning and evening home BP logging.",
                "diagnosis_codes": ["I10", "R03.0"],
                "confidence": 0.94,
                "basis": "Clinical examination and home blood pressure log review.",
            }),
            "status": "FINALIZED",
            "finalized_at": datetime.now() - timedelta(days=5),
        },
        # Record 2: DRAFT awaiting Doctor Review Gate in /doctor/approvals
        {
            "record_id": uuid.UUID("cccccccc-0000-0000-0000-000000000002"),
            "patient_id": patients[0]["patient_id"],
            "doctor_id": doctors[0]["doctor_id"],
            "appointment_id": appointments[0]["appointment_id"],
            "content": json.dumps({
                "chief_complaint": "Mild exertional shortness of breath when climbing stairs.",
                "history_present_illness": "Patient describes mild tightness and dyspnea after climbing two flights of stairs. Denies chest pain radiating to left arm.",
                "physical_examination": "BP: 136/86 mmHg, Pulse: 82 bpm, SpO2: 97%. JVP normal. Peripheral pulses well-felt.",
                "assessment": "Atypical exertional dyspnea; evaluate for early coronary artery disease vs deconditioning.",
                "plan": "1. Schedule Exercise Treadmill Test (TMT).\n2. Fasting Lipid Profile & HbA1c.\n3. Continue cardioprotective anti-hypertensive regimen.",
                "diagnosis_codes": ["R06.02", "I25.9"],
                "confidence": 0.88,
                "basis": "Ambient dictation transcription synthesized by Copilot Scribe Agent.",
            }),
            "status": "DRAFT",
            "finalized_at": None,
        },
        # Record 3: DRAFT awaiting Doctor Review Gate for Patient 2 (Neurology)
        {
            "record_id": uuid.UUID("cccccccc-0000-0000-0000-000000000003"),
            "patient_id": patients[1]["patient_id"],
            "doctor_id": doctors[2]["doctor_id"],
            "appointment_id": appointments[1]["appointment_id"],
            "content": json.dumps({
                "chief_complaint": "Unilateral throbbing right-sided headache with visual aura.",
                "history_present_illness": "Episodes occurring 3 times per week lasting 6-8 hours each. Preceded by zig-zag visual flashes.",
                "physical_examination": "Cranial nerves II-XII intact. Fundus exam normal. Neck supple.",
                "assessment": "Migraine with aura (G43.109).",
                "plan": "1. Propranolol 40mg twice daily for prophylaxis.\n2. Rizatriptan 10mg PRN for acute attacks.",
                "diagnosis_codes": ["G43.109"],
                "confidence": 0.91,
                "basis": "Intake questionnaire responses synthesized by Scribe Agent.",
            }),
            "status": "DRAFT",
            "finalized_at": None,
        },
    ]

    try:
        check_mr = await session.execute(text(
            "SELECT enumlabel FROM pg_enum JOIN pg_type ON pg_enum.enumtypid = pg_type.oid WHERE typname IN ('medicalrecordstatus', 'medical_record_status');"
        ))
        valid_mr = {r[0] for r in check_mr.fetchall()}
    except Exception:
        valid_mr = set()

    for r in records:
        st = r["status"]
        if valid_mr and st not in valid_mr:
            if st.lower() in valid_mr:
                r["status"] = st.lower()
            elif st.upper() in valid_mr:
                r["status"] = st.upper()

        await session.execute(text("""
            INSERT INTO medical_records (
                record_id, patient_id, doctor_id, appointment_id, content, status,
                finalized_at, created_at, updated_at
            ) VALUES (
                :record_id, :patient_id, :doctor_id, :appointment_id, CAST(:content AS json), :status,
                :finalized_at, NOW(), NOW()
            )
            ON CONFLICT (record_id) DO UPDATE SET
                content = CAST(EXCLUDED.content AS json),
                status = EXCLUDED.status,
                finalized_at = EXCLUDED.finalized_at,
                updated_at = NOW()
        """), r)

    return records


async def seed_prescriptions(session: AsyncSession, doctors: list, patients: list, records: list) -> list:
    """Seed finalized and draft prescriptions."""
    prescriptions = [
        # Rx 1: Finalized Prescription linked to completed record
        {
            "prescription_id": uuid.UUID("dddddddd-0000-0000-0000-000000000001"),
            "medical_record_id": records[0]["record_id"],
            "patient_id": patients[0]["patient_id"],
            "doctor_id": doctors[0]["doctor_id"],
            "medications": json.dumps([
                {
                    "name": "Telmisartan",
                    "dosage": "40mg",
                    "frequency": "Once daily",
                    "duration": "90 days",
                    "instructions": "Take in the morning after breakfast.",
                },
                {
                    "name": "Amlodipine",
                    "dosage": "5mg",
                    "frequency": "Once daily",
                    "duration": "90 days",
                    "instructions": "Take with water. Monitor for mild pedal edema.",
                },
            ]),
            "status": "FINALIZED",
            "notes": "Anti-hypertensive maintenance therapy. Do not discontinue without consultation.",
            "finalized_at": datetime.now() - timedelta(days=5),
        },
        # Rx 2: DRAFT Prescription in Review Gate with Interaction Warning
        {
            "prescription_id": uuid.UUID("dddddddd-0000-0000-0000-000000000002"),
            "medical_record_id": records[1]["record_id"],
            "patient_id": patients[0]["patient_id"],
            "doctor_id": doctors[0]["doctor_id"],
            "medications": json.dumps([
                {
                    "name": "Atorvastatin",
                    "dosage": "20mg",
                    "frequency": "Once daily at bedtime",
                    "duration": "30 days",
                    "instructions": "Take at night. Avoid grapefruit juice.",
                },
                {
                    "name": "Aspirin (Ecosprin)",
                    "dosage": "75mg",
                    "frequency": "Once daily",
                    "duration": "30 days",
                    "instructions": "Take after meals to prevent gastric irritation.",
                },
            ]),
            "status": "DRAFT",
            "notes": "Draft generated by Prescription Agent. Clinician review required.",
            "finalized_at": None,
        },
    ]

    try:
        check_rx = await session.execute(text(
            "SELECT enumlabel FROM pg_enum JOIN pg_type ON pg_enum.enumtypid = pg_type.oid WHERE typname IN ('prescriptionstatus', 'prescription_status');"
        ))
        valid_rx = {r[0] for r in check_rx.fetchall()}
    except Exception:
        valid_rx = set()

    for p in prescriptions:
        st = p["status"]
        if valid_rx and st not in valid_rx:
            if st.lower() in valid_rx:
                p["status"] = st.lower()
            elif st.upper() in valid_rx:
                p["status"] = st.upper()

        await session.execute(text("""
            INSERT INTO prescriptions (
                prescription_id, medical_record_id, patient_id, doctor_id, medications,
                status, notes, finalized_at, created_at, updated_at
            ) VALUES (
                :prescription_id, :medical_record_id, :patient_id, :doctor_id, CAST(:medications AS json),
                :status, :notes, :finalized_at, NOW(), NOW()
            )
            ON CONFLICT (prescription_id) DO UPDATE SET
                medications = CAST(EXCLUDED.medications AS json),
                status = EXCLUDED.status,
                notes = EXCLUDED.notes,
                finalized_at = EXCLUDED.finalized_at,
                updated_at = NOW()
        """), p)

    return prescriptions


async def seed_consents(session: AsyncSession, patients: list, doctors: list) -> list:
    """Seed data access consents."""
    consents = [
        {
            "consent_id": uuid.UUID("eeeeeeee-0000-0000-0000-000000000001"),
            "patient_id": patients[0]["patient_id"],
            "provider_id": doctors[0]["doctor_id"],
            "record_scope": "full_access",
            "granted_at": datetime.now() - timedelta(days=30),
            "revoked_at": None,
        },
        {
            "consent_id": uuid.UUID("eeeeeeee-0000-0000-0000-000000000002"),
            "patient_id": patients[1]["patient_id"],
            "provider_id": doctors[2]["doctor_id"],
            "record_scope": "full_access",
            "granted_at": datetime.now() - timedelta(days=20),
            "revoked_at": None,
        },
        {
            "consent_id": uuid.UUID("eeeeeeee-0000-0000-0000-000000000003"),
            "patient_id": patients[2]["patient_id"],
            "provider_id": doctors[4]["doctor_id"],
            "record_scope": "records_only",
            "granted_at": datetime.now() - timedelta(days=10),
            "revoked_at": None,
        },
    ]

    try:
        check_cs = await session.execute(text(
            "SELECT enumlabel FROM pg_enum JOIN pg_type ON pg_enum.enumtypid = pg_type.oid WHERE typname IN ('consentscope', 'consent_scope');"
        ))
        valid_cs = {r[0] for r in check_cs.fetchall()}
    except Exception:
        valid_cs = set()

    for c in consents:
        st = c["record_scope"]
        if valid_cs and st not in valid_cs:
            if st.lower() in valid_cs:
                c["record_scope"] = st.lower()
            elif st.upper() in valid_cs:
                c["record_scope"] = st.upper()

        await session.execute(text("""
            INSERT INTO consents (
                consent_id, patient_id, provider_id, record_scope, granted_at, revoked_at,
                created_at, updated_at
            ) VALUES (
                :consent_id, :patient_id, :provider_id, :record_scope, :granted_at, :revoked_at,
                NOW(), NOW()
            )
            ON CONFLICT (consent_id) DO NOTHING
        """), c)

    return consents


async def seed_inpatient_workstation(session: AsyncSession, org_id: uuid.UUID, patients: list) -> int:
    """Seed inpatient beds, historical vitals logs and shift tasks."""
    beds = [
        {
            "bed_id": uuid.UUID("ffffffff-0000-0000-0000-000000000001"),
            "bed_number": "Bed 101-A",
            "ward": "Cardiology Step-Down Ward",
            "status": "occupied",
            "clinical_status": "Stable",
            "patient_id": patients[0]["patient_id"],
            "patient_name": "Amit Kumar",
            "uhid": "UHID-APEX-2026-9041",
            "age": 41,
            "gender": "Male",
            "admitted_for": "Post-PCI Observation & Anti-hypertensive Stabilization",
            "attending_physician": "Dr. Rajesh Sharma",
            "admitted_at": datetime.now() - timedelta(days=2),
            "admit_day": 3,
            "diet": "Low Salt, Cardiac Diet",
            "allergies": json.dumps(["Penicillin"]),
            "code_status": "Full Code",
            "isolation_precautions": "None",
            "next_medication": "Amlodipine 5mg",
            "medication_due": "14:00 Round",
            "bp": "128/82",
            "systolic": 128,
            "diastolic": 82,
            "pulse": 74,
            "spo2": 98,
            "temp": 98.4,
            "respiratory_rate": 16,
            "pain_score": 1,
            "organization_id": org_id,
        },
        {
            "bed_id": uuid.UUID("ffffffff-0000-0000-0000-000000000002"),
            "bed_number": "Bed 201-ICU",
            "ward": "Intensive Care Unit (ICU)",
            "status": "occupied",
            "clinical_status": "Attention",
            "patient_id": patients[2]["patient_id"],
            "patient_name": "Rahul Singh",
            "uhid": "UHID-APEX-2026-8812",
            "age": 48,
            "gender": "Male",
            "admitted_for": "Severe Acute Bronchospasm & Respiratory Monitoring",
            "attending_physician": "Dr. Meera Nambiar",
            "admitted_at": datetime.now() - timedelta(days=1),
            "admit_day": 2,
            "diet": "Diabetic Soft Diet",
            "allergies": json.dumps(["Sulfa Drugs"]),
            "code_status": "Full Code",
            "isolation_precautions": "Contact Precautions",
            "next_medication": "Nebulized Budesonide 0.5mg",
            "medication_due": "15:30 Round",
            "bp": "135/88",
            "systolic": 135,
            "diastolic": 88,
            "pulse": 88,
            "spo2": 95,
            "temp": 99.1,
            "respiratory_rate": 20,
            "pain_score": 2,
            "organization_id": org_id,
        },
        {
            "bed_id": uuid.UUID("ffffffff-0000-0000-0000-000000000003"),
            "bed_number": "Bed 202-ICU",
            "ward": "Intensive Care Unit (ICU)",
            "status": "vacant",
            "clinical_status": "Stable",
            "patient_id": None,
            "patient_name": "Vacant / Reserved",
            "uhid": "N/A",
            "age": 0,
            "gender": "N/A",
            "admitted_for": "Sanitized and Ready for Admission",
            "attending_physician": "On-Duty Intensivist",
            "admitted_at": datetime.now(),
            "admit_day": 0,
            "diet": "N/A",
            "allergies": json.dumps([]),
            "code_status": "Full Code",
            "isolation_precautions": None,
            "next_medication": "None",
            "medication_due": "N/A",
            "bp": "120/80",
            "systolic": 120,
            "diastolic": 80,
            "pulse": 72,
            "spo2": 99,
            "temp": 98.6,
            "respiratory_rate": 16,
            "pain_score": 0,
            "organization_id": org_id,
        },
    ]

    for b in beds:
        await session.execute(text("""
            INSERT INTO inpatient_beds (
                bed_id, bed_number, ward, status, clinical_status, patient_id, patient_name,
                uhid, age, gender, admitted_for, attending_physician, admitted_at, admit_day,
                diet, allergies, code_status, isolation_precautions, next_medication,
                medication_due, bp, systolic, diastolic, pulse, spo2, temp, respiratory_rate,
                pain_score, vitals_last_checked, organization_id, created_at, updated_at
            ) VALUES (
                :bed_id, :bed_number, :ward, :status, :clinical_status, :patient_id, :patient_name,
                :uhid, :age, :gender, :admitted_for, :attending_physician, :admitted_at, :admit_day,
                :diet, CAST(:allergies AS json), :code_status, :isolation_precautions, :next_medication,
                :medication_due, :bp, :systolic, :diastolic, :pulse, :spo2, :temp, :respiratory_rate,
                :pain_score, NOW(), :organization_id, NOW(), NOW()
            )
            ON CONFLICT (bed_id) DO UPDATE SET
                status = EXCLUDED.status,
                clinical_status = EXCLUDED.clinical_status,
                bp = EXCLUDED.bp,
                pulse = EXCLUDED.pulse,
                spo2 = EXCLUDED.spo2,
                updated_at = NOW()
        """), b)

    return len(beds)


async def seed_patient_extras(session: AsyncSession, patients: list) -> int:
    """Seed patient reminders and uploaded lab reports."""
    # 1. Medicine Reminders
    reminders = [
        {
            "reminder_id": uuid.UUID("11111111-2222-3333-4444-555555555551"),
            "patient_id": patients[0]["patient_id"],
            "medication_name": "Telmisartan 40mg",
            "dosage": "1 Tablet",
            "frequency": "Once daily",
            "times_of_day": json.dumps(["08:30"]),
            "instructions": "Take after breakfast with a full glass of water.",
            "is_active": True,
        },
        {
            "reminder_id": uuid.UUID("11111111-2222-3333-4444-555555555552"),
            "patient_id": patients[0]["patient_id"],
            "medication_name": "Amlodipine 5mg",
            "dosage": "1 Tablet",
            "frequency": "Once daily",
            "times_of_day": json.dumps(["20:30"]),
            "instructions": "Take after dinner.",
            "is_active": True,
        },
    ]

    for r in reminders:
        await session.execute(text("""
            INSERT INTO medicine_reminders (
                reminder_id, patient_id, medication_name, dosage, frequency,
                times_of_day, instructions, is_active, created_at, updated_at
            ) VALUES (
                :reminder_id, :patient_id, :medication_name, :dosage, :frequency,
                CAST(:times_of_day AS json), :instructions, :is_active, NOW(), NOW()
            )
            ON CONFLICT (reminder_id) DO NOTHING
        """), r)

    # 2. Patient Report
    report = {
        "report_id": uuid.UUID("22222222-3333-4444-5555-666666666661"),
        "patient_id": patients[0]["patient_id"],
        "title": "Comprehensive Lipid Panel & HbA1c Report",
        "report_type": "lab",
        "file_name": "lipid_profile_amit_kumar.pdf",
        "file_path": "/storage/reports/lipid_profile_amit_kumar.pdf",
        "file_size_bytes": 142850,
        "mime_type": "application/pdf",
        "notes": "Total Cholesterol 192 mg/dL, HDL 46 mg/dL, LDL 118 mg/dL, HbA1c 5.8%.",
    }
    await session.execute(text("""
        INSERT INTO patient_reports (
            report_id, patient_id, title, report_type, file_name, file_path,
            file_size_bytes, mime_type, notes, created_at, updated_at
        ) VALUES (
            :report_id, :patient_id, :title, :report_type, :file_name, :file_path,
            :file_size_bytes, :mime_type, :notes, NOW(), NOW()
        )
        ON CONFLICT (report_id) DO NOTHING
    """), report)

    return len(reminders)


if __name__ == "__main__":
    asyncio.run(seed_database())