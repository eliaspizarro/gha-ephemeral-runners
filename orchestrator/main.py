"""
API FastAPI del Orchestrator - Punto de entrada y routing.
Contiene solo la definición de endpoints y delega lógica a src.core.orchestrator.
"""

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException

from src.api.models import *
from src.core.orchestrator import OrchestratorService
from src.utils.helpers import ErrorHandler, setup_logging_config

# Configurar logging ANTES de inicializar el servicio
setup_logging_config()

# Configuración de logging
logger = logging.getLogger(__name__)

# Inicialización del servicio de negocio
logger.info("🚀 INICIANDO ORCHESTRATOR SERVICE...")
orchestrator_service = OrchestratorService()
logger.info("✅ ORCHESTRATOR SERVICE INICIALIZADO")


# Lifecycle events
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Maneja el ciclo de vida de la aplicación FastAPI."""
    logger.info("Iniciando servicio de orquestador")
    logger.info("Servicio iniciado exitosamente")
    
    yield
    
    logger.info("Deteniendo servicio de orquestador")
    orchestrator_service.stop_monitoring()
    logger.info("Servicio detenido")


# Inicialización del servicio FastAPI
app = FastAPI(
    title="GitHub Actions Ephemeral Runners Orchestrator",
    description="Servicio para gestionar runners efímeros de GitHub Actions",
    version="1.0.0",
    lifespan=lifespan,
)


# ===== ENDPOINTS DE RUNNERS =====

@app.post("/runners/create", response_model=List[RunnerResponse])
async def create_runners(request: RunnerRequest):
    """Crea nuevos runners efímeros."""
    try:
        return await orchestrator_service.create_runners(request)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise ErrorHandler.handle_error(e, "creando runners", logger)


@app.get("/runners/{runner_id}/status", response_model=RunnerStatus)
async def get_runner_status(runner_id: str):
    """Obtiene el estado de un runner específico."""
    try:
        return await orchestrator_service.get_runner_status(runner_id)
    except Exception as e:
        raise ErrorHandler.handle_error(e, "obteniendo estado del runner", logger)


@app.delete("/runners/{runner_id}")
async def destroy_runner(runner_id: str):
    """Destruye un runner específico."""
    try:
        return await orchestrator_service.destroy_runner(runner_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise ErrorHandler.handle_error(e, "destruyendo runner", logger)


@app.get("/runners", response_model=List[RunnerStatus])
async def list_runners():
    """Lista todos los runners activos."""
    try:
        return await orchestrator_service.list_runners()
    except Exception as e:
        raise ErrorHandler.handle_error(e, "listando runners", logger)


@app.post("/runners/cleanup")
async def cleanup_runners():
    """Limpia runners inactivos."""
    try:
        return await orchestrator_service.cleanup_runners()
    except Exception as e:
        raise ErrorHandler.handle_error(e, "limpieza de runners", logger)


@app.get("/runners/{runner_name}/logs")
async def get_runner_logs(runner_name: str):
    """Obtiene logs de un runner específico."""
    try:
        return await orchestrator_service.get_runner_logs(runner_name)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise ErrorHandler.handle_error(e, "obteniendo logs del runner", logger)


# ===== ENDPOINTS DE CONFIGURACIÓN =====

@app.get("/config/info", response_model=ConfigurationInfo)
async def get_configuration_info():
    """Obtiene información de configuración."""
    try:
        return await orchestrator_service.get_configuration_info()
    except Exception as e:
        raise ErrorHandler.handle_error(e, "obteniendo información de configuración", logger)


@app.get("/config/validate", response_model=ValidationResult)
async def validate_configuration():
    """Valida la configuración actual."""
    try:
        return await orchestrator_service.validate_configuration()
    except Exception as e:
        raise ErrorHandler.handle_error(e, "validando configuración", logger)


@app.get("/config/placeholders")
async def get_available_placeholders():
    """Obtiene placeholders disponibles."""
    try:
        return await orchestrator_service.get_available_placeholders()
    except Exception as e:
        raise ErrorHandler.handle_error(e, "obteniendo placeholders", logger)


# ===== HEALTH CHECKS =====

@app.get("/health")
async def health_check():
    """Health check básico del servicio."""
    try:
        return await orchestrator_service.health_check()
    except Exception as e:
        raise ErrorHandler.handle_error(e, "health check", logger)


@app.get("/healthz")
async def docker_health_check():
    """Health check para Docker Engine."""
    try:
        return await orchestrator_service.docker_health_check()
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise ErrorHandler.handle_error(e, "health check", logger)


# ===== EJECUCIÓN =====

if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("ORCHESTRATOR_PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
