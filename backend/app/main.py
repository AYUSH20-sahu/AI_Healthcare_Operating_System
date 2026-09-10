from fastapi import FastAPI

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
)
from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.services.auth.audit import AuditLoggingMiddleware

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

# Add audit logging middleware
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


@app.on_event("startup")
async def startup_event():
    """Ensure database connection initialized and default test personas exist."""
    from app.database import AsyncSessionLocal, init_db
    from app.models import UserRole
    from app.services.auth.service import UserCreate, create_user, get_user_by_email

    try:
        init_db()
        test_personas = [
            ("doctor@test.com", "doctorpassword123", "Dr. Rajesh Sharma", "doctor"),
            ("patient@test.com", "patientpassword123", "Amit Kumar", "patient"),
            ("admin@test.com", "adminpassword123", "Institutional Admin", "admin"),
        ]
        if AsyncSessionLocal:
            async with AsyncSessionLocal() as session:
                for email, password, name, role in test_personas:
                    existing = await get_user_by_email(session, email)
                    if not existing:
                        await create_user(
                            session,
                            UserCreate(
                                email=email,
                                password=password,
                                full_name=name,
                                role=role,
                            ),
                        )
    except Exception as e:
        print(f"[AI-HOS Startup] Notice: Test persona auto-seed check skipped or deferred: {e}")


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "ai-hos-backend",
        "version": "0.1.0",
        "environment": settings.APP_ENV,
    }


@app.get("/")
async def root():
    return {
        "message": "AI-HOS Backend API",
        "docs": "/docs",
        "health": "/health",
    }