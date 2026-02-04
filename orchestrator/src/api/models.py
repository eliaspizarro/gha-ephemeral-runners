"""
Modelos de datos para la API del Orchestrator.
Define las estructuras de datos para requests y respuestas.
"""

from typing import Dict, List, Optional
from pydantic import BaseModel


class RunnerRequest(BaseModel):
    """Modelo para solicitud de creación de runner."""
    scope: str
    scope_name: str
    runner_name: Optional[str] = None
    runner_group: Optional[str] = None
    labels: Optional[List[str]] = None
    count: int = 1


class RunnerResponse(BaseModel):
    """Modelo para respuesta de creación de runner."""
    runner_id: str
    status: str
    message: str


class RunnerStatus(BaseModel):
    """Modelo para estado de un runner."""
    runner_id: str
    status: str
    container_id: Optional[str] = None
    image: Optional[str] = None
    created: Optional[str] = None
    labels: Optional[Dict] = None


class ConfigurationInfo(BaseModel):
    """Modelo para información de configuración."""
    runner_image: str
    total_variables: int
    variable_names: List[str]
    has_configuration: bool
    available_placeholders: int
    orchestrator_id: str


class ValidationResult(BaseModel):
    """Modelo para resultado de validación de configuración."""
    valid: bool
    errors: List[str]
    warnings: List[str]
    recommendations: List[str]
