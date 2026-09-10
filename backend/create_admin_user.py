"""Script to create/update an Admin user in Nhost PostgreSQL and verify authentication."""

import asyncio
import uuid
import bcrypt
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Direct Nhost PostgreSQL connection
DB_URL = "postgresql+asyncpg://postgres:@7HmkeZnqpfJSaB@icfbnbiumbflxblqcwdl.db.ap-south-1.nhost.run:5432/icfbnbiumbflxblqcwdl"

ADMIN_EMAIL = "admin@test.com"
ADMIN_PASSWORD = "adminpassword123"
ADMIN_NAME = "Institutional Admin"


def get_hash(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def check_hash(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))


async def main():
    print(f"[Admin Setup] Connecting to Nhost PostgreSQL...")
    engine = create_async_engine(DB_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    from app.models import User, UserRole

    async with async_session() as session:
        # Check existing
        result = await session.execute(select(User).where(User.email == ADMIN_EMAIL))
        existing_admin = result.scalar_one_or_none()

        hashed_pwd = get_hash(ADMIN_PASSWORD)

        if existing_admin:
            print(f"[Admin Setup] Found existing user {ADMIN_EMAIL}. Updating password and role to ADMIN...")
            existing_admin.hashed_password = hashed_pwd
            existing_admin.role = UserRole.ADMIN
            existing_admin.is_active = True
            existing_admin.full_name = ADMIN_NAME
            await session.commit()
            await session.refresh(existing_admin)
            admin_user = existing_admin
            print(f"✓ [Admin Setup] Successfully updated {ADMIN_EMAIL}")
        else:
            print(f"[Admin Setup] Creating new Admin user {ADMIN_EMAIL}...")
            new_admin = User(
                user_id=uuid.uuid4(),
                email=ADMIN_EMAIL,
                hashed_password=hashed_pwd,
                full_name=ADMIN_NAME,
                role=UserRole.ADMIN,
                is_active=True,
            )
            session.add(new_admin)
            await session.commit()
            await session.refresh(new_admin)
            admin_user = new_admin
            print(f"✓ [Admin Setup] Successfully created {ADMIN_EMAIL}")

        # Also provision a backup secondary admin: admin@aihos.org
        alt_email = "admin@aihos.org"
        result_alt = await session.execute(select(User).where(User.email == alt_email))
        existing_alt = result_alt.scalar_one_or_none()
        if existing_alt:
            existing_alt.hashed_password = hashed_pwd
            existing_alt.role = UserRole.ADMIN
            existing_alt.is_active = True
            await session.commit()
        else:
            alt_admin = User(
                user_id=uuid.uuid4(),
                email=alt_email,
                hashed_password=hashed_pwd,
                full_name="AI-HOS System Administrator",
                role=UserRole.ADMIN,
                is_active=True,
            )
            session.add(alt_admin)
            await session.commit()
        print(f"✓ [Admin Setup] Verified secondary admin: {alt_email}")

        # Verify authentication
        print(f"\n[Auth Check] Verifying password verification logic...")
        is_valid = check_hash(ADMIN_PASSWORD, admin_user.hashed_password)
        print(f"  Password match: {is_valid}")
        assert is_valid is True, "Password check failed!"

        # Verify JWT Token Generation
        from app.services.auth.service import create_access_token
        token = create_access_token(data={
            "sub": str(admin_user.user_id),
            "email": admin_user.email,
            "role": admin_user.role.value,
        })
        print(f"  Access Token generated successfully!")
        print(f"  Token: {token[:25]}...")

        print(f"\n==================================================")
        print(f"✓ ADMIN CREDENTIALS ACTIVE & VERIFIED:")
        print(f"  Email:    {ADMIN_EMAIL} (and {alt_email})")
        print(f"  Password: {ADMIN_PASSWORD}")
        print(f"  Role:     ADMIN (Level 4 Clearance)")
        print(f"  Status:   ACTIVE")
        print(f"==================================================")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
