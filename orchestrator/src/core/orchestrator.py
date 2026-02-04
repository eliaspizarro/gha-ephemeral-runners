"""
Lógica principal del servicio Orchestrator.
Contiene toda la lógica de negocio separada de la API FastAPI.
"""

import logging
import os
from typing import Dict, List, Optional

from src.api.models import (
    ConfigurationInfo, 
    RunnerRequest, 
    RunnerResponse, 
    RunnerStatus, 
    ValidationResult
)
from src.core.container import ContainerManager
from src.core.lifecycle import LifecycleManager
from src.services.config import ConfigValidator
from src.services.environment import EnvironmentManager
from src.utils.helpers import (
    ConfigurationError, 
    ErrorHandler, 
    PlaceholderResolver,
    create_response, 
    get_env_var, 
    setup_logging_config
)

# Configuración de logging centralizada
setup_logging_config()
logger = logging.getLogger(__name__)


class OrchestratorService:
    """Servicio principal del orchestrator con toda la lógica de negocio."""
    
    def __init__(self):
        """Inicializa el servicio con configuración y componentes."""
        self._initialize_environment()
        self._initialize_components()
        self._validate_configuration()
        self._setup_monitoring()
    
    def _initialize_environment(self):
        """Inicializa variables de entorno."""
        try:
            self.github_runner_token = get_env_var("GITHUB_RUNNER_TOKEN", required=True)
            self.runner_image = get_env_var("RUNNER_IMAGE", required=True)
            self.auto_create_runners = os.getenv("AUTO_CREATE_RUNNERS", "false").lower() == "true"
            self.runner_check_interval = int(os.getenv("RUNNER_CHECK_INTERVAL", "300"))
            
            logger.info("Variables de entorno inicializadas correctamente")
            
        except Exception as e:
            logger.error(f"Error inicializando variables de entorno: {e}")
            raise
    
    def _initialize_components(self):
        """Inicializa componentes principales."""
        try:
            # Inicializar Lifecycle Manager
            self.lifecycle_manager = LifecycleManager(self.github_runner_token, self.runner_image)
            
            # Inicializar Config Validator
            self.config_validator = ConfigValidator()
            
            # Inicializar Placeholder Resolver
            self.placeholder_resolver = PlaceholderResolver()
            
            logger.info("Componentes inicializados correctamente")
            
        except Exception as e:
            logger.error(f"Error inicializando componentes: {e}")
            raise
    
    def _validate_configuration(self):
        """Valida la configuración del servicio."""
        try:
            validation_result = self.config_validator.validate_environment()
            
            if not validation_result["valid"]:
                for error in validation_result["errors"]:
                    logger.error(f"Error de configuración: {error}")
                raise ConfigurationError("Configuración inválida")
            
            for warning in validation_result["warnings"]:
                logger.warning(f"Advertencia: {warning}")
            
            logger.info("Configuración validada exitosamente")
            
        except Exception as e:
            logger.error(f"Error validando configuración: {e}")
            raise
    
    def _setup_monitoring(self):
        """Configura el monitoreo automático si está activado."""
        try:
            if self.auto_create_runners:
                logger.info(f"Automatización activada - Verificando cada {self.runner_check_interval} segundos")
                self.lifecycle_manager.start_monitoring(self.runner_check_interval)
            else:
                logger.info("Automatización desactivada")
                
        except Exception as e:
            logger.error(f"Error configurando monitoreo: {e}")
            raise
    
    # ===== MÉTODOS DE NEGOCIO PARA RUNNERS =====
    
    async def create_runners(self, request: RunnerRequest) -> List[RunnerResponse]:
        """Crea múltiples runners efímeros."""
        try:
            runners = []
            for i in range(request.count):
                runner_name = request.runner_name
                if request.count > 1:
                    runner_name = f"{request.runner_name}-{i+1}" if request.runner_name else None
                
                runner_id = self.lifecycle_manager.create_runner(
                    scope=request.scope,
                    scope_name=request.scope_name,
                    runner_name=runner_name,
                    runner_group=request.runner_group,
                    labels=request.labels,
                )
                
                runners.append(
                    RunnerResponse(
                        runner_id=runner_id, 
                        status="created", 
                        message="Runner creado exitosamente"
                    )
                )
            
            logger.info(f"Creados {len(runners)} runners para {request.scope}/{request.scope_name}")
            return runners
            
        except ValueError as e:
            raise
        except Exception as e:
            logger.error(f"Error creando runners: {e}")
            raise
    
    async def get_runner_status(self, runner_id: str) -> RunnerStatus:
        """Obtiene el estado de un runner específico."""
        try:
            status = self.lifecycle_manager.get_runner_status(runner_id)
            return RunnerStatus(**status)
            
        except Exception as e:
            logger.error(f"Error obteniendo estado del runner {runner_id}: {e}")
            raise
    
    async def destroy_runner(self, runner_id: str) -> Dict:
        """Destruye un runner específico."""
        try:
            success = self.lifecycle_manager.destroy_runner(runner_id)
            
            if not success:
                raise ValueError("Runner no encontrado o no se pudo destruir")
            
            return create_response(True, f"Runner {runner_id} destruido exitosamente")
            
        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Error destruyendo runner {runner_id}: {e}")
            raise
    
    async def list_runners(self) -> List[RunnerStatus]:
        """Lista todos los runners activos."""
        try:
            runners = self.lifecycle_manager.list_active_runners()
            return [RunnerStatus(**runner) for runner in runners]
            
        except Exception as e:
            logger.error(f"Error listando runners: {e}")
            raise
    
    async def cleanup_runners(self) -> Dict:
        """Limpia runners inactivos."""
        try:
            cleaned = self.lifecycle_manager.cleanup_inactive_runners()
            return create_response(True, f"Limpiados {cleaned} runners", {"cleaned_count": cleaned})
            
        except Exception as e:
            logger.error(f"Error en limpieza: {e}")
            raise
    
    async def get_runner_logs(self, runner_name: str) -> Dict:
        """Obtiene logs de un runner específico."""
        try:
            # Buscar contenedor por nombre
            container = self.lifecycle_manager.container_manager.get_container_by_name(runner_name)
            if not container:
                raise ValueError("Runner no encontrado")
            
            # Obtener logs
            logs = self.lifecycle_manager.container_manager.get_container_logs(container, tail=200)
            
            return create_response(True, "Logs obtenidos", {"logs": logs})
            
        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Error obteniendo logs del runner: {e}")
            raise
    
    # ===== MÉTODOS DE NEGOCIO PARA CONFIGURACIÓN =====
    
    async def get_configuration_info(self) -> ConfigurationInfo:
        """Obtiene información de configuración."""
        try:
            env_manager = self.lifecycle_manager.container_manager.environment_manager
            config_summary = env_manager.get_configuration_summary()
            return ConfigurationInfo(**config_summary)
            
        except Exception as e:
            logger.error(f"Error obteniendo información de configuración: {e}")
            raise
    
    async def validate_configuration(self) -> ValidationResult:
        """Valida la configuración actual."""
        try:
            validation_result = self.config_validator.get_validation_summary()
            recommendations = self.config_validator.get_configuration_recommendations()
            
            return ValidationResult(
                valid=validation_result["overall_valid"],
                errors=validation_result["validation_details"]["errors"],
                warnings=validation_result["validation_details"]["warnings"],
                recommendations=recommendations,
            )
            
        except Exception as e:
            logger.error(f"Error validando configuración: {e}")
            raise
    
    async def get_available_placeholders(self) -> Dict:
        """Obtiene placeholders disponibles."""
        try:
            placeholders = self.placeholder_resolver.get_available_placeholders()
            
            return create_response(
                True,
                "Placeholders obtenidos",
                {"total_placeholders": len(placeholders), "placeholders": placeholders},
            )
            
        except Exception as e:
            logger.error(f"Error obteniendo placeholders: {e}")
            raise
    
    # ===== MÉTODOS DE HEALTH CHECK =====
    
    async def health_check(self) -> Dict:
        """Health check básico del servicio."""
        return create_response(
            True,
            "Servicio saludable",
            {
                "service": "orchestrator",
                "active_runners": len(self.lifecycle_manager.active_runners),
                "monitoring": self.lifecycle_manager.monitoring,
            },
        )
    
    async def docker_health_check(self) -> Dict:
        """Health check para Docker Engine."""
        try:
            if not hasattr(self.lifecycle_manager, "active_runners"):
                raise ValueError("Lifecycle manager no inicializado")
            
            active_count = len(self.lifecycle_manager.active_runners)
            if active_count > 100:
                raise ValueError(f"Demasiados runners activos: {active_count}")
            
            return create_response(
                True,
                "Servicio saludable",
                {
                    "service": "orchestrator",
                    "active_runners": active_count,
                    "monitoring": self.lifecycle_manager.monitoring,
                },
            )
            
        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Error en health check: {e}")
            raise
    
    def stop_monitoring(self):
        """Detiene el monitoreo automático."""
        if hasattr(self.lifecycle_manager, 'stop_monitoring'):
            self.lifecycle_manager.stop_monitoring()
            logger.info("Monitoreo detenido")
