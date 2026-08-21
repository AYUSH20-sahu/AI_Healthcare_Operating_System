"""Standard error envelope and exception handlers for AI-HOS API."""

from typing import Any, Dict, Optional
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from starlette.exceptions import HTTPException as StarletteHTTPException


class ErrorDetail(BaseModel):
    """Error detail model."""
    code: str = Field(..., description="Error code")
    message: str = Field(..., description="Human-readable error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")


class ErrorResponse(BaseModel):
    """Standard error response envelope."""
    error: ErrorDetail


def create_error_response(
    code: str,
    message: str,
    details: Optional[Dict[str, Any]] = None,
    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
) -> JSONResponse:
    """Create a standardized error response."""
    return JSONResponse(
        status_code=status_code,
        content=ErrorResponse(
            error=ErrorDetail(code=code, message=message, details=details)
        ).model_dump(),
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """Handle HTTP exceptions with standard error envelope."""
    # Map common status codes to error codes
    error_codes = {
        status.HTTP_400_BAD_REQUEST: "BAD_REQUEST",
        status.HTTP_401_UNAUTHORIZED: "UNAUTHORIZED",
        status.HTTP_403_FORBIDDEN: "FORBIDDEN",
        status.HTTP_404_NOT_FOUND: "NOT_FOUND",
        status.HTTP_409_CONFLICT: "CONFLICT",
        status.HTTP_422_UNPROCESSABLE_ENTITY: "VALIDATION_ERROR",
        status.HTTP_429_TOO_MANY_REQUESTS: "RATE_LIMITED",
        status.HTTP_500_INTERNAL_SERVER_ERROR: "INTERNAL_ERROR",
        status.HTTP_503_SERVICE_UNAVAILABLE: "SERVICE_UNAVAILABLE",
    }
    
    code = error_codes.get(exc.status_code, "HTTP_ERROR")
    
    # Extract details if present
    details = None
    if isinstance(exc.detail, dict):
        details = exc.detail
    elif isinstance(exc.detail, str) and exc.detail != exc.detail:
        pass
    
    return create_error_response(
        code=code,
        message=exc.detail if isinstance(exc.detail, str) else "An error occurred",
        details=details,
        status_code=exc.status_code,
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Handle validation exceptions with standard error envelope."""
    errors = []
    for error in exc.errors():
        errors.append({
            "field": ".".join(str(loc) for loc in error["loc"]),
            "message": error["msg"],
            "type": error["type"],
        })
    
    return create_error_response(
        code="VALIDATION_ERROR",
        message="Request validation failed",
        details={"errors": errors},
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unexpected exceptions with standard error envelope."""
    # Log the exception here if needed
    return create_error_response(
        code="INTERNAL_ERROR",
        message="An unexpected error occurred",
        details={"type": type(exc).__name__} if settings.DEBUG else None,
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Register all exception handlers with the FastAPI app."""
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)
    
    # Add error response models to OpenAPI schema
    original_openapi = app.openapi
    
    def custom_openapi():
        if app.openapi_schema:
            return app.openapi_schema
        openapi_schema = original_openapi()
        
        # Ensure components/schemas exists
        if "components" not in openapi_schema:
            openapi_schema["components"] = {}
        if "schemas" not in openapi_schema["components"]:
            openapi_schema["components"]["schemas"] = {}
        
        # Add ErrorDetail and ErrorResponse schemas manually
        openapi_schema["components"]["schemas"]["ErrorDetail"] = {
            "title": "ErrorDetail",
            "type": "object",
            "properties": {
                "code": {"title": "Code", "type": "string"},
                "message": {"title": "Message", "type": "string"},
                "details": {"title": "Details", "type": "object", "nullable": True}
            },
            "required": ["code", "message"]
        }
        
        openapi_schema["components"]["schemas"]["ErrorResponse"] = {
            "title": "ErrorResponse",
            "type": "object",
            "properties": {
                "error": {"$ref": "#/components/schemas/ErrorDetail"}
            },
            "required": ["error"]
        }
        
        app.openapi_schema = openapi_schema
        return app.openapi_schema
    
    app.openapi = custom_openapi


# Import settings for DEBUG flag
from app.core.config import settings