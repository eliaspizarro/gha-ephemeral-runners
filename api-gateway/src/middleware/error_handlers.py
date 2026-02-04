"""
API Gateway - Error Handlers Middleware
Contains centralized exception handlers for standardized error responses.
"""

import logging
from typing import Any, Dict

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse

from src.api.models import ErrorResponse

logger = logging.getLogger(__name__)


def create_error_response(
    status_code: int, 
    message: str, 
    error_data: Dict[str, Any] = None
) -> JSONResponse:
    """Create a standardized error response."""
    error_response = ErrorResponse(
        message=message,
        data=error_data or {"error_code": status_code}
    )
    return JSONResponse(status_code=status_code, content=error_response.dict())


def handle_http_exception(request: Request, exc: HTTPException) -> JSONResponse:
    """Handle HTTP exceptions with standardized format."""
    return create_error_response(
        status_code=exc.status_code,
        message=exc.detail,
        error_data={"error_code": exc.status_code}
    )


def handle_general_exception(request: Request, exc: Exception) -> JSONResponse:
    """Handle general exceptions with standardized format."""
    logger.error(f"Excepción no manejada: {exc}")
    
    return create_error_response(
        status_code=500,
        message="Error interno del servidor",
        error_data={"error_type": type(exc).__name__}
    )


def setup_exception_handlers(app) -> None:
    """Setup exception handlers for the FastAPI application."""
    app.add_exception_handler(HTTPException, handle_http_exception)
    app.add_exception_handler(Exception, handle_general_exception)
