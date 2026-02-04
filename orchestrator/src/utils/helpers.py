"""
Utilitarios consolidados para el orchestrator.
Combina utils.py, error_handler.py y placeholder_resolver.py.
"""

import datetime
import logging
import os
import re
import socket
import time
from typing import Any, Dict, Optional

from fastapi import HTTPException


# ===== CONFIGURACIÓN Y LOGGING =====

def setup_logger(name: str) -> logging.Logger:
    """Configura y retorna un logger estandarizado."""
    return logging.getLogger(name)


def setup_logging_config():
    """Configura el logging básico para toda la aplicación."""
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s, %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    # Reducir verbosidad de uvicorn
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.error").setLevel(logging.ERROR)


def get_env_var(key: str, default: str = None, required: bool = False) -> str:
    """Obtiene variable de entorno con validación."""
    value = os.getenv(key, default)
    if required and not value:
        raise RuntimeError(f"{key} es obligatorio")
    return value


# ===== UTILIDADES DE CONTENEDORES =====

def format_container_id(container_id: str) -> str:
    """Formatea ID de contenedor a 12 caracteres."""
    return container_id[:12] if container_id else "unknown"


def validate_runner_name(runner_name: str) -> str:
    """Valida y normaliza nombre de runner."""
    if not runner_name:
        raise ValueError("runner_name no puede estar vacío")
    
    # Eliminar caracteres inválidos
    clean_name = re.sub(r"[^a-zA-Z0-9_-]", "", runner_name)
    
    if not clean_name:
        raise ValueError("runner_name contiene caracteres inválidos")
    
    return clean_name


# ===== RESPUESTAS ESTANDARIZADAS =====

def create_response(success: bool, message: str, data: Any = None) -> Dict[str, Any]:
    """Crea una respuesta estandarizada."""
    response = {"success": success, "message": message}
    
    if data is not None:
        response["data"] = data
    
    return response


# ===== MANEJO DE ERRORES =====

class OrchestratorError(Exception):
    """Error base del orchestrator."""
    pass


class ValidationError(OrchestratorError):
    """Error de validación."""
    pass


class DockerError(OrchestratorError):
    """Error relacionado con Docker."""
    pass


class GitHubError(OrchestratorError):
    """Error relacionado con GitHub API."""
    pass


class ConfigurationError(OrchestratorError):
    """Error de configuración."""
    pass


class ErrorHandler:
    """Manejador centralizado de errores."""
    
    @staticmethod
    def handle_error(
        error: Exception, operation: str, logger: logging.Logger, context: Optional[Dict[str, Any]] = None
    ) -> HTTPException:
        """Maneja errores de forma centralizada."""
        error_type = type(error).__name__
        error_msg = str(error)
        
        # Logging detallado
        logger.error(f"Error en {operation}: {error_type} - {error_msg}")
        if context:
            logger.error(f"Contexto: {context}")
        
        # Mapeo de errores a HTTP status codes
        if isinstance(error, ValidationError):
            return HTTPException(status_code=400, detail=f"Error de validación: {error_msg}")
        
        elif isinstance(error, DockerError):
            return HTTPException(status_code=500, detail=f"Error de Docker: {error_msg}")
        
        elif isinstance(error, GitHubError):
            return HTTPException(status_code=502, detail=f"Error de GitHub API: {error_msg}")
        
        elif isinstance(error, ConfigurationError):
            return HTTPException(status_code=500, detail=f"Error de configuración: {error_msg}")
        
        elif isinstance(error, (ValueError, KeyError)):
            return HTTPException(status_code=400, detail=f"Error en datos: {error_msg}")
        
        elif isinstance(error, ConnectionError):
            return HTTPException(status_code=503, detail="Error de conexión")
        
        else:
            return HTTPException(status_code=500, detail="Error interno del servidor")


# ===== RESOLUCIÓN DE PLACEHOLDERS =====

class PlaceholderResolver:
    """Resuelve placeholders dinamicos en configuraciones de runners."""
    
    def __init__(self):
        self.orchestrator_id = f"orchestrator-{os.getpid()}"
    
    def resolve_placeholders(self, template: str, context: Dict[str, Any]) -> str:
        """Resuelve todos los placeholders en una plantilla."""
        try:
            # Validar contexto minimo
            required_context = ["scope_name", "runner_name", "registration_token"]
            for key in required_context:
                if key not in context:
                    logger.warning(f"Context missing required variable: {key}")
                    context[key] = f"missing_{key}"
            
            # Construir diccionario de sustituciones
            substitutions = self._build_substitutions(context)
            
            # Reemplazar placeholders
            result = template
            for placeholder, value in substitutions.items():
                result = result.replace(placeholder, str(value))
            
            return result
        
        except Exception as e:
            logger.error(f"Error resolviendo placeholders: {e}")
            return template
    
    def _build_substitutions(self, context: Dict[str, Any]) -> Dict[str, str]:
        """Construye diccionario completo de sustituciones."""
        now = datetime.datetime.utcnow()
        scope_name = context.get("scope_name", "")
        runner_name = context.get("runner_name", "")
        registration_token = context.get("registration_token", "")
        
        # Variables basicas
        substitutions = {
            "{scope_name}": scope_name,
            "{runner_name}": runner_name,
            "{registration_token}": registration_token,
            # Variables de tiempo
            "{timestamp}": str(int(time.time())),
            "{timestamp_iso}": now.isoformat() + "Z",
            "{timestamp_date}": now.strftime("%Y-%m-%d"),
            "{timestamp_time}": now.strftime("%H-%M-%S"),
            # Variables de sistema
            "{hostname}": socket.gethostname(),
            "{orchestrator_id}": self.orchestrator_id,
            "{docker_network}": os.getenv("DOCKER_NETWORK", "bridge"),
            # Variables de entorno
            "{orchestrator_port}": os.getenv("ORCHESTRATOR_PORT", "8000"),
            "{api_gateway_port}": os.getenv("API_GATEWAY_PORT", "8080"),
            "{runner_image}": os.getenv("RUNNER_IMAGE", "unknown"),
            "{registry_url}": os.getenv("REGISTRY", "unknown"),
            # Variables de GitHub API
            "{repo_owner}": self._extract_repo_owner(scope_name),
            "{repo_name}": self._extract_repo_name(scope_name),
            "{repo_full_name}": scope_name,
            "{user_login}": os.getenv("GITHUB_USER_LOGIN", "unknown"),
        }
        
        return substitutions
    
    def _extract_repo_owner(self, scope_name: str) -> str:
        """Extrae el owner del scope_name."""
        if "/" in scope_name:
            return scope_name.split("/")[0]
        return "unknown"
    
    def _extract_repo_name(self, scope_name: str) -> str:
        """Extrae el nombre del repo del scope_name."""
        if "/" in scope_name:
            return scope_name.split("/")[1]
        return scope_name
    
    def get_available_placeholders(self) -> Dict[str, str]:
        """Retorna lista de placeholders disponibles con descripción."""
        return {
            # Básicas
            "{scope_name}": "Nombre del repositorio/organización (ej: eliaspizarro/hello-ci)",
            "{runner_name}": "Nombre único del runner (ej: ephemeral-runner-abc123)",
            "{registration_token}": "Token efímero de registro",
            # Tiempo
            "{timestamp}": "Timestamp Unix actual",
            "{timestamp_iso}": "Timestamp ISO 8601 (ej: 2024-02-03T18:30:34Z)",
            "{timestamp_date}": "Fecha actual YYYY-MM-DD (ej: 2024-02-03)",
            "{timestamp_time}": "Hora actual HH-MM-SS (ej: 18-30-34)",
            # Sistema
            "{hostname}": "Hostname del sistema (ej: docker2)",
            "{orchestrator_id}": "ID único del orchestrator",
            "{docker_network}": "Red Docker usada",
            # Entorno
            "{orchestrator_port}": "Puerto del orchestrator (ej: 8000)",
            "{api_gateway_port}": "Puerto del API Gateway (ej: 8080)",
            "{runner_image}": "Imagen del runner usada",
            "{registry_url}": "URL del registry",
            # GitHub API
            "{repo_owner}": "Owner del repositorio (ej: eliaspizarro)",
            "{repo_name}": "Nombre del repo sin owner (ej: hello-ci)",
            "{repo_full_name}": "Nombre completo del repo (ej: eliaspizarro/hello-ci)",
            "{user_login}": "Username del token",
        }
    
    def validate_template(self, template: str) -> Dict[str, Any]:
        """Valida una plantilla y retorna información sobre placeholders."""
        # Encontrar todos los placeholders
        placeholders = re.findall(r"\{[^}]+\}", template)
        available = self.get_available_placeholders()
        
        valid_placeholders = []
        invalid_placeholders = []
        
        for placeholder in placeholders:
            if placeholder in available:
                valid_placeholders.append(placeholder)
            else:
                invalid_placeholders.append(placeholder)
        
        return {
            "template": template,
            "total_placeholders": len(placeholders),
            "valid_placeholders": valid_placeholders,
            "invalid_placeholders": invalid_placeholders,
            "is_valid": len(invalid_placeholders) == 0,
        }
