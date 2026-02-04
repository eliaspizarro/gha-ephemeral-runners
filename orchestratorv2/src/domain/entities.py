"""
Entidades de dominio con identidad y reglas de negocio.

Rol: Definir las entidades principales del sistema con su ciclo de vida.
Contiene Runner, Workflow, Repository.
Estas entidades no tienen dependencias externas y representan el modelo de dominio puro.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, Optional, List
from enum import Enum

from ..shared.constants import RunnerState, WorkflowStatus, ScopeType


@dataclass
class Runner:
    """Entidad principal: Runner efímero de GitHub Actions."""
    
    id: str
    name: str
    scope: ScopeType
    scope_name: str
    state: RunnerState = RunnerState.CREATED
    container_id: Optional[str] = None
    repository: Optional[str] = None
    runner_group: Optional[str] = None
    labels: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def transition_to(self, new_state: RunnerState) -> None:
        """Transiciona el runner a un nuevo estado."""
        if not self._is_valid_transition(self.state, new_state):
            raise ValueError(f"Transición inválida: {self.state} -> {new_state}")
        
        self.state = new_state
        self.updated_at = datetime.utcnow()
    
    def _is_valid_transition(self, from_state: RunnerState, to_state: RunnerState) -> bool:
        """Verifica si la transición de estados es válida."""
        valid_transitions = {
            RunnerState.CREATED: [RunnerState.STARTING, RunnerState.ERROR],
            RunnerState.STARTING: [RunnerState.RUNNING, RunnerState.ERROR],
            RunnerState.RUNNING: [RunnerState.IDLE, RunnerState.BUSY, RunnerState.STOPPING],
            RunnerState.IDLE: [RunnerState.BUSY, RunnerState.STOPPING],
            RunnerState.BUSY: [RunnerState.IDLE, RunnerState.STOPPING],
            RunnerState.STOPPING: [RunnerState.STOPPED, RunnerState.ERROR],
            RunnerState.STOPPED: [],
            RunnerState.ERROR: [RunnerState.STOPPING],
            RunnerState.UNKNOWN: [RunnerState.STOPPING],
        }
        
        return to_state in valid_transitions.get(from_state, [])
    
    def is_active(self) -> bool:
        """Verifica si el runner está activo."""
        return self.state in [RunnerState.RUNNING, RunnerState.IDLE, RunnerState.BUSY]
    
    def is_terminatable(self) -> bool:
        """Verifica si el runner puede ser terminado."""
        return self.state in [RunnerState.IDLE, RunnerState.ERROR, RunnerState.UNKNOWN]
    
    def add_label(self, label: str) -> None:
        """Agrega un label al runner."""
        if label not in self.labels:
            self.labels.append(label)
            self.updated_at = datetime.utcnow()
    
    def remove_label(self, label: str) -> None:
        """Remueve un label del runner."""
        if label in self.labels:
            self.labels.remove(label)
            self.updated_at = datetime.utcnow()


@dataclass
class Workflow:
    """Entidad: Workflow de GitHub Actions."""
    
    id: int
    repository: str
    name: str
    status: WorkflowStatus
    branch: Optional[str] = None
    commit_sha: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    run_number: Optional[int] = None
    conclusion: Optional[str] = None
    jobs_count: int = 0
    self_hosted_jobs: int = 0
    
    def is_active(self) -> bool:
        """Verifica si el workflow está activo."""
        return self.status in [WorkflowStatus.QUEUED, WorkflowStatus.IN_PROGRESS, WorkflowStatus.PENDING]
    
    def is_completed(self) -> bool:
        """Verifica si el workflow está completado."""
        return self.status in [WorkflowStatus.COMPLETED, WorkflowStatus.FAILED, WorkflowStatus.CANCELLED, WorkflowStatus.SKIPPED]
    
    def needs_runner(self) -> bool:
        """Verifica si el workflow necesita un runner."""
        return self.is_active() and self.self_hosted_jobs > 0
    
    def update_status(self, new_status: WorkflowStatus) -> None:
        """Actualiza el estado del workflow."""
        self.status = new_status
        self.updated_at = datetime.utcnow()
    
    def add_job(self, is_self_hosted: bool = True) -> None:
        """Agrega un job al workflow."""
        self.jobs_count += 1
        if is_self_hosted:
            self.self_hosted_jobs += 1


@dataclass
class Repository:
    """Entidad: Repositorio de GitHub."""
    
    name: str
    owner: str
    full_name: str
    description: Optional[str] = None
    is_private: bool = False
    has_workflows: bool = False
    uses_self_hosted: bool = False
    last_activity: Optional[datetime] = None
    active_workflows: int = 0
    queued_jobs: int = 0
    
    @property
    def scope_name(self) -> str:
        """Retorna el nombre completo del repositorio."""
        return self.full_name
    
    def update_activity(self) -> None:
        """Actualiza la última actividad del repositorio."""
        self.last_activity = datetime.utcnow()
    
    def increment_active_workflows(self) -> None:
        """Incrementa el contador de workflows activos."""
        self.active_workflows += 1
        self.update_activity()
    
    def decrement_active_workflows(self) -> None:
        """Decrementa el contador de workflows activos."""
        if self.active_workflows > 0:
            self.active_workflows -= 1
        self.update_activity()
    
    def set_queued_jobs(self, count: int) -> None:
        """Establece el número de jobs en cola."""
        self.queued_jobs = max(0, count)
        self.update_activity()
    
    def needs_runners(self) -> bool:
        """Verifica si el repositorio necesita runners."""
        return (self.uses_self_hosted and 
                (self.active_workflows > 0 or self.queued_jobs > 0))
    
    def get_runner_demand(self) -> int:
        """Calcula la demanda de runners para este repositorio."""
        return self.active_workflows + self.queued_jobs


@dataclass
class RunnerGroup:
    """Entidad: Grupo de runners."""
    
    name: str
    description: Optional[str] = None
    max_runners: int = 10
    current_runners: int = 0
    repositories: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    def can_add_runner(self) -> bool:
        """Verifica si se puede agregar un runner al grupo."""
        return self.current_runners < self.max_runners
    
    def add_runner(self) -> None:
        """Agrega un runner al grupo."""
        if self.can_add_runner():
            self.current_runners += 1
        else:
            raise ValueError(f"Grupo {self.name} está en su capacidad máxima")
    
    def remove_runner(self) -> None:
        """Remueve un runner del grupo."""
        if self.current_runners > 0:
            self.current_runners -= 1
    
    def add_repository(self, repository: str) -> None:
        """Agrega un repositorio al grupo."""
        if repository not in self.repositories:
            self.repositories.append(repository)
    
    def remove_repository(self, repository: str) -> None:
        """Remueve un repositorio del grupo."""
        if repository in self.repositories:
            self.repositories.remove(repository)
