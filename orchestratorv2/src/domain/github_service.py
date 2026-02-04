"""
Servicio de lógica de negocio relacionada con GitHub.

Rol: Contener la lógica de negocio pura para interactuar con GitHub.
Interpreta estados de workflows y decide acciones basadas en GitHub.
No contiene código HTTP, solo lógica de interpretación y decisión.

Depende de: TokenProvider (interface) para obtener tokens.
"""

from typing import List, Dict, Any, Optional

from ..shared.constants import WorkflowStatus, ScopeType
from ..shared.domain_exceptions import WorkflowError, RepositoryError
from ..domain.entities import Workflow, Repository
from .contracts import TokenProvider


class GitHubService:
    """Servicio de lógica de negocio para GitHub API."""
    
    def __init__(self, token_provider: TokenProvider):
        """
        Inicializa servicio de GitHub.
        
        Args:
            token_provider: Proveedor de tokens de GitHub
        """
        self.token_provider = token_provider
    
    def get_active_workflows_for_repo(self, repo: str) -> int:
        """
        Obtiene workflows activos para un repositorio.
        
        Args:
            repo: Nombre del repositorio (owner/repo)
        
        Returns:
            Número de workflows activos
        
        Raises:
            WorkflowError: Si hay error en la lógica
        """
        try:
            workflow_runs = self.token_provider.get_workflow_runs(repo, "in_progress")
            
            # Filtrar runs que podrían necesitar self-hosted
            active_count = 0
            for run in workflow_runs:
                # Asumimos que si el repo usa self-hosted, estos jobs lo necesitan
                if self._workflow_needs_runner(run):
                    active_count += 1
            
            return active_count
            
        except Exception as e:
            raise WorkflowError(f"Error obteniendo workflows activos para {repo}: {e}")
    
    def get_queued_jobs_for_repo(self, repo: str) -> int:
        """
        Obtiene jobs en cola para un repositorio.
        
        Args:
            repo: Nombre del repositorio (owner/repo)
        
        Returns:
            Número de jobs en cola
        
        Raises:
            WorkflowError: Si hay error en la lógica
        """
        try:
            workflow_runs = self.token_provider.get_workflow_runs(repo, "queued")
            
            # Contar jobs que podrían necesitar self-hosted
            queued_count = 0
            for run in workflow_runs:
                if self._workflow_needs_runner(run):
                    queued_count += 1
            
            return queued_count
            
        except Exception as e:
            raise WorkflowError(f"Error obteniendo jobs en cola para {repo}: {e}")
    
    def get_repository_info(self, repo: str) -> Repository:
        """
        Obtiene información completa de un repositorio.
        
        Args:
            repo: Nombre del repositorio (owner/repo)
        
        Returns:
            Entidad Repository con información completa
        
        Raises:
            RepositoryError: Si hay error en la lógica
        """
        try:
            # Extraer owner y repo name
            if "/" not in repo:
                raise RepositoryError(f"Formato de repositorio inválido: {repo}")
            
            owner, repo_name = repo.split("/", 1)
            
            # Verificar si usa self-hosted runners
            uses_self_hosted = self.token_provider.check_repository_workflows(repo)
            
            # Obtener workflows activos y en cola
            active_workflows = self.get_active_workflows_for_repo(repo)
            queued_jobs = self.get_queued_jobs_for_repo(repo)
            
            return Repository(
                name=repo_name,
                owner=owner,
                full_name=repo,
                has_workflows=True,  # Si podemos consultar, tiene workflows
                uses_self_hosted=uses_self_hosted,
                active_workflows=active_workflows,
                queued_jobs=queued_jobs
            )
            
        except Exception as e:
            raise RepositoryError(f"Error obteniendo información del repositorio {repo}: {e}")
    
    def get_user_repositories(self) -> List[Repository]:
        """
        Obtiene todos los repositorios del usuario.
        
        Returns:
            Lista de entidades Repository
        
        Raises:
            RepositoryError: Si hay error en la lógica
        """
        try:
            repo_names = self.token_provider.get_user_repositories()
            
            repositories = []
            for repo_name in repo_names:
                try:
                    repo_info = self.get_repository_info(repo_name)
                    repositories.append(repo_info)
                except Exception:
                    # Ignorar errores individuales y continuar
                    continue
            
            return repositories
            
        except Exception as e:
            raise RepositoryError(f"Error obteniendo repositorios del usuario: {e}")
    
    def get_organization_repositories(self, org: str) -> List[Repository]:
        """
        Obtiene todos los repositorios de una organización.
        
        Args:
            org: Nombre de la organización
        
        Returns:
            Lista de entidades Repository
        
        Raises:
            RepositoryError: Si hay error en la lógica
        """
        try:
            repo_names = self.token_provider.get_organization_repositories(org)
            
            repositories = []
            for repo_name in repo_names:
                try:
                    repo_info = self.get_repository_info(repo_name)
                    repositories.append(repo_info)
                except Exception:
                    # Ignorar errores individuales y continuar
                    continue
            
            return repositories
            
        except Exception as e:
            raise RepositoryError(f"Error obteniendo repositorios de {org}: {e}")
    
    def get_all_accessible_repositories(self) -> List[Repository]:
        """
        Obtiene todos los repositorios accesibles (usuario + organizaciones).
        
        Returns:
            Lista combinada de todos los repositorios
        
        Raises:
            RepositoryError: Si hay error en la lógica
        """
        try:
            # Obtener repositorios del usuario
            user_repos = self.get_user_repositories()
            
            # Obtener organizaciones y sus repositorios
            orgs = self.token_provider.get_user_organizations()
            all_repos = user_repos.copy()
            
            for org in orgs:
                try:
                    org_repos = self.get_organization_repositories(org)
                    all_repos.extend(org_repos)
                except Exception:
                    # Ignorar errores de organizaciones individuales
                    continue
            
            return all_repos
            
        except Exception as e:
            raise RepositoryError(f"Error obteniendo todos los repositorios accesibles: {e}")
    
    def should_create_runner_for_repo(self, repo: str) -> bool:
        """
        Decide si se debe crear un runner para un repositorio.
        
        Args:
            repo: Nombre del repositorio
        
        Returns:
            True si se debe crear un runner
        """
        try:
            repo_info = self.get_repository_info(repo)
            return repo_info.needs_runners()
            
        except Exception:
            # Si hay error, no crear runner
            return False
    
    def get_repositories_needing_runners(self) -> List[Repository]:
        """
        Obtiene repositorios que actualmente necesitan runners.
        
        Returns:
            Lista de repositorios con demanda de runners
        """
        try:
            all_repos = self.get_all_accessible_repositories()
            
            needing_runners = []
            for repo in all_repos:
                if repo.needs_runners():
                    needing_runners.append(repo)
            
            # Ordenar por demanda (mayor primero)
            needing_runners.sort(key=lambda r: r.get_runner_demand(), reverse=True)
            
            return needing_runners
            
        except Exception as e:
            raise RepositoryError(f"Error obteniendo repositorios needing runners: {e}")
    
    def _workflow_needs_runner(self, workflow_run: Dict[str, Any]) -> bool:
        """
        Determina si un workflow run necesita un runner self-hosted.
        
        Args:
            workflow_run: Datos del workflow run
        
        Returns:
            True si necesita runner self-hosted
        """
        # Lógica simplificada: si el workflow está activo, asumimos que necesita runner
        # En una implementación más completa, se analizarían los jobs específicos
        status = workflow_run.get("status", "")
        return status in ["queued", "in_progress", "pending"]
    
    def calculate_runner_demand(self, repo: str) -> int:
        """
        Calcula la demanda de runners para un repositorio.
        
        Args:
            repo: Nombre del repositorio
        
        Returns:
            Número de runners necesarios
        """
        try:
            active = self.get_active_workflows_for_repo(repo)
            queued = self.get_queued_jobs_for_repo(repo)
            
            # Lógica simple: 1 runner por workflow activo + 1 por cada 5 jobs en cola
            demand = active + max(1, queued // 5)
            
            return min(demand, 10)  # Máximo 10 runners por repositorio
            
        except Exception:
            return 0
