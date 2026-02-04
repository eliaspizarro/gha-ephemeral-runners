"""
Constantes globales de la aplicación.

Rol: Definir constantes usadas en toda la aplicación.
DEFAULT_TIMEOUT, RUNNER_STATES, API_ENDPOINTS.
Centraliza valores mágicos y configuraciones fijas.

Depende de: enums para estados, typing para tipos.
"""

from enum import Enum
from typing import Dict, List

# Constantes de configuración
DEFAULT_TIMEOUT = 30.0
DEFAULT_POLL_INTERVAL = 60
DEFAULT_CLEANUP_INTERVAL = 300
MAX_RUNNER_NAME_LENGTH = 64

# Estados de runners
class RunnerState(Enum):
    """Estados posibles de un runner."""
    CREATED = "created"
    STARTING = "starting"
    RUNNING = "running"
    IDLE = "idle"
    BUSY = "busy"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"
    UNKNOWN = "unknown"

# Estados de workflows
class WorkflowStatus(Enum):
    """Estados posibles de workflows en GitHub."""
    QUEUED = "queued"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    SKIPPED = "skipped"
    PENDING = "pending"
    WAITING = "waiting"
    REQUESTED = "requested"

# Tipos de scope
class ScopeType(Enum):
    """Tipos de scope para runners."""
    REPO = "repo"
    ORG = "org"
    ENTERPRISE = "enterprise"

# Endpoints de GitHub API
GITHUB_API_BASE = "https://api.github.com"
GITHUB_API_ENDPOINTS = {
    "user_repos": "/user/repos",
    "user_orgs": "/user/orgs",
    "org_repos": "/orgs/{org}/repos",
    "repo_workflows": "/repos/{owner}/{repo}/actions/runs",
    "repo_contents": "/repos/{owner}/{repo}/contents/.github/workflows",
}

# Labels estándar para contenedores
DEFAULT_CONTAINER_LABELS = {
    "gha-ephemeral": "true",
    "managed-by": "orchestratorv2",
}

# Expresiones regulares para validación
RUNNER_NAME_PATTERN = r"^[a-zA-Z0-9_-]{1,64}$"
REPO_NAME_PATTERN = r"^[a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+$"

# Límites y umbrales
MAX_ACTIVE_RUNNERS_PER_REPO = 10
MAX_CONCURRENT_OPERATIONS = 5
RUNNER_CREATION_TIMEOUT = 300  # 5 minutos
RUNNER_DESTRUCTION_TIMEOUT = 60   # 1 minuto

# Mensajes de error estándar
ERROR_MESSAGES = {
    "runner_not_found": "Runner no encontrado",
    "invalid_state": "Estado inválido para la operación",
    "docker_error": "Error en operación Docker",
    "github_api_error": "Error en GitHub API",
    "configuration_error": "Error de configuración",
    "validation_error": "Error de validación de datos",
}
