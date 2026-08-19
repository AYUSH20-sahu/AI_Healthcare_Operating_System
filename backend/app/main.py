from fastapi import FastAPI

from app.core.config import settings
from app.api import auth, consent
from app.services.auth.audit import AuditLoggingMiddleware

app = FastAPI(
    title="AI-HOS Backend",
    description="AI Healthcare Operating System - Backend API",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# Add audit logging middleware
app.add_middleware(AuditLoggingMiddleware)

app.include_router(auth.router, prefix="/api/v1")
app.include_router(consent.router, prefix="/api/v1")


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