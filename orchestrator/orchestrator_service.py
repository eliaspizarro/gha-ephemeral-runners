import logging
import os
from contextlib import asynccontextmanager
from typing import Dict, List, Optional

from config_validator import ConfigValidator
from error_handler import ConfigurationError, ErrorHandler
from fastapi import FastAPI, HTTPException
from lifecycle_manager import LifecycleManager
from pydantic import BaseModel
from utils import create_response, get_env_var, setup_logging_config

# Configuración de logging centralizada
setup_logging_config()
logger = logging.getLogger(__name__)


# Modelos de datos
class RunnerRequest(BaseModel):
    scope: str
    scope_name: str
    runner_name: Optional[str] = None
    runner_group: Optional[str] = None
    labels: Optional[List[str]] = None
    count: int = 1


class RunnerResponse(BaseModel):
    runner_id: str
    status: str
    message: str


class RunnerStatus(BaseModel):
    runner_id: str
    status: str
    container_id: Optional[str] = None
    image: Optional[str] = None
    created: Optional[str] = None
    labels: Optional[Dict] = None


class ConfigurationInfo(BaseModel):
    runner_image: str
    total_variables: int
    variable_names: List[str]
    has_configuration: bool
    available_placeholders: int
    orchestrator_id: str


class ValidationResult(BaseModel):
    valid: bool
    errors: List[str]
    warnings: List[str]
    recommendations: List[str]


# Lifecycle events
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Iniciando servicio de orquestador")
    logger.info("Servicio iniciado exitosamente")

    yield

    logger.info("Deteniendo servicio de orquestador")
    lifecycle_manager.stop_monitoring()
    logger.info("Servicio detenido")


# Inicialización del servicio
app = FastAPI(
    title="GitHub Actions Ephemeral Runners Orchestrator",
    description="Servicio para gestionar runners efímeros de GitHub Actions",
    version="1.0.0",
    lifespan=lifespan,
)

# Variables de entorno - usando utilitarios
try:
    GITHUB_RUNNER_TOKEN = get_env_var("GITHUB_RUNNER_TOKEN", required=True)
    RUNNER_IMAGE = get_env_var("RUNNER_IMAGE", required=True)
    AUTO_CREATE_RUNNERS = os.getenv("AUTO_CREATE_RUNNERS", "false").lower() == "true"
    RUNNER_CHECK_INTERVAL = int(os.getenv("RUNNER_CHECK_INTERVAL", "300"))

    # Inicializar Lifecycle Manager
    lifecycle_manager = LifecycleManager(GITHUB_RUNNER_TOKEN, RUNNER_IMAGE)

    # Validar configuración
    config_validator = ConfigValidator()
    validation_result = config_validator.validate_environment()

    if not validation_result["valid"]:
        for error in validation_result["errors"]:
            logger.error(f"Error de configuración: {error}")
        raise ConfigurationError("Configuración inválida")

    for warning in validation_result["warnings"]:
        logger.warning(f"Advertencia: {warning}")

    logger.info("Configuración validada exitosamente")

    # Iniciar monitoreo automático
    if AUTO_CREATE_RUNNERS:
        logger.info(f"Automatización activada - Verificando cada {RUNNER_CHECK_INTERVAL} segundos")
        lifecycle_manager.start_monitoring(RUNNER_CHECK_INTERVAL)
    else:
        logger.info("Automatización desactivada")

except Exception as e:
    logger.error(f"Error inicializando servicio: {e}")
    raise


# Endpoints del servicio
@app.post("/runners/create", response_model=List[RunnerResponse])
async def create_runners(request: RunnerRequest):
    try:
        runners = []
        for i in range(request.count):
            runner_name = request.runner_name
            if request.count > 1:
                runner_name = f"{request.runner_name}-{i+1}" if request.runner_name else None

            runner_id = lifecycle_manager.create_runner(
                scope=request.scope,
                scope_name=request.scope_name,
                runner_name=runner_name,
                runner_group=request.runner_group,
                labels=request.labels,
            )

            runners.append(
                RunnerResponse(
                    runner_id=runner_id, status="created", message="Runner creado exitosamente"
                )
            )

        logger.info(f"Creados {len(runners)} runners para {request.scope}/{request.scope_name}")
        return runners

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise ErrorHandler.handle_error(e, "creando runners", logger)


@app.get("/runners/{runner_id}/status", response_model=RunnerStatus)
async def get_runner_status(runner_id: str):
    try:
        status = lifecycle_manager.get_runner_status(runner_id)
        return RunnerStatus(**status)
    except Exception as e:
        raise ErrorHandler.handle_error(e, "obteniendo estado del runner", logger)


@app.delete("/runners/{runner_id}")
async def destroy_runner(runner_id: str):
    try:
        success = lifecycle_manager.destroy_runner(runner_id)

        if not success:
            raise HTTPException(
                status_code=404, detail="Runner no encontrado o no se pudo destruir"
            )

        return create_response(True, f"Runner {runner_id} destruido exitosamente")

    except HTTPException:
        raise
    except Exception as e:
        raise ErrorHandler.handle_error(e, "destruyendo runner", logger)


@app.get("/runners", response_model=List[RunnerStatus])
async def list_runners():
    try:
        runners = lifecycle_manager.list_active_runners()
        return [RunnerStatus(**runner) for runner in runners]
    except Exception as e:
        raise ErrorHandler.handle_error(e, "listando runners", logger)


@app.post("/runners/cleanup")
async def cleanup_runners():
    try:
        cleaned = lifecycle_manager.cleanup_inactive_runners()
        return create_response(True, f"Limpiados {cleaned} runners", {"cleaned_count": cleaned})
    except Exception as e:
        raise ErrorHandler.handle_error(e, "limpieza de runners", logger)


@app.get("/config/info", response_model=ConfigurationInfo)
async def get_configuration_info():
    try:
        env_manager = lifecycle_manager.container_manager.environment_manager
        config_summary = env_manager.get_configuration_summary()
        return ConfigurationInfo(**config_summary)
    except Exception as e:
        raise ErrorHandler.handle_error(e, "obteniendo información de configuración", logger)


@app.get("/config/validate", response_model=ValidationResult)
async def validate_configuration():
    try:
        validation_result = config_validator.get_validation_summary()
        recommendations = config_validator.get_configuration_recommendations()

        return ValidationResult(
            valid=validation_result["overall_valid"],
            errors=validation_result["validation_details"]["errors"],
            warnings=validation_result["validation_details"]["warnings"],
            recommendations=recommendations,
        )
    except Exception as e:
        raise ErrorHandler.handle_error(e, "validando configuración", logger)


@app.get("/config/placeholders")
async def get_available_placeholders():
    try:
        env_manager = lifecycle_manager.container_manager.environment_manager
        placeholders = env_manager.get_placeholder_info()

        return create_response(
            True,
            "Placeholders obtenidos",
            {"total_placeholders": len(placeholders), "placeholders": placeholders},
        )
    except Exception as e:
        raise ErrorHandler.handle_error(e, "obteniendo placeholders", logger)


@app.get("/health")
async def health_check():
    return create_response(
        True,
        "Servicio saludable",
        {
            "service": "orchestrator",
            "active_runners": len(lifecycle_manager.active_runners),
            "monitoring": lifecycle_manager.monitoring,
        },
    )


@app.get("/runners/{runner_name}/logs")
async def get_runner_logs(runner_name: str):
    """
    Obtiene logs de un runner específico.
    """
    try:
        # Buscar contenedor por nombre
        container = lifecycle_manager.container_manager.get_container_by_name(runner_name)
        if not container:
            raise HTTPException(status_code=404, detail="Runner no encontrado")

        # Obtener logs
        logs = lifecycle_manager.container_manager.get_container_logs(container, tail=200)

        return create_response(True, "Logs obtenidos", {"logs": logs})

    except Exception as e:
        raise ErrorHandler.handle_error(e, "obteniendo logs del runner", logger)


@app.get("/healthz")
async def docker_health_check():
    try:
        if not hasattr(lifecycle_manager, "active_runners"):
            raise HTTPException(status_code=503, detail="Lifecycle manager no inicializado")

        active_count = len(lifecycle_manager.active_runners)
        if active_count > 100:
            raise HTTPException(
                status_code=503, detail=f"Demasiados runners activos: {active_count}"
            )

        return create_response(
            True,
            "Servicio saludable",
            {
                "service": "orchestrator",
                "active_runners": active_count,
                "monitoring": lifecycle_manager.monitoring,
            },
        )
    except HTTPException:
        raise
    except Exception as e:
        raise ErrorHandler.handle_error(e, "health check", logger)


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("ORCHESTRATOR_PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
