"""
Aplicación principal FastAPI para OrchestratorV2.

Rol: Punto de entrada principal y configuración de la aplicación.
Inicializa dependencias, configura logging y expone endpoints.
Implementa el lifecycle de la aplicación y dependency injection.
"""

import logging
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from ..shared.logging_utils import setup_logging_config, get_logger
from ..shared.infrastructure_exceptions import ConfigurationError, DockerError
from ..infrastructure.config import get_config
from ..infrastructure.container_manager import ContainerManager
from ..infrastructure.github_client import GitHubClient
from ..infrastructure.environment_setup import EnvironmentSetup
from ..domain.orchestration_service import OrchestrationService
from ..domain.github_service import GitHubService
from .runner_routes import router as runner_router
from .health_routes import router as health_router
from .request_models import RunnerRequest
from .response_models import ErrorResponse

# Configuración de logging
setup_logging_config()
logger = get_logger(__name__)

# Dependencias para inyección
def get_orchestration_service() -> OrchestrationService:
    """Obtiene el servicio de orquestación desde el estado de la aplicación."""
    return app.state.orchestration_service

def get_container_manager() -> ContainerManager:
    """Obtiene el gestor de contenedores desde el estado de la aplicación."""
    return app.state.container_manager

def get_config_dependency() -> get_config:
    """Obtiene la configuración desde el estado de la aplicación."""
    return app.state.config_service

# Variables globales para la aplicación
orchestration_service: Optional[OrchestrationService] = None
container_manager: Optional[ContainerManager] = None
github_client: Optional[GitHubClient] = None
github_service: Optional[GitHubService] = None
environment_setup: Optional[EnvironmentSetup] = None


class AppInfo(BaseModel):
    """"Información básica de la aplicación."""
    
    name: str = "OrchestratorV2"
    version: str = "0.1.0"
    description: str = "GitHub Actions Ephemeral Runners Orchestrator"
    environment: str = os.getenv("ENVIRONMENT", "development")
    debug: bool = os.getenv("DEBUG", "false").lower() == "true"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifecycle de la aplicación FastAPI.
    
    Args:
        app: Instancia de FastAPI
    """
    global orchestration_service
    
    logger.info("Iniciando servicio de orquestador v2")
    
    try:
        # Inicializar dependencias principales
        config = get_config()
        
        # Crear componentes de infraestructura
        container_manager = ContainerManager(config.docker.runner_image)
        github_client = GitHubClient(
            token=config.github.runner_token,
            api_base=config.github.api_base,
            timeout=config.github.timeout
        )
        environment_setup = EnvironmentSetup(config.docker.runner_image)
        
        # Crear servicios de dominio
        github_service = GitHubService(github_client)
        orchestration_service = OrchestrationService(
            container_manager=container_manager,
            token_provider=github_client,
            github_service=github_service
        )
        
        # Configurar servicio de orquestación
        orchestration_service.poll_interval = config.orchestrator.poll_interval
        orchestration_service.cleanup_interval = config.orchestrator.cleanup_interval
        orchestration_service.max_runners_per_repo = config.orchestrator.max_runners_per_repo
        orchestration_service.auto_create_runners = config.orchestrator.auto_create_runners
        
        # Hacer disponibles globalmente
        globals().update({
            'orchestration_service': orchestration_service,
            'container_manager': container_manager,
            'github_client': github_client,
            'github_service': github_service,
            'environment_setup': environment_setup
        })
        
        # 5. Verificar conexión con Docker
        try:
            container_manager.test_connection()
            logger.info("✅ Conexión Docker verificada")
        except DockerError as e:
            logger.error(f"❌ Error Docker: {e}")
            raise ConfigurationError(f"No se puede conectar a Docker: {e}")
        
        logger.info("Servicio iniciado exitosamente")
        
        yield
        
        logger.info("Deteniendo servicio de orquestador v2")
        
        # Detener monitoreo si está activo
        if orchestration_service.monitoring_active:
            from .use_cases.monitor_workflows import MonitorWorkflows
            monitor_use_case = MonitorWorkflows(orchestration_service)
            monitor_use_case.stop_monitoring()
        
        logger.info("Servicio detenido")
        
    except Exception as e:
        logger.error(f"Error en inicialización: {e}")
        raise ConfigurationError(f"Error iniciando aplicación: {e}")


def create_app() -> FastAPI:
    """
    Crea y configura la aplicación FastAPI.
    
    Returns:
        Instancia de FastAPI configurada
    """
    try:
        # Crear aplicación FastAPI
        app = FastAPI(
            title="GitHub Actions Ephemeral Runners Orchestrator V2",
            description="Servicio para gestionar runners efímeros de GitHub Actions",
            version="0.1.0",
            lifespan=lifespan,
            debug=os.getenv("DEBUG", "false").lower() == "true"
        )
        
        # Configurar middleware
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"]
        )
        
        # Incluir rutas
        app.include_router(runner_router, prefix="/api")
        app.include_router(health_router, prefix="/api")
        
        # Endpoint raíz
        @app.get("/", response_model=AppInfo)
        async def root():
            return AppInfo()
        
        # Manejo de errores globales
        @app.exception_handler(Exception)
        async def global_exception_handler(request, exc):
            logger.error(f"Error global no manejado: {type(exc).__name__}: {str(exc)}")
            return JSONResponse(
                status_code=500,
                content={
                    "success": False,
                    "error": "Error interno del servidor",
                    "message": "Ha ocurrido un error inesperado",
                    "details": str(exc)
                }
            )
        
        return app
        
    except Exception as e:
        logger.error(f"Error creando aplicación: {e}")
        raise ConfigurationError(f"Error creando aplicación: {e}")

# Crear instancia global de la aplicación
app = create_app()

if __name__ == "__main__":
    import uvicorn
    
    # Obtener configuración
    config = get_config()
    
    # Iniciar servidor
    uvicorn.run(
        app,
        host=config.api.host,
        port=config.api.port,
        log_level=config.api.log_level.lower(),
        reload=config.debug
    )
