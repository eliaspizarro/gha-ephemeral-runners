"""
Servicio principal de orquestación de lógica de negocio.

Rol: Coordinar la lógica principal de orquestación sin dependencias técnicas.
Decide cuándo crear/destruir runners basándose en reglas de negocio.
Coordina con GitHub Service y mantiene estado global de runners activos.
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

from ..shared.constants import RunnerState, WorkflowStatus, ScopeType, DEFAULT_CLEANUP_INTERVAL
from ..shared.domain_exceptions import RunnerNotFound, OrchestrationError
from ..shared.logging_utils import log_operation_start, log_operation_success, log_operation_error
from ..domain.entities import Runner, Workflow, Repository
from .contracts import ContainerManager, TokenProvider
from .github_service import GitHubService

logger = logging.getLogger(__name__)


class OrchestrationService:
    """Servicio principal de orquestación de runners efímeros."""
    
    def __init__(
        self,
        container_manager: ContainerManager,
        token_provider: TokenProvider,
        github_service: Optional[GitHubService] = None
    ):
        """
        Inicializa servicio de orquestación.
        
        Args:
            container_manager: Gestor de contenedores Docker
            token_provider: Proveedor de tokens GitHub
            github_service: Servicio de GitHub (opcional, se crea si no se proporciona)
        """
        self.container_manager = container_manager
        self.token_provider = token_provider
        self.github_service = github_service or GitHubService(token_provider)
        
        # Estado global de runners
        self.active_runners: Dict[str, Runner] = {}
        self.runner_containers: Dict[str, Any] = {}
        
        # Configuración
        self.max_runners_per_repo = 10
        self.default_runner_group = "default"
        self.default_labels = ["self-hosted", "ephemeral"]
        
        # Estado de monitoreo
        self.monitoring_active = False
        self.last_cleanup_time = datetime.utcnow()
    
    def create_runner(
        self,
        scope: str,
        scope_name: str,
        runner_name: Optional[str] = None,
        runner_group: Optional[str] = None,
        labels: Optional[List[str]] = None,
    ) -> str:
        """
        Crea un nuevo runner efímero.
        
        Args:
            scope: 'repo' u 'org'
            scope_name: Nombre del repositorio u organización
            runner_name: Nombre único del runner (opcional)
            runner_group: Grupo del runner (opcional)
            labels: Labels para el runner (opcional)
        
        Returns:
            ID del runner creado
        
        Raises:
            OrchestrationError: Si falla la creación
        """
        operation = "create_runner"
        log_operation_start(logger, operation, scope=scope, scope_name=scope_name)
        
        try:
            # Validar parámetros
            self._validate_create_params(scope, scope_name)
            
            # Verificar límites
            if not self._can_create_runner(scope_name):
                raise OrchestrationError(f"Límite de runners alcanzado para {scope_name}")
            
            # Generar token de registro
            registration_token = self.token_provider.generate_registration_token(scope, scope_name)
            
            # Crear contenedor
            container = self.container_manager.create_runner_container(
                registration_token=registration_token,
                scope=scope,
                scope_name=scope_name,
                runner_name=runner_name,
                runner_group=runner_group or self.default_runner_group,
                labels=labels or self.default_labels
            )
            
            # Crear entidad Runner
            runner_id = container.labels.get("runner-name", container.id[:12])
            
            runner = Runner(
                id=runner_id,
                name=runner_id,
                scope=ScopeType(scope),
                scope_name=scope_name,
                state=RunnerState.CREATED,
                container_id=container.id,
                repository=scope_name,
                runner_group=runner_group or self.default_runner_group,
                labels=labels or self.default_labels
            )
            
            # Actualizar estado
            self.active_runners[runner_id] = runner
            self.runner_containers[runner_id] = container
            
            # Transicionar a estado STARTING
            runner.transition_to(RunnerState.STARTING)
            
            log_operation_success(logger, operation, 
                                 runner_id=runner_id, scope=scope, scope_name=scope_name,
                                 container_id=container.id[:12])
            
            return runner_id
            
        except Exception as e:
            log_operation_error(logger, operation, e, scope=scope, scope_name=scope_name)
            raise OrchestrationError(f"Error creando runner: {e}")
    
    def destroy_runner(self, runner_id: str, timeout: int = 30) -> bool:
        """
        Destruye un runner específico.
        
        Args:
            runner_id: ID del runner a destruir
            timeout: Timeout para destrucción
        
        Returns:
            True si se destruyó exitosamente
        
        Raises:
            RunnerNotFound: Si el runner no existe
            OrchestrationError: Si falla la destrucción
        """
        operation = "destroy_runner"
        log_operation_start(logger, operation, runner_id=runner_id)
        
        try:
            # Verificar que el runner existe
            if runner_id not in self.active_runners:
                raise RunnerNotFound(f"Runner {runner_id} no encontrado")
            
            runner = self.active_runners[runner_id]
            container = self.runner_containers.get(runner_id)
            
            if not container:
                # El contenedor ya no existe, limpiar estado
                self._cleanup_runner_state(runner_id)
                log_operation_success(logger, operation, runner_id=runner_id, already_gone=True)
                return True
            
            # Transicionar a estado STOPPING
            runner.transition_to(RunnerState.STOPPING)
            
            # Detener y eliminar contenedor
            self.container_manager.remove_container(container, timeout)
            
            # Transicionar a estado STOPPED
            runner.transition_to(RunnerState.STOPPED)
            
            # Limpiar estado
            self._cleanup_runner_state(runner_id)
            
            log_operation_success(logger, operation, runner_id=runner_id)
            return True
            
        except Exception as e:
            log_operation_error(logger, operation, e, runner_id=runner_id)
            raise OrchestrationError(f"Error destruyendo runner {runner_id}: {e}")
    
    def cleanup_inactive_runners(self) -> int:
        """
        Limpia runners inactivos basándose en estado de workflows.
        
        Returns:
            Número de runners limpiados
        """
        operation = "cleanup_inactive_runners"
        log_operation_start(logger, operation)
        
        try:
            cleaned_count = 0
            runners_to_remove = []
            
            # Identificar runners que pueden ser eliminados
            for runner_id, runner in self.active_runners.items():
                if self._should_cleanup_runner(runner):
                    runners_to_remove.append(runner_id)
            
            # Eliminar runners identificados
            for runner_id in runners_to_remove:
                try:
                    self.destroy_runner(runner_id, timeout=10)
                    cleaned_count += 1
                except Exception as e:
                    logger.error(f"Error limpiando runner {runner_id}: {e}")
            
            self.last_cleanup_time = datetime.utcnow()
            
            log_operation_success(logger, operation, cleaned_count=cleaned_count)
            return cleaned_count
            
        except Exception as e:
            log_operation_error(logger, operation, e)
            raise OrchestrationError(f"Error en limpieza de runners: {e}")
    
    def get_runner_status(self, runner_id: str) -> Dict[str, Any]:
        """
        Obtiene el estado de un runner.
        
        Args:
            runner_id: ID del runner
        
        Returns:
            Diccionario con estado del runner
        """
        try:
            if runner_id not in self.active_runners:
                # Intentar buscar por nombre
                container = self.container_manager.get_container_by_name(runner_id)
                if container:
                    # Runner existe pero no está en estado activo
                    container_info = self.container_manager.get_container_info(container)
                    return {
                        "status": "found",
                        "runner_id": runner_id,
                        "container_info": container_info
                    }
                else:
                    return {"status": "not_found", "runner_id": runner_id}
            
            runner = self.active_runners[runner_id]
            container = self.runner_containers.get(runner_id)
            
            if container:
                # Actualizar estado del contenedor
                is_running = self.container_manager.is_container_running(container)
                
                # Actualizar estado del runner basado en el contenedor
                if is_running and runner.state == RunnerState.STARTING:
                    runner.transition_to(RunnerState.RUNNING)
                elif not is_running and runner.state == RunnerState.RUNNING:
                    runner.transition_to(RunnerState.STOPPED)
                
                container_info = self.container_manager.get_container_info(container)
                
                return {
                    "status": "active",
                    "runner_id": runner_id,
                    "state": runner.state.value,
                    "container_info": container_info,
                    "repository": runner.repository,
                    "runner_group": runner.runner_group,
                    "labels": runner.labels,
                    "created_at": runner.created_at.isoformat(),
                    "updated_at": runner.updated_at.isoformat()
                }
            else:
                # El contenedor ya no existe
                return {
                    "status": "container_lost",
                    "runner_id": runner_id,
                    "state": runner.state.value,
                    "repository": runner.repository
                }
                
        except Exception as e:
            logger.error(f"Error obteniendo estado del runner {runner_id}: {e}")
            return {"status": "error", "runner_id": runner_id, "error": str(e)}
    
    def list_active_runners(self) -> List[Dict[str, Any]]:
        """
        Lista todos los runners activos.
        
        Returns:
            Lista de información de runners activos
        """
        try:
            runners_info = []
            
            for runner_id in self.active_runners:
                runner_status = self.get_runner_status(runner_id)
                runners_info.append(runner_status)
            
            return runners_info
            
        except Exception as e:
            logger.error(f"Error listando runners activos: {e}")
            return []
    
    def get_repository_runner_demand(self, repo: str) -> int:
        """
        Calcula la demanda de runners para un repositorio.
        
        Args:
            repo: Nombre del repositorio
        
        Returns:
            Número de runners necesarios
        """
        try:
            return self.github_service.calculate_runner_demand(repo)
        except Exception as e:
            logger.error(f"Error calculando demanda para {repo}: {e}")
            return 0
    
    def should_create_runner_for_repo(self, repo: str) -> bool:
        """
        Decide si se debe crear un runner para un repositorio.
        
        Args:
            repo: Nombre del repositorio
        
        Returns:
            True si se debe crear un runner
        """
        try:
            # Verificar si el repositorio necesita runners
            if not self.github_service.should_create_runner_for_repo(repo):
                return False
            
            # Verificar si ya hay suficientes runners
            current_runners = self._count_runners_for_repo(repo)
            needed_runners = self.get_repository_runner_demand(repo)
            
            return current_runners < needed_runners
            
        except Exception as e:
            logger.error(f"Error evaluando creación de runner para {repo}: {e}")
            return False
    
    def get_repositories_needing_runners(self) -> List[Repository]:
        """
        Obtiene repositorios que necesitan runners.
        
        Returns:
            Lista de repositorios con demanda
        """
        try:
            return self.github_service.get_repositories_needing_runners()
        except Exception as e:
            logger.error(f"Error obteniendo repositorios needing runners: {e}")
            return []
    
    def _validate_create_params(self, scope: str, scope_name: str) -> None:
        """Valida parámetros de creación de runner."""
        if scope not in [s.value for s in ScopeType]:
            raise OrchestrationError(f"Scope inválido: {scope}")
        
        if not scope_name or "/" not in scope_name:
            raise OrchestrationError(f"Scope name inválido: {scope_name}")
    
    def _can_create_runner(self, scope_name: str) -> bool:
        """Verifica si se puede crear un runner para el repositorio."""
        current_count = self._count_runners_for_repo(scope_name)
        return current_count < self.max_runners_per_repo
    
    def _count_runners_for_repo(self, repo: str) -> int:
        """Cuenta runners activos para un repositorio."""
        count = 0
        for runner in self.active_runners.values():
            if runner.repository == repo:
                count += 1
        return count
    
    def _should_cleanup_runner(self, runner: Runner) -> bool:
        """Determina si un runner debe ser limpiado."""
        # Si el runner está en estado terminable
        if not runner.is_terminatable():
            return False
        
        # Verificar si hay workflows activos para el repositorio
        try:
            active_workflows = self.github_service.get_active_workflows_for_repo(runner.repository)
            queued_jobs = self.github_service.get_queued_jobs_for_repo(runner.repository)
            
            # Si no hay workflows activos ni jobs en cola, limpiar
            return active_workflows == 0 and queued_jobs == 0
            
        except Exception:
            # Si hay error verificando, ser conservador y no limpiar
            return False
    
    def _cleanup_runner_state(self, runner_id: str) -> None:
        """Limpia el estado de un runner."""
        if runner_id in self.active_runners:
            del self.active_runners[runner_id]
        
        if runner_id in self.runner_containers:
            del self.runner_containers[runner_id]
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Obtiene estadísticas del servicio de orquestación.
        
        Returns:
            Diccionario con estadísticas
        """
        try:
            total_runners = len(self.active_runners)
            
            # Contar runners por estado
            state_counts = {}
            for runner in self.active_runners.values():
                state = runner.state.value
                state_counts[state] = state_counts.get(state, 0) + 1
            
            # Contar runners por repositorio
            repo_counts = {}
            for runner in self.active_runners.values():
                repo = runner.repository or "unknown"
                repo_counts[repo] = repo_counts.get(repo, 0) + 1
            
            return {
                "total_runners": total_runners,
                "state_distribution": state_counts,
                "repository_distribution": repo_counts,
                "monitoring_active": self.monitoring_active,
                "last_cleanup_time": self.last_cleanup_time.isoformat(),
                "max_runners_per_repo": self.max_runners_per_repo
            }
            
        except Exception as e:
            logger.error(f"Error obteniendo estadísticas: {e}")
            return {"error": str(e)}
