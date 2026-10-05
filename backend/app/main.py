import os
from fastapi import FastAPI  # type: ignore

from app.api import (
    appointments,
    approval,
    auth,
    consent,
    doctors,
    medical_records,
    patients,
    prescriptions,
    voice_notes,
    admin_users,
    admin_operations,
    admin_audit,
    admin_organizations,
    copilot,
    intake,
    telehealth,
    voice,
    fhir,
    abdm,
    abdm_webhooks,
    observability,
    nurses,
    websockets,
)

from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.core.observability import (
    ObservabilityMiddleware,
    check_ai_mesh_health,
    check_database_health,
)
from app.core.security import RateLimitingMiddleware, SecurityHeadersMiddleware
from app.services.auth.audit import AuditLoggingMiddleware
from fastapi.middleware.cors import CORSMiddleware  # type: ignore
import app.services.scribe  # registers ScribeAgent on orchestrator
import app.services.prescriptions  # registers PrescriptionDraftAgent on orchestrator
import app.services.intake  # registers IntakeAgent on orchestrator

# ─── Sentry Error Tracking (optional) ────────────────────────────────────────
sentry_dsn = os.getenv("SENTRY_DSN") or settings.SENTRY_DSN
if sentry_dsn and not sentry_dsn.startswith("your_sentry"):
    try:
        import importlib
        sentry_sdk = importlib.import_module("sentry_sdk")

        def _scrub_sensitive_data(event, hint):
            # HIPAA & OWASP: Scrub sensitive authentication headers and credentials
            if "request" in event:
                req = event["request"]
                if "headers" in req:
                    for sensitive in ("authorization", "x-api-key", "cookie"):
                        if sensitive in req["headers"]:
                            req["headers"][sensitive] = "[FILTERED]"
                if "data" in req and isinstance(req["data"], dict):
                    for key in list(req["data"].keys()):
                        if any(k in key.lower() for k in ("password", "token", "secret", "cvv")):
                            req["data"][key] = "[FILTERED]"
            return event

        sentry_init_kwargs = {
            "dsn": sentry_dsn,
            "send_default_pii": True,
            "enable_logs": True,
            "traces_sample_rate": 1.0,
            "profile_session_sample_rate": 1.0,
            "profile_lifecycle": "trace",
            "environment": settings.APP_ENV,
            "release": "ai-hos@0.1.0",
            "before_send": _scrub_sensitive_data,
        }
        try:
            sentry_sdk.init(**sentry_init_kwargs)
        except TypeError:
            # Fallback for older sentry-sdk versions without new profiling options
            sentry_init_kwargs.pop("profile_session_sample_rate", None)
            sentry_init_kwargs.pop("profile_lifecycle", None)
            sentry_init_kwargs.pop("enable_logs", None)
            sentry_init_kwargs["profiles_sample_rate"] = 1.0
            sentry_sdk.init(**sentry_init_kwargs)
    except ImportError:
        import logging
        logging.getLogger(__name__).warning(
            "sentry-sdk not installed — Sentry disabled. Run: pip install sentry-sdk"
        )

app = FastAPI(
    title="AI-HOS Backend",
    description="AI Healthcare Operating System - Backend API",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)


# Register exception handlers for standard error envelope
register_exception_handlers(app)

# 1. Security Headers Middleware (OWASP defense-in-depth)
app.add_middleware(SecurityHeadersMiddleware)

# 2. CORS Middleware with restricted origins & exposed tracing headers
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:8000",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID", "X-Response-Time", "X-RateLimit-Remaining", "Retry-After"],
)

# 3. Rate Limiting Middleware (protects auth, AI, and endpoints against abuse)
app.add_middleware(RateLimitingMiddleware)

# 4. Observability Middleware for request correlation & latency tracking
app.add_middleware(ObservabilityMiddleware)

# 5. Audit logging middleware (separate compliance table)
app.add_middleware(AuditLoggingMiddleware)

app.include_router(auth.router, prefix="/api/v1")
app.include_router(consent.router, prefix="/api/v1")
app.include_router(patients.router, prefix="/api/v1")
app.include_router(doctors.router, prefix="/api/v1")
app.include_router(appointments.router, prefix="/api/v1")
app.include_router(medical_records.router, prefix="/api/v1")
app.include_router(prescriptions.router, prefix="/api/v1")
app.include_router(voice_notes.router, prefix="/api/v1")
app.include_router(approval.router, prefix="/api/v1")
app.include_router(admin_users.router, prefix="/api/v1")
app.include_router(admin_operations.router, prefix="/api/v1")
app.include_router(admin_audit.router, prefix="/api/v1")
app.include_router(admin_organizations.router, prefix="/api/v1")
app.include_router(copilot.router, prefix="/api/v1")
app.include_router(intake.router, prefix="/api/v1")
app.include_router(telehealth.router, prefix="/api/v1")
app.include_router(voice.router, prefix="/api/v1")
app.include_router(fhir.router, prefix="/api/v1")
app.include_router(abdm.router, prefix="/api/v1")
app.include_router(abdm_webhooks.router, prefix="/api/v1")
app.include_router(observability.router, prefix="/api/v1")
app.include_router(nurses.router, prefix="/api/v1")
app.include_router(websockets.router, prefix="/api/v1")


@app.on_event("startup")
async def startup_event():
    """Ensure database connection initialized and default test personas & organizations exist."""
    from app.database import AsyncSessionLocal, init_db
    from app.services.auth.service import UserCreate, create_user, get_user_by_email

    try:
        init_db()
        from app.database import engine  # type: ignore
        from sqlalchemy import text  # type: ignore
        from app.models import Base

        if engine:
            try:
                async with engine.begin() as conn:
                    await conn.run_sync(Base.metadata.create_all)
            except Exception as e:
                print(f"[AI-HOS Startup] Table creation check: {e}")

        # Ensure enum and new columns exist on startup
        if engine and "sqlite" not in str(engine.url):
            try:
                async with engine.connect() as conn:
                    await conn.execution_options(isolation_level="AUTOCOMMIT")
                    await conn.execute(text("ALTER TYPE userrole ADD VALUE IF NOT EXISTS 'super_admin';"))
                    await conn.execute(text("ALTER TYPE userrole ADD VALUE IF NOT EXISTS 'head_physician';"))
                    await conn.execute(text("ALTER TYPE userrole ADD VALUE IF NOT EXISTS 'head_nurse';"))
                    await conn.execute(text("ALTER TYPE appointmentstatus ADD VALUE IF NOT EXISTS 'in_progress';"))
            except Exception:
                pass

            async with engine.begin() as conn:
                alter_stmts = [
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
                for stmt in alter_stmts:
                    try:
                        await conn.execute(text(stmt))
                    except Exception:
                        pass

        # Ensure Global Super Administrator exists ONLY in development when explicitly enabled.
        # CRITICAL-04 Remediation: Never overwrite passwords of existing accounts on restart.
        if (
            AsyncSessionLocal
            and settings.APP_ENV == "development"
            and getattr(settings, "SEED_INITIAL_ADMIN", True)
        ):
            async with AsyncSessionLocal() as session:
                super_admin_email = getattr(settings, "SUPER_ADMIN_EMAIL", "superadmin@aihos.org")
                existing = await get_user_by_email(session, super_admin_email)
                if not existing:
                    initial_password = os.getenv("INITIAL_SUPER_ADMIN_PASSWORD", "adminpassword123")
                    await create_user(
                        session,
                        UserCreate(
                            email=super_admin_email,
                            password=initial_password,
                            full_name="AI-HOS Global Super Administrator",
                            phone="+919999000001",
                            role="super_admin",
                        ),
                        role="super_admin",
                    )
                    print(f"[AI-HOS Startup] Development Super Admin provisioned: {super_admin_email}")
                # If existing, preserve its existing password and configuration untouched.
    except Exception as e:
        print(f"[AI-HOS Startup] Notice during startup initialization: {e}")


@app.get("/health")
async def health_check():
    db_health = await check_database_health()
    ai_mesh = check_ai_mesh_health()
    overall_status = "healthy" if db_health.get("status") == "healthy" else "degraded"
    return {
        "status": overall_status,
        "service": "ai-hos-backend",
        "version": "0.1.0",
        "environment": settings.APP_ENV,
        "database": db_health,
        "ai_provider_mesh": ai_mesh,
    }


@app.get("/")
async def root():
    return {
        "message": "AI-HOS Backend API",
        "docs": "/docs",
        "health": "/health",
    }