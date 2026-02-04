"""
Configuración y validación centralizada de la aplicación.

Rol: Cargar variables de entorno, validar y proveer defaults.
Centraliza toda la configuración del sistema en un solo lugar.
Provee configuración tipada y validada para toda la aplicación.

Depende de: variables de entorno, pydantic para validación.
"""

import logging
import os
import re
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, validator
from pydantic_settings import BaseSettings

from ..shared.infrastructure_exceptions import ConfigurationError
from ..shared.validation_utils import validate_timeout, validate_count
from ..shared.constants import DEFAULT_TIMEOUT, DEFAULT_POLL_INTERVAL, DEFAULT_CLEANUP_INTERVAL

logger = logging.getLogger(__name__)


class GitHubConfig(BaseModel):
    """Configuración relacionada con GitHub API."""
    
    runner_token: str = Field(..., description="Token de registro de GitHub")
    api_base: str = Field(default="https://api.github.com", description="URL base de GitHub API")
    timeout: int = Field(default=DEFAULT_TIMEOUT, description="Timeout para requests")
    
    @validator('runner_token')
    def validate_github_token(cls, v):
        """Valida formato de token de GitHub."""
        pattern = r"^gh[pouhs]_[A-Za-z0-9_]{36,255}$"
        if not re.match(pattern, v):
            raise ValueError("Token de GitHub inválido")
        return v
    
    @validator('timeout')
    def validate_timeout(cls, v):
        """Valida timeout."""
        return validate_timeout(v)


class DockerConfig(BaseModel):
    """Configuración relacionada con Docker."""
    
    runner_image: str = Field(..., description="Imagen Docker para runners")
    default_timeout: int = Field(default=DEFAULT_TIMEOUT, description="Timeout por defecto")
    network_name: Optional[str] = Field(default=None, description="Nombre de red Docker")
    
    @validator('default_timeout')
    def validate_default_timeout(cls, v):
        """Valida timeout por defecto."""
        return validate_timeout(v)


class OrchestratorConfig(BaseModel):
    """Configuración principal del orchestrator."""
    
    poll_interval: int = Field(default=DEFAULT_POLL_INTERVAL, description="Intervalo de polling en segundos")
    cleanup_interval: int = Field(default=DEFAULT_CLEANUP_INTERVAL, description="Intervalo de limpieza en segundos")
    max_runners_per_repo: int = Field(default=10, description="Máximo de runners por repositorio")
    auto_create_runners: bool = Field(default=False, description="Crear runners automáticamente")
    
    @validator('poll_interval', 'cleanup_interval')
    def validate_intervals(cls, v):
        """Valida intervalos de tiempo."""
        if v < 10:
            raise ValueError("Intervalo debe ser >= 10 segundos")
        return v
    
    @validator('max_runners_per_repo')
    def validate_max_runners(cls, v):
        """Valida máximo de runners."""
        if v < 1 or v > 50:
            raise ValueError("Máximo de runners debe estar entre 1 y 50")
        return v


class APIConfig(BaseModel):
    """Configuración de la API REST."""
    
    host: str = Field(default="0.0.0.0", description="Host de la API")
    port: int = Field(default=8000, description="Puerto de la API")
    log_level: str = Field(default="INFO", description="Nivel de logging")
    cors_origins: List[str] = Field(default=["*"], description="Orígenes CORS")
    
    @validator('port')
    def validate_port(cls, v):
        """Valida puerto."""
        if not (1 <= v <= 65535):
            raise ValueError("Puerto debe estar entre 1 y 65535")
        return v
    
    @validator('log_level')
    def validate_log_level(cls, v):
        """Valida nivel de logging."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"Log level debe ser uno de: {valid_levels}")
        return v.upper()


class Config(BaseSettings):
    """Configuración centralizada de la aplicación."""
    
    github: GitHubConfig = Field(..., description="Configuración de GitHub")
    docker: DockerConfig = Field(..., description="Configuración de Docker")
    orchestrator: OrchestratorConfig = Field(default_factory=OrchestratorConfig, description="Configuración del orchestrator")
    api: APIConfig = Field(default_factory=APIConfig, description="Configuración de la API")
    
    # Variables de entorno adicionales
    environment: str = Field(default="development", description="Entorno de ejecución")
    debug: bool = Field(default=False, description="Modo debug")
    
    class Config:
        env_file = ".env"
        env_nested_delimiter = "__"
        case_sensitive = False
    
    @classmethod
    def from_env(cls) -> "Config":
        """Carga configuración desde variables de entorno."""
        try:
            return cls(
                github=GitHubConfig(
                    runner_token=os.getenv("GITHUB_RUNNER_TOKEN"),
                    api_base=os.getenv("GITHUB_API_BASE", "https://api.github.com"),
                    timeout=int(os.getenv("GITHUB_TIMEOUT", DEFAULT_TIMEOUT))
                ),
                docker=DockerConfig(
                    runner_image=os.getenv("RUNNER_IMAGE"),
                    default_timeout=int(os.getenv("DOCKER_TIMEOUT", DEFAULT_TIMEOUT)),
                    network_name=os.getenv("DOCKER_NETWORK_NAME")
                ),
                orchestrator=OrchestratorConfig(
                    poll_interval=int(os.getenv("RUNNER_CHECK_INTERVAL", DEFAULT_POLL_INTERVAL)),
                    cleanup_interval=int(os.getenv("RUNNER_CLEANUP_INTERVAL", DEFAULT_CLEANUP_INTERVAL)),
                    max_runners_per_repo=int(os.getenv("MAX_RUNNERS_PER_REPO", 10)),
                    auto_create_runners=os.getenv("AUTO_CREATE_RUNNERS", "false").lower() == "true"
                ),
                api=APIConfig(
                    host=os.getenv("API_HOST", "0.0.0.0"),
                    port=int(os.getenv("API_PORT", 8000)),
                    log_level=os.getenv("LOG_LEVEL", "INFO"),
                    cors_origins=os.getenv("CORS_ORIGINS", "*").split(",") if os.getenv("CORS_ORIGINS") else ["*"]
                ),
                environment=os.getenv("ENVIRONMENT", "development"),
                debug=os.getenv("DEBUG", "false").lower() == "true"
            )
        except Exception as e:
            logger.error(f"Error cargando configuración: {e}")
            raise ConfigurationError(f"Error en configuración: {e}")
    
    def validate(self) -> bool:
        """Valida toda la configuración."""
        try:
            # Validar configuración básica
            self.github  # Pydantic valida automáticamente
            self.docker
            self.orchestrator
            self.api
            
            # Validaciones adicionales
            if self.environment not in ["development", "staging", "production"]:
                raise ValueError("Environment debe ser: development, staging, production")
            
            return True
            
        except Exception as e:
            logger.error(f"Validación de configuración fallida: {e}")
            return False
    
    def get_runner_env_vars(self) -> Dict[str, str]:
        """Obtiene variables de entorno para runners (runnerenv_*)."""
        runner_vars = {}
        
        for key, value in os.environ.items():
            if key.startswith("runnerenv_"):
                env_key = key[11:]  # Remover prefijo
                runner_vars[env_key] = value
        
        return runner_vars
    
    def validate_runner_env_vars(self) -> Dict[str, Any]:
        """Valida variables de entorno de runners."""
        runner_vars = self.get_runner_env_vars()
        
        result = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "variables_found": len(runner_vars),
            "invalid_placeholders": []
        }
        
        if not runner_vars:
            result["warnings"].append("No se encontraron variables runnerenv_*")
            return result
        
        # Validar placeholders
        placeholder_pattern = r"\{[^}]+\}"
        valid_placeholders = {
            "{scope_name}", "{runner_name}", "{registration_token}",
            "{timestamp}", "{timestamp_iso}", "{hostname}",
            "{repo_owner}", "{repo_name}", "{repo_full_name}"
        }
        
        for env_key, env_value in runner_vars.items():
            placeholders = re.findall(placeholder_pattern, env_value)
            
            for placeholder in placeholders:
                if placeholder not in valid_placeholders:
                    result["invalid_placeholders"].append(f"{env_key}: {placeholder}")
                    result["valid"] = False
        
        if result["invalid_placeholders"]:
            result["errors"].append(f"Placeholders inválidos: {result['invalid_placeholders']}")
        
        return result


# Instancia global de configuración
_config: Optional[Config] = None


def get_config() -> Config:
    """Obtiene instancia de configuración (singleton)."""
    global _config
    
    if _config is None:
        _config = Config.from_env()
        
        if not _config.validate():
            raise ConfigurationError("Configuración inválida")
    
    return _config


def reload_config() -> Config:
    """Recarga la configuración desde variables de entorno."""
    global _config
    _config = None
    return get_config()
