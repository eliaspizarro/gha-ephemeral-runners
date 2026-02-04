"""
API Gateway - Core Service Configuration
Contains FastAPI app configuration, middleware setup, and service initialization.
"""

import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, Dict

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from src.api.endpoints import router
from src.config.settings import (
    APP_TITLE, APP_DESCRIPTION, APP_VERSION, API_PREFIX,
    CORS_ORIGINS, CORS_ALLOW_CREDENTIALS, CORS_ALLOW_METHODS, CORS_ALLOW_HEADERS,
    ORCHESTRATOR_URL, LOG_LEVEL
)
from src.middleware.error_handlers import setup_exception_handlers
from src.utils.helpers import setup_logging_config, log_request_info, format_log
from ..version import __version__

# Configure logging
setup_logging_config()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle events."""
    # Startup
    logger.info(format_log('START', 'API Gateway Service'))
    logger.info(format_log('CONFIG', 'Orquestador configurado', ORCHESTRATOR_URL))
    yield
    # Shutdown
    logger.info(format_log('INFO', 'Deteniendo API Gateway Service'))


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title=APP_TITLE,
        description=APP_DESCRIPTION,
        version=APP_VERSION,
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=CORS_ORIGINS,
        allow_credentials=CORS_ALLOW_CREDENTIALS,
        allow_methods=CORS_ALLOW_METHODS,
        allow_headers=CORS_ALLOW_HEADERS,
    )

    # Add logging middleware
    @app.middleware("http")
    async def logging_middleware(request: Request, call_next):
        """Middleware para logging de solicitudes externas."""
        start_time = datetime.utcnow()

        # Get client information
        client_info = log_request_info(request)

        # No loggear health checks internos (solo para verbose/debug)
        # Detectar health checks por path y IP local
        is_health_check = (
            request.url.path in ["/health", "/healthz"] and 
            client_info['ip'] in ["127.0.0.1", "testclient", "localhost"]
        )

        # Log request solo si no es health check interno
        if not is_health_check:
            logger.info(
                format_log('REQUEST', 'Solicitud recibida', f"{client_info['method']} {client_info['url']} - IP: {client_info['ip']}")
            )

        # Process request
        response = await call_next(request)

        # Calculate duration
        process_time = (datetime.utcnow() - start_time).total_seconds()

        # Log response solo si no es health check interno
        if not is_health_check:
            logger.info(format_log('RESPONSE', 'Respuesta enviada', f"Status: {response.status_code} - Duración: {process_time:.3f}s"))

        return response

    # Setup exception handlers
    setup_exception_handlers(app)

    # Include API endpoints
    app.include_router(router, prefix=API_PREFIX)
    
    # Add health check endpoints at root level (for Docker health checks)
    @app.get("/health", tags=["Health"])
    async def root_health_check():
        """Basic health check endpoint at root level."""
        try:
            from src.services.request_router import RequestRouter
            from src.config.settings import ORCHESTRATOR_URL, DEFAULT_HEADERS
            from src.api.models import APIResponse
            
            request_router = RequestRouter(ORCHESTRATOR_URL, 30.0, DEFAULT_HEADERS)
            orchestrator_health = await request_router.get_health()
            
            return APIResponse(
                data={
                    "status": "healthy",
                    "service": "api-gateway",
                    "version": __version__,
                    "orchestrator": orchestrator_health.get("status", "unknown")
                },
                message="Gateway funcionando correctamente",
            )
        except Exception as e:
            logger.error(format_log('ERROR', 'Error verificando salud del orchestrator', str(e)))
            from src.api.models import APIResponse
            return APIResponse(
                data={
                    "status": "degraded",
                    "service": "api-gateway",
                    "version": __version__,
                    "orchestrator": "unreachable"
                },
                message="Gateway funcionando pero con problemas en orchestrator",
            )

    @app.get("/healthz", tags=["Health"])
    async def root_docker_health_check():
        """Docker health check endpoint at root level."""
        try:
            from src.api.models import APIResponse
            return APIResponse(
                data={"status": "healthy", "service": "api-gateway", "version": __version__},
                message="Gateway saludable",
            )
        except Exception as e:
            logger.error(f"Health check falló: {e}")
            from fastapi import HTTPException
            raise HTTPException(status_code=503, detail="Servicio no saludable")

    return app
