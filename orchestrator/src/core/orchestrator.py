"""
Lógica principal del servicio Orchestrator.
Contiene toda la lógica de negocio separada de la API FastAPI.
"""

import logging
import os
from typing import Dict, List

from src.api.models import (
    ConfigurationInfo, 
    RunnerRequest, 
    RunnerResponse, 
    RunnerStatus, 
    ValidationResult
)
from src.core.lifecycle import LifecycleManager
from src.services.config import ConfigValidator
from src.utils.helpers import (
    ConfigurationError, 
    PlaceholderResolver,
    create_response, 
    setup_logger,
    get_env_var
)

# Configuración de logging centralizada
logger = setup_logger(__name__)


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
            logger.info("=== INICIALIZANDO ORCHESTRATOR SERVICE ===")
            logger.info("Configurando variables de entorno...")
            
            self.github_runner_token = get_env_var("GITHUB_RUNNER_TOKEN", required=True)
            logger.info(f"GITHUB_RUNNER_TOKEN: {'***CONFIGURADO***' if self.github_runner_token else 'NO CONFIGURADO'}")
            
            self.runner_image = get_env_var("RUNNER_IMAGE", required=True)
            logger.info(f"RUNNER_IMAGE: {self.runner_image}")
            
            self.auto_create_runners = os.getenv("AUTO_CREATE_RUNNERS", "false").lower() == "true"
            logger.info(f"AUTO_CREATE_RUNNERS: {self.auto_create_runners}")
            
            self.runner_check_interval = int(os.getenv("RUNNER_CHECK_INTERVAL", "300"))
            logger.info(f"RUNNER_CHECK_INTERVAL: {self.runner_check_interval} segundos")
            
            # Mostrar todas las variables de entorno relevantes
            logger.info("Variables de entorno configuradas:")
            for key, value in os.environ.items():
                if key.startswith(('GITHUB_', 'RUNNER_', 'AUTO_')):
                    if 'TOKEN' in key:
                        logger.info(f"  {key}: ***CONFIGURADO***")
                    else:
                        logger.info(f"  {key}: {value}")
            
            logger.info("✅ Variables de entorno inicializadas correctamente")
            
        except Exception as e:
            logger.error(f"❌ Error inicializando variables de entorno: {e}")
            raise
    
    def _initialize_components(self):
        """Inicializa componentes principales."""
        try:
            logger.info("Inicializando componentes del orchestrator...")
            
            # Inicializar Lifecycle Manager
            logger.info("Creando Lifecycle Manager...")
            self.lifecycle_manager = LifecycleManager(self.github_runner_token, self.runner_image)
            logger.info("✅ Lifecycle Manager inicializado")
            
            # Inicializar Config Validator
            logger.info("Creando Config Validator...")
            self.config_validator = ConfigValidator()
            logger.info("✅ Config Validator inicializado")
            
            # Inicializar Placeholder Resolver
            logger.info("Creando Placeholder Resolver...")
            self.placeholder_resolver = PlaceholderResolver()
            logger.info("✅ Placeholder Resolver inicializado")
            
            logger.info("✅ Todos los componentes inicializados correctamente")
            
        except Exception as e:
            logger.error(f"❌ Error inicializando componentes: {e}")
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
            logger.info("Configurando sistema de monitoreo...")
            
            if self.auto_create_runners:
                logger.info(f"🚀 AUTOMATIZACIÓN ACTIVADA")
                logger.info(f"⏰ Verificando runners cada {self.runner_check_interval} segundos")
                logger.info("🔍 Iniciando monitoreo automático de workflows...")
                self.lifecycle_manager.start_monitoring(self.runner_check_interval)
                logger.info("✅ Monitoreo automático iniciado")
            else:
                logger.info("⏸️  AUTOMATIZACIÓN DESACTIVADA")
                logger.info("ℹ️  Los runners se crearán solo por solicitud manual via API")
                
            logger.info("✅ Sistema de monitoreo configurado correctamente")
            logger.info("=== ORCHESTRATOR SERVICE INICIALIZADO COMPLETAMENTE ===")
                
        except Exception as e:
            logger.error(f"❌ Error configurando monitoreo: {e}")
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
