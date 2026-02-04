"""
Modelos Pydantic para requests de la API.

Rol: Definir modelos de datos para validar requests entrantes.
RunnerRequest, CleanupRequest, ConfigRequest.
Asegura validación automática y tipado de datos.
"""

from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
from ..shared.validation_utils import validate_scope, validate_repository, validate_runner_name, validate_runner_group, validate_labels, validate_count
from ..shared.constants import ScopeType


class RunnerRequest(BaseModel):
    """"Request para crear runners efímeros."""
    
    scope: ScopeType
    scope_name: str
    runner_name: Optional[str] = None
    runner_group: Optional[str] = None
    labels: Optional[List[str]] = None
    count: int = Field(default=1, ge=1, le=10)
    
    @validator('scope_name')
    def validate_scope_name(cls, v):
        return validate_repository(v)
    
    @validator('runner_name')
    def validate_runner_name(cls, v):
        if v:
            return validate_runner_name(v)
        return None
    
    @validator('runner_group')
    def validate_runner_group(cls, v):
        if v:
            return validate_runner_group(v)
        return None
    
    @validator('labels')
    def validate_labels(cls, v):
        if v:
            validated_labels = validate_labels(v)
            return validated_labels
        return None
    
    @validator('count')
    def validate_count(cls, v):
        return validate_count(v)


class CleanupRequest(BaseModel):
    """"Request para limpieza de runners."""
    
    dry_run: bool = Field(default=False, description="Simular limpieza sin ejecutar")
    force: bool = Field(default=False, description="Forzar limpieza de todos los runners")
    timeout: int = Field(default=30, ge=1, le=300)


class ConfigRequest(BaseModel):
    """"Request para configuración del servicio."""
    
    poll_interval: Optional[int] = Field(default=None, ge=10, le=300)
    cleanup_interval: Optional[int] = Field(default=None, ge=60, le=600)
    max_runners_per_repo: Optional[int] = Field(default=None, ge=1, le=50)
    auto_create_runners: Optional[bool] = Field(default=None)
    
    @validator('poll_interval')
    def validate_poll_interval(cls, v):
        if v is not None and (v < 10 or v > 300):
            raise ValueError("poll_interval debe estar entre 10 y 300 segundos")
    
    @validator('cleanup_interval')
    def validate_cleanup_interval(cls, v):
        if v is not None and (v < 60 or v > 600):
            raise ValueError("cleanup_interval debe estar entre 60 y 600 segundos")
    
    @validator('max_runners_per_repo')
    def validate_max_runners_per_repo(cls, v):
        if v is not None and (v < 1 or v > 50):
            raise ValueError("max_runners_per_repo debe estar entre 1 y 50")
    
    @validator('auto_create_runners')
    def validate_auto_create_runners(cls, v):
        if v is not None and not isinstance(v, bool):
            raise ValueError("auto_create_runners debe ser booleano")


class HealthCheckRequest(BaseModel):
    """"Request para health checks."""
    
    detailed: bool = Field(default=False, description="Incluir información detallada")
    include_stats: bool = Field(default=True, description="Incluir estadísticas")
    include_config: bool = Field(default=True, description="Incluir configuración")


class ServiceConfig(BaseModel):
    """"Información de configuración del servicio."""
    
    poll_interval: int
    cleanup_interval: int
    max_runners_per_repo: int
    auto_create_runners: bool
    monitoring_active: bool
    total_runners: int
    repositories_with_demand: int
    last_cleanup_time: str
    errors_count: int


class Stats(BaseModel):
    """"Estadísticas del servicio."""
    
    total_runners: int
    state_distribution: Dict[str, int]
    repository_distribution: Dict[str, int]
    monitoring_active: bool
    last_cleanup_time: str
    errors_count: int


class RepositoryStats(BaseModel):
    """"Estadísticas por repositorio."""
    
    name: str
    active_workflows: int
    queued_jobs: int
    runner_demand: int
    uses_self_hosted: bool
    last_activity: str


class SystemStats(BaseModel):
    """"Estadísticas del sistema."""
    
    uptime_seconds: int
    memory_usage_mb: float
    cpu_usage_percent: float
    disk_usage_gb: float
    network_connections: int
    docker_containers: int
    python_version: str
    git_hash: str
    build_time: str
