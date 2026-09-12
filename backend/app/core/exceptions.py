"""Standard error envelope and exception handlers for AI-HOS API."""

from datetime import datetime, timezone
from typing import Any, Optional

from app.core.config import settings
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from starlette.exceptions import HTTPException as StarletteHTTPException


class ErrorDetail(BaseModel):
    """Error detail model."""
    code: str = Field(..., description="Error code")
    message: str = Field(..., description="Human-readable error message")
    details: dict[str, Any] | None = Field(None, description="Additional error details")
    request_id: Optional[str] = Field(None, description="Request correlation identifier")
    timestamp: Optional[str] = Field(None, description="ISO timestamp of error occurrence")


class ErrorResponse(BaseModel):
    """Standard error response envelope."""
    error: ErrorDetail


def create_error_response(
    code: str,
    message: str,
    details: dict[str, Any] | None = None,
    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
    request: Optional[Request] = None,
) -> JSONResponse:
    """Create a standardized error response with request correlation."""
    from app.core.observability import current_request_id

    req_id = None
    if request and hasattr(request, "state") and hasattr(request.state, "request_id"):
        req_id = request.state.request_id
    if not req_id:
        req_id = current_request_id.get("system")

    ts = datetime.now(timezone.utc).isoformat()

    headers = {"X-Request-ID": req_id} if req_id else {}
    return JSONResponse(
        status_code=status_code,
        content=ErrorResponse(
            error=ErrorDetail(
                code=code,
                message=message,
                details=details,
                request_id=req_id,
                timestamp=ts,
            )
        ).model_dump(),
        headers=headers,
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
    
    return create_error_response(
        code=code,
        message=exc.detail if isinstance(exc.detail, str) else "An error occurred",
        details=details,
        status_code=exc.status_code,
        request=request,
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
        request=request,
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unexpected exceptions with standard error envelope and no raw stack trace leakage."""
    return create_error_response(
        code="INTERNAL_ERROR",
        message="An unexpected server error occurred. Please contact support with the request_id.",
        details={"type": type(exc).__name__} if settings.DEBUG else None,
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        request=request,
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
                "details": {"title": "Details", "type": "object", "nullable": True},
                "request_id": {"title": "RequestId", "type": "string", "nullable": True},
                "timestamp": {"title": "Timestamp", "type": "string", "nullable": True},
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