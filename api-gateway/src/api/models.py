"""
API Gateway - Pydantic Models for Request/Response Validation
Contains all data models used by the API Gateway for request validation and response formatting.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class RunnerRequest(BaseModel):
    """Model for runner creation requests."""
    scope: str = Field(..., description="Tipo de scope: 'repo' u 'org'")
    scope_name: str = Field(..., description="Nombre del repositorio (owner/repo) u organización")
    runner_name: Optional[str] = Field(None, description="Nombre único del runner")
    runner_group: Optional[str] = Field(None, description="Grupo del runner")
    labels: Optional[List[str]] = Field(None, description="Labels para el runner")
    count: int = Field(1, ge=1, le=10, description="Número de runners a crear")


class RunnerResponse(BaseModel):
    """Model for runner creation responses."""
    runner_id: str
    status: str
    message: str


class RunnerStatus(BaseModel):
    """Model for runner status information."""
    runner_id: str
    status: str
    container_id: Optional[str] = None
    image: Optional[str] = None
    created: Optional[str] = None
    labels: Optional[Dict] = None


class APIResponse(BaseModel):
    """Standard API response model."""
    status: str = "success"
    data: Optional[Any] = None
    message: str = ""
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class ErrorResponse(APIResponse):
    """Error response model."""
    status: str = "error"
    data: Optional[Dict] = None
