"""
Configuración de entorno para contenedores de runners.

Rol: Configurar variables de entorno y placeholders para runners.
Procesa plantillas de configuración y resuelve placeholders.
Prepara el entorno específico para cada tipo de runner.

Depende de: Config, plantillas de entorno.
"""

import logging
import os
from typing import Any, Dict

from ..shared.logging_utils import log_operation_start, log_operation_success, log_operation_error
from ..shared.infrastructure_exceptions import ConfigurationError

logger = logging.getLogger(__name__)


class EnvironmentSetup:
    """Configuración de entorno para runners con soporte para placeholders."""
    
    def __init__(self, runner_image: str):
        """
        Inicializa configurador de entorno.
        
        Args:
            runner_image: Imagen Docker del runner
        """
        self.runner_image = runner_image
        self._cached_config: Dict[str, str] = {}
    
    def process_environment_variables(
        self, scope_name: str, runner_name: str, registration_token: str
    ) -> Dict[str, str]:
        """
        Procesa variables de entorno resolviendo placeholders.
        
        Args:
            scope_name: Nombre del repositorio/organización
            runner_name: Nombre único del runner
            registration_token: Token de registro
        
        Returns:
            Diccionario de variables procesadas
        """
        operation = "process_environment_variables"
        log_operation_start(logger, operation, scope_name=scope_name, runner_name=runner_name)
        
        try:
            # Cargar variables base
            raw_env = self._load_runner_environment()
            
            if not raw_env:
                logger.warning("No se encontraron variables runnerenv_")
                processed_env = self._get_default_environment(scope_name, runner_name, registration_token)
                log_operation_success(logger, operation, scope_name=scope_name, runner_name=runner_name, vars_count=len(processed_env))
                return processed_env
            
            # Contexto para resolución de placeholders
            context = {
                "scope_name": scope_name,
                "runner_name": runner_name,
                "registration_token": registration_token,
            }
            
            # Procesar cada variable
            processed_env = {}
            for key, value in raw_env.items():
                resolved_value = self._resolve_placeholders(value, context)
                processed_env[key] = resolved_value
                
                # Log de resolución para debugging
                if value != resolved_value:
                    logger.debug(f"Variable {key}: '{value}' -> '{resolved_value}'")
            
            log_operation_success(logger, operation, scope_name=scope_name, runner_name=runner_name, vars_count=len(processed_env))
            return processed_env
            
        except Exception as e:
            log_operation_error(logger, operation, e, scope_name=scope_name, runner_name=runner_name)
            raise ConfigurationError(f"Error procesando variables de entorno: {e}")
    
    def _load_runner_environment(self) -> Dict[str, str]:
        """
        Carga variables de entorno con prefijo runnerenv_.
        
        Returns:
            Diccionario de variables de entorno para el runner
        """
        if self._cached_config:
            return self._cached_config
        
        runner_env = {}
        
        # Cargar todas las variables con prefijo runnerenv_
        for key, value in os.environ.items():
            if key.startswith("runnerenv_"):
                # Remover prefijo "runnerenv_"
                env_key = key[11:]  # Remover prefijo
                runner_env[env_key] = value
                logger.debug(f"Variable runnerenv encontrada: {env_key}")
        
        self._cached_config = runner_env
        logger.info(f"Cargadas {len(runner_env)} variables de entorno para runners")
        
        # Si no se encontraron variables, mostrar advertencia
        if not runner_env:
            logger.warning("No se encontraron variables runnerenv_ en el entorno")
            logger.warning("Asegúrate de que el compose.yaml esté pasando correctamente las variables runnerenv_")
        
        return runner_env
    
    def _resolve_placeholders(self, template: str, context: Dict[str, Any]) -> str:
        """
        Resuelve placeholders en una plantilla.
        
        Args:
            template: Plantilla con placeholders
            context: Contexto con variables
        
        Returns:
            Template con placeholders resueltos
        """
        import datetime
        import socket
        import time
        
        try:
            # Construir diccionario de sustituciones
            now = datetime.datetime.utcnow()
            scope_name = context.get("scope_name", "")
            
            substitutions = {
                # Variables basicas
                "{scope_name}": scope_name,
                "{runner_name}": context.get("runner_name", ""),
                "{registration_token}": context.get("registration_token", ""),
                # Variables de tiempo
                "{timestamp}": str(int(time.time())),
                "{timestamp_iso}": now.isoformat() + "Z",
                "{timestamp_date}": now.strftime("%Y-%m-%d"),
                "{timestamp_time}": now.strftime("%H-%M-%S"),
                # Variables de sistema
                "{hostname}": socket.gethostname(),
                "{orchestrator_id}": f"orchestrator-{os.getpid()}",
                "{docker_network}": os.getenv("DOCKER_NETWORK", "bridge"),
                # Variables de entorno
                "{orchestrator_port}": os.getenv("ORCHESTRATOR_PORT", "8000"),
                "{api_gateway_port}": os.getenv("API_GATEWAY_PORT", "8080"),
                "{runner_image}": self.runner_image,
                "{registry_url}": os.getenv("REGISTRY", "unknown"),
                # Variables de GitHub API
                "{repo_owner}": self._extract_repo_owner(scope_name),
                "{repo_name}": self._extract_repo_name(scope_name),
                "{repo_full_name}": scope_name,
                "{user_login}": os.getenv("GITHUB_USER_LOGIN", "unknown"),
            }
            
            # Reemplazar placeholders
            result = template
            for placeholder, value in substitutions.items():
                result = result.replace(placeholder, str(value))
            
            return result
            
        except Exception as e:
            logger.error(f"Error resolviendo placeholders: {e}")
            return template
    
    def _extract_repo_owner(self, scope_name: str) -> str:
        """
        Extrae el owner del scope_name.
        
        Args:
            scope_name: Nombre en formato owner/repo
        
        Returns:
            Owner del repositorio
        """
        if "/" in scope_name:
            return scope_name.split("/")[0]
        return scope_name
    
    def _extract_repo_name(self, scope_name: str) -> str:
        """
        Extrae el nombre del repo del scope_name.
        
        Args:
            scope_name: Nombre en formato owner/repo
        
        Returns:
            Nombre del repositorio
        """
        if "/" in scope_name:
            return scope_name.split("/")[1]
        return scope_name
    
    def _get_default_environment(
        self, scope_name: str, runner_name: str, registration_token: str
    ) -> Dict[str, str]:
        """
        Genera entorno por defecto si no hay variables runnerenv_.
        
        Args:
            scope_name: Nombre del repositorio/organización
            runner_name: Nombre del runner
            registration_token: Token de registro
        
        Returns:
            Entorno por defecto
        """
        return {
            "RUNNER_NAME": runner_name,
            "REPO_URL": f"https://github.com/{scope_name}",
            "REGISTRATION_TOKEN": registration_token,
            "RUNNER_GROUP": "default",
            "RUNNER_LABELS": "self-hosted,ephemeral",
            "DISABLE_AUTO_UPDATE": "true",
        }
    
    def validate_environment(self, env_vars: Dict[str, str]) -> Dict[str, Any]:
        """
        Valida variables de entorno procesadas.
        
        Args:
            env_vars: Variables de entorno a validar
        
        Returns:
            Resultado de validación
        """
        result = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "missing_required": [],
        }
        
        # Validar variables obligatorias
        required_vars = ["RUNNER_NAME", "REGISTRATION_TOKEN"]
        
        for var in required_vars:
            if var not in env_vars or not env_vars[var]:
                result["missing_required"].append(var)
                result["valid"] = False
        
        # Validar formato de variables específicas
        if "RUNNER_GROUP" in env_vars:
            group = env_vars["RUNNER_GROUP"]
            if len(group) > 64:
                result["errors"].append("RUNNER_GROUP no puede exceder 64 caracteres")
                result["valid"] = False
        
        # Generar errores y warnings finales
        if result["missing_required"]:
            result["errors"].append(f"Variables obligatorias faltantes: {result['missing_required']}")
        
        return result
    
    def clear_cache(self):
        """Limpia la caché de configuración."""
        self._cached_config.clear()
        logger.info("Caché de configuración de entorno limpiada")
