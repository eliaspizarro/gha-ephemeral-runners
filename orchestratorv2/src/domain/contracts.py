"""
Contratos/interfaces para dependencias externas del dominio.

Rol: Definir las interfaces que el dominio necesita del mundo exterior.
Permite que el dominio permanezca aislado de implementaciones técnicas.
Usa ABC para definir contratos que deben cumplir las implementaciones.

Implementado por: ContainerManager, TokenProvider en infrastructure.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional


class ContainerManager(ABC):
    """Contrato para gestión de contenedores Docker."""
    
    @abstractmethod
    def create_runner_container(
        self,
        registration_token: str,
        scope: str,
        scope_name: str,
        runner_name: Optional[str] = None,
        runner_group: Optional[str] = None,
        labels: Optional[list] = None,
    ) -> Any:
        """Crea un contenedor Docker para un runner."""
        pass
    
    @abstractmethod
    def stop_container(self, container: Any, timeout: int = 30) -> bool:
        """Detiene un contenedor de runner."""
        pass
    
    @abstractmethod
    def remove_container(self, container: Any, timeout: int = 30) -> bool:
        """"Elimina un contenedor de runner."""
        pass
    
    @abstractmethod
    def get_runner_containers(self) -> list:
        """Obtiene todos los contenedores de runners activos."""
        pass
    
    @abstractmethod
    def get_container_by_name(self, runner_name: str) -> Optional[Any]:
        """Busca un contenedor por nombre."""
        pass
    
    @abstractmethod
    def get_container_info(self, container: Any) -> Dict[str, Any]:
        """Obtiene información de un contenedor."""
        pass
    
    @abstractmethod
    def is_container_running(self, container: Any) -> bool:
        """Verifica si un contenedor está corriendo."""
        pass


class TokenProvider(ABC):
    """Contrato para gestión de tokens de GitHub."""
    
    @abstractmethod
    def generate_registration_token(self, scope: str, scope_name: str) -> str:
        """Genera un token de registro para GitHub Actions."""
        pass
    
    @abstractmethod
    def get_workflow_runs(self, repo: str, status: Optional[str] = None) -> list:
        """Obtiene workflow runs de un repositorio."""
        pass
    
    @abstractmethod
    def get_user_repositories(self) -> list:
        """Obtiene repositorios del usuario."""
        pass
    
    @abstractmethod
    def get_user_organizations(self) -> list:
        """Obtiene organizaciones del usuario."""
        pass
    
    @abstractmethod
    def get_organization_repositories(self, org: str) -> list:
        """Obtiene repositorios de una organización."""
        pass
    
    @abstractmethod
    def check_repository_workflows(self, repo: str) -> bool:
        """Verifica si un repositorio usa self-hosted runners."""
        pass
