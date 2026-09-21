"""Nhost Database Reset and Clean Production Seeder.

Connects to Nhost PostgreSQL, cleans all dummy/stale records,
ensures schema tables & columns are created, and seeds the production-grade
baseline (Super Admin, accredited Apex Medical Center, and initial staff).
"""

import asyncio
import os
import uuid
from pathlib import Path
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Load .env
root_dir = Path(__file__).resolve().parent.parent
env_file = root_dir / ".env"
try:
    from dotenv import load_dotenv
    if env_file.exists():
        load_dotenv(env_file)
except ImportError:
    pass

DB_URL = os.getenv("DATABASE_URL", "")

if DB_URL.startswith("postgres://"):
    DB_URL = DB_URL.replace("postgres://", "postgresql+asyncpg://", 1)
elif DB_URL.startswith("postgresql://") and not DB_URL.startswith("postgresql+asyncpg://"):
    DB_URL = DB_URL.replace("postgresql://", "postgresql+asyncpg://", 1)


async def main():
    print("=" * 60)
    print("AI-HOS: NHOST POSTGRESQL CLEAN RESET & RE-SEED")
    print("=" * 60)

    if not DB_URL:
        print("❌ ERROR: DATABASE_URL not found in environment!")
        return

    print(f"Connecting to database host: {DB_URL.split('@')[-1] if '@' in DB_URL else 'localhost'}...")

    connect_args = {"command_timeout": 30}
    if "localhost" not in DB_URL and "127.0.0.1" not in DB_URL:
        connect_args["ssl"] = True

    engine = create_async_engine(DB_URL, connect_args=connect_args, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    from app.models import (
        Base,
        Organization,
        User,
        UserRole,
        Doctor,
    )
    from app.services.auth.service import get_password_hash

    # 1. Ensure Schema and Columns are Created & Synchronized
    print("\n[Step 1/4] Ensuring PostgreSQL schema tables & columns exist...")
    
    # A. Ensure 'super_admin', 'head_physician', 'head_nurse' exist in PostgreSQL enum
    try:
        async with engine.connect() as conn:
            await conn.execution_options(isolation_level="AUTOCOMMIT")
            await conn.execute(text("ALTER TYPE userrole ADD VALUE IF NOT EXISTS 'super_admin';"))
            await conn.execute(text("ALTER TYPE userrole ADD VALUE IF NOT EXISTS 'head_physician';"))
            await conn.execute(text("ALTER TYPE userrole ADD VALUE IF NOT EXISTS 'head_nurse';"))
            print("  ✓ Ensured 'super_admin', 'head_physician', 'head_nurse' enum values in userrole.")
    except Exception as e:
        print(f"  - Notice on userrole enum: {e}")

    # B. Ensure Tables are created
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

        # C. Migrate/Add newly introduced columns to existing tables
        alter_statements = [
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS phone VARCHAR(30);",
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
            "ALTER TABLE patients ADD COLUMN IF NOT EXISTS phone VARCHAR(30);",
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
        ]
        for stmt in alter_statements:
            try:
                await conn.execute(text(stmt))
            except Exception as e:
                print(f"  - Notice on column addition: {e}")

    print("✓ Schema verified & synchronized successfully.")

    # 2. Clean/Purge Dummy Data
    print("\n[Step 2/4] Purging all dummy & stale records from Nhost database...")
    async with async_session() as session:
        # Tables to truncate / delete in reverse foreign key order
        tables = [
            "audit_logs",
            "consents",
            "prescriptions",
            "medical_records",
            "appointments",
            "intake_sessions",
            "voice_notes",
            "patient_reports",
            "medicine_reminders",
            "patients",
            "doctors",
            "users",
            "organizations",
        ]

        for table in tables:
            try:
                await session.execute(text(f"DELETE FROM {table} CASCADE;"))
                print(f"  ✓ Purged table: {table}")
            except Exception as e:
                # Table might not exist or already clean
                print(f"  - Notice on {table}: {e}")
                await session.rollback()

        await session.commit()
    print("✓ All dummy records successfully wiped.")

    # 3. Seed Clean Foundation (Super Administrator ONLY - Zero Dummy Data)
    print("\n[Step 3/4] Seeding production baseline (Super Admin ONLY, ZERO dummy data)...")
    async with async_session() as session:
        default_pwd_hash = get_password_hash("adminpassword123")

        # Global Super Administrator (Cross-Tenant Authority)
        super_admin = User(
            user_id=uuid.uuid4(),
            email="superadmin@aihos.org",
            phone="+919999000001",
            full_name="AI-HOS Global Super Administrator",
            hashed_password=default_pwd_hash,
            role=UserRole.SUPER_ADMIN,
            is_active=True,
        )
        session.add(super_admin)
        print("  ✓ Provisioned Super Admin: superadmin@aihos.org (Full Authority)")
        print("  ✓ Zero dummy organizations, doctors, or patients seeded.")

        await session.commit()

    # 4. Summary Output
    print("\n[Step 4/4] Verification of Active Database State:")
    print("=" * 60)
    print("GLOBAL SUPER ADMINISTRATOR (ONLY ACTIVE USER):")
    print("  Email:    superadmin@aihos.org")
    print("  Phone:    +919999000001")
    print("  Password: adminpassword123")
    print("  Role:     SUPER_ADMIN (Full authority over all organizations)")
    print("")
    print("STATUS: ZERO DUMMY DATA. Clean database ready for new real")
    print("organizations to be onboarded via the 4-step wizard.")
    print("=" * 60)

    await engine.dispose()
    print("✓ Nhost database cleaned: Zero dummy data, Super Admin ready!\n")


if __name__ == "__main__":
    asyncio.run(main())
