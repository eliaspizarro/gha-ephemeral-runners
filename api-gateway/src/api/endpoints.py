"""
API Gateway - FastAPI Endpoints
Contains all HTTP endpoints for the API Gateway service.
"""

import logging
from typing import List

from fastapi import APIRouter, HTTPException

from src.api.models import APIResponse, RunnerRequest
from src.config.settings import ORCHESTRATOR_URL, DEFAULT_HEADERS
from src.utils.helpers import format_log
from src.services.request_router import RequestRouter

logger = logging.getLogger(__name__)

# Initialize router
router = APIRouter()
request_router = RequestRouter(ORCHESTRATOR_URL, 30.0, DEFAULT_HEADERS)


@router.post("/runners", response_model=APIResponse)
async def create_runners(request: RunnerRequest):
    """Create new ephemeral runners."""
    try:
        # Validate request
        request_router.validate_runner_request(request.dict())

        # Create runners
        runners = await request_router.create_runners(request.dict())

        return APIResponse(data=runners, message=f"Creados {len(runners)} runners exitosamente")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(format_log('ERROR', 'Error creando runners', str(e)))
        raise HTTPException(status_code=500, detail="Error interno del servidor")


@router.get("/runners/{runner_id}", response_model=APIResponse)
async def get_runner_status(runner_id: str):
    """Get status of a specific runner."""
    try:
        status = await request_router.get_runner_status(runner_id)

        return APIResponse(data=status, message="Estado obtenido exitosamente")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error obteniendo estado del runner {runner_id}: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")


@router.delete("/runners/{runner_id}", response_model=APIResponse)
async def destroy_runner(runner_id: str):
    """Destroy a specific runner."""
    try:
        result = await request_router.destroy_runner(runner_id)

        return APIResponse(data=result, message=f"Runner {runner_id} destruido exitosamente")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error destruyendo runner {runner_id}: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")


@router.get("/runners", response_model=APIResponse)
async def list_runners():
    """List all active runners."""
    try:
        runners = await request_router.list_runners()

        return APIResponse(data=runners, message=f"Listados {len(runners)} runners activos")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listando runners: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")


@router.post("/runners/cleanup", response_model=APIResponse)
async def cleanup_runners():
    """Clean up inactive runners."""
    try:
        result = await request_router.cleanup_runners()

        return APIResponse(data=result, message="Limpieza completada exitosamente")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error en limpieza: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")


@router.get("/health", response_model=APIResponse)
async def full_health_check():
    """Full health check including orchestrator."""
    try:
        # Check orchestrator
        orchestrator_health = await request_router.get_health()
        
        return APIResponse(
            data={
                "status": "healthy",
                "service": "api-gateway",
                "version": "1.0.0",
                "orchestrator": orchestrator_health.get("status", "unknown")
            },
            message="Gateway y orchestrator funcionando correctamente",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(format_log('ERROR', 'Error en health check completo', str(e)))
        return APIResponse(
            data={
                "status": "degraded",
                "service": "api-gateway",
                "version": "1.0.0",
                "orchestrator": "unreachable"
            },
            message="Gateway con problemas en orchestrator",
        )
