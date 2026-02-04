"""
Modelos Pydantic para respuestas de la API.

Rol: Definir modelos de datos para respuestas salientes.
RunnerResponse, StatusResponse, ErrorResponse.
Asegura consistencia en formato de respuestas.
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime


class RunnerResponse(BaseModel):
    """"Response para creación de runners."""
    
    success: bool
    runner_id: Optional[str] = None
    runner_name: Optional[str] = None
    message: str
    error: Optional[str] = None
    container_id: Optional[str] = None
    created_at: Optional[datetime] = None


class RunnerStatus(BaseModel):
    """"Estado de un runner."""
    
    runner_id: str
    status: str
    container_id: Optional[str] = None
    image: Optional[str] = None
    created: Optional[str] = None
    updated: Optional[str] = None
    repository: Optional[str] = None
    runner_group: Optional[str] = None
    labels: Optional[List[str]] = None
    state: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class CleanupResponse(BaseModel):
    """"Response para limpieza de runners."""
    
    success: bool
    cleaned_count: int
    dry_run: bool
    candidates_count: Optional[int] = None
    candidates: Optional[List[Dict[str, Any]]] = None
    message: str
    execution_time: Optional[float] = None


class MonitoringResponse(BaseModel):
    """"Response para operaciones de monitoreo."""
    
    success: bool
    monitoring_active: bool
    message: str
    poll_interval: Optional[int] = None
    cleanup_interval: Optional[int] = None
    total_cycles: Optional[int] = None
    errors_count: Optional[int] = None
    last_check_time: Optional[str] = None


class DiscoveryResponse(BaseModel):
    """"Response para descubrimiento automático."""
    
    success: bool
    repositories_found: int
    repositories_processed: int
    runners_created: int
    dry_run: bool
    processed_repos: Optional[List[str]] = None
    message: str
    execution_time: Optional[float] = None


class ErrorResponse(BaseModel):
    """"Response estándar para errores."""
    
    success: bool = False
    error: str
    message: str
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    request_id: Optional[str] = None


class SuccessResponse(BaseModel):
    """"Response estándar para operaciones exitosas."""
    
    success: bool = True
    message: str
    data: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    request_id: Optional[str] = None


class HealthResponse(BaseModel):
    """"Response para health checks."""
    
    status: str
    message: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    uptime_seconds: Optional[int] = None
    version: Optional[str] = None
    environment: Optional[str] = None
    monitoring_active: Optional[bool] = None
    total_runners: Optional[int] = None
    last_cleanup_time: Optional[str] = None
    errors_count: Optional[int] = None
    config: Optional[Dict[str, Any]] = None
    stats: Optional[Dict[str, Any]] = None
    system_stats: Optional[Dict[str, Any]] = None


class ConfigResponse(BaseModel):
    """"Response para configuración."""
    
    success: bool
    message: str
    updated_config: Optional[Dict[str, Any]] = None
    previous_config: Optional[Dict[str, Any]] = None
    changes: Optional[List[str]] = None


class RepositoryInfo(BaseModel):
    """"Información de un repositorio."""
    
    name: str
    owner: str
    full_name: str
    active_workflows: int
    queued_jobs: int
    runner_demand: int
    uses_self_hosted: bool
    last_activity: Optional[str] = None
    current_runners: int
    max_runners: int


class RepositoryListResponse(BaseModel):
    """"Response para lista de repositorios."""
    
    success: bool
    total_repositories: int
    repositories_with_demand: int
    repositories: List[RepositoryInfo]
    message: str


class BatchOperationResponse(BaseModel):
    """"Response para operaciones batch."""
    
    success: bool
    total_operations: int
    successful_operations: int
    failed_operations: int
    results: List[Dict[str, Any]]
    message: str
    execution_time: Optional[float] = None


class StatisticsResponse(BaseModel):
    """"Response para estadísticas."""
    
    success: bool
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    total_runners: int
    state_distribution: Dict[str, int]
    repository_distribution: Dict[str, int]
    monitoring_active: bool
    last_cleanup_time: str
    errors_count: int
    uptime_seconds: int
    repositories_with_demand: int
    top_repositories: Optional[List[Dict[str, Any]]] = None
    system_stats: Optional[Dict[str, Any]] = None
