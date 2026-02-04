"""
OrchestratorV2 - GitHub Actions Ephemeral Runners

Versión: 0.1.0
Arquitectura: Clean Architecture con DDD
Propósito: Orquestación de runners efímeros para GitHub Actions
"""

__version__ = "0.1.0"
__author__ = "OrchestratorV2 Team"
__description__ = "GitHub Actions Ephemeral Runners Orchestrator"

# Exportaciones principales del dominio
from .domain.entities import Runner, Workflow, Repository
from .domain.orchestration_service import OrchestrationService
from .domain.github_service import GitHubService

# Exportaciones de casos de uso
from .use_cases.create_runner import CreateRunner
from .use_cases.destroy_runner import DestroyRunner
from .use_cases.cleanup_runners import CleanupRunners

# Exportaciones de infraestructura
from .infrastructure.container_manager import ContainerManager
from .infrastructure.github_client import GitHubClient
from .infrastructure.config import Config

__all__ = [
    # Versión y metadata
    "__version__",
    "__author__",
    "__description__",
    
    # Entidades de dominio
    "Runner",
    "Workflow", 
    "Repository",
    
    # Servicios principales
    "OrchestrationService",
    "GitHubService",
    
    # Casos de uso
    "CreateRunner",
    "DestroyRunner",
    "CleanupRunners",
    
    # Infraestructura
    "ContainerManager",
    "GitHubClient",
    "Config",
]
