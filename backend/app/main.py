from fastapi import FastAPI

from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.api import auth, consent, patients, doctors, appointments, medical_records, prescriptions, voice_notes
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