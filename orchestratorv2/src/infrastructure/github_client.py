"""
Cliente HTTP para GitHub API.

Rol: Cliente técnico para interactuar con GitHub API.
Maneja autenticación, requests HTTP y errores de red.
Implementa el contrato TokenProvider del dominio.

Depende de: requests library, configuración de tokens.
"""

import logging
from typing import Dict, Optional, List, Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from ..shared.infrastructure_exceptions import GitHubAPIError, NetworkError
from ..shared.logging_utils import log_operation_start, log_operation_success, log_operation_error, mask_sensitive_data
from ..shared.constants import GITHUB_API_BASE, DEFAULT_TIMEOUT, WorkflowStatus

logger = logging.getLogger(__name__)


class GitHubClient:
    """Cliente HTTP para GitHub API con manejo robusto de errores."""
    
    def __init__(self, token: str, api_base: str = GITHUB_API_BASE, timeout: int = DEFAULT_TIMEOUT):
        """
        Inicializa cliente GitHub API.
        
        Args:
            token: Token de autenticación de GitHub
            api_base: URL base de GitHub API
            timeout: Timeout para requests
        """
        self.token = token
        self.api_base = api_base.rstrip("/")
        self.timeout = timeout
        
        # Configurar headers
        self.headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "orchestratorv2/1.0.0"
        }
        
        # Configurar sesión con retry strategy
        self.session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "POST", "PUT", "DELETE", "OPTIONS", "TRACE"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
    
    def generate_registration_token(self, scope: str, scope_name: str) -> str:
        """
        Genera un registration token para GitHub Actions runner.
        
        Args:
            scope: 'repo' u 'org'
            scope_name: Nombre del repositorio u organización
        
        Returns:
            Token de registro temporal
        
        Raises:
            GitHubAPIError: Si hay error en la API
            NetworkError: Si hay error de red
        """
        operation = "generate_registration_token"
        log_operation_start(logger, operation, scope=scope, scope_name=scope_name)
        
        try:
            if scope == "repo":
                url = f"{self.api_base}/repos/{scope_name}/actions/runners/registration-token"
            else:  # org
                url = f"{self.api_base}/orgs/{scope_name}/actions/runners/registration-token"
            
            response = self.session.post(url, headers=self.headers, timeout=self.timeout)
            response.raise_for_status()
            
            token_data = response.json()
            token = token_data.get("token")
            
            if not token:
                raise GitHubAPIError("La API no devolvió un token válido")
            
            log_operation_success(logger, operation, scope=scope, scope_name=scope_name)
            return token
            
        except requests.exceptions.Timeout as e:
            log_operation_error(logger, operation, e, scope=scope, scope_name=scope_name)
            raise NetworkError(f"Timeout generando token: {e}")
        except requests.exceptions.RequestException as e:
            log_operation_error(logger, operation, e, scope=scope, scope_name=scope_name)
            raise GitHubAPIError(f"Error en API GitHub: {e}")
        except Exception as e:
            log_operation_error(logger, operation, e, scope=scope, scope_name=scope_name)
            raise GitHubAPIError(f"Error inesperado: {e}")
    
    def get_workflow_runs(self, repo: str, status: Optional[str] = None, per_page: int = 50) -> List[Dict[str, Any]]:
        """
        Obtiene workflow runs de un repositorio.
        
        Args:
            repo: Nombre del repositorio (owner/repo)
            status: Estado de los workflows (opcional)
            per_page: Número de resultados por página
        
        Returns:
            Lista de workflow runs
        
        Raises:
            GitHubAPIError: Si hay error en la API
            NetworkError: Si hay error de red
        """
        operation = "get_workflow_runs"
        log_operation_start(logger, operation, repo=repo, status=status, per_page=per_page)
        
        try:
            url = f"{self.api_base}/repos/{repo}/actions/runs"
            
            params = {"per_page": per_page}
            if status:
                params["status"] = status
            
            response = self.session.get(url, headers=self.headers, params=params, timeout=self.timeout)
            response.raise_for_status()
            
            data = response.json()
            workflow_runs = data.get("workflow_runs", [])
            
            log_operation_success(logger, operation, repo=repo, count=len(workflow_runs))
            return workflow_runs
            
        except requests.exceptions.Timeout as e:
            log_operation_error(logger, operation, e, repo=repo, status=status)
            raise NetworkError(f"Timeout obteniendo workflows: {e}")
        except requests.exceptions.RequestException as e:
            log_operation_error(logger, operation, e, repo=repo, status=status)
            raise GitHubAPIError(f"Error en API GitHub: {e}")
        except Exception as e:
            log_operation_error(logger, operation, e, repo=repo, status=status)
            raise GitHubAPIError(f"Error inesperado: {e}")
    
    def get_user_repositories(self) -> List[str]:
        """
        Obtiene todos los repositorios accesibles del usuario.
        
        Returns:
            Lista de nombres de repositorios (owner/repo)
        
        Raises:
            GitHubAPIError: Si hay error en la API
            NetworkError: Si hay error de red
        """
        operation = "get_user_repositories"
        log_operation_start(logger, operation)
        
        try:
            url = f"{self.api_base}/user/repos"
            
            repos = []
            page = 1
            per_page = 100
            
            while True:
                params = {"page": page, "per_page": per_page}
                response = self.session.get(url, headers=self.headers, params=params, timeout=self.timeout)
                response.raise_for_status()
                
                data = response.json()
                page_repos = data
                
                if not page_repos:
                    break
                
                repos.extend([f"{repo['owner']['login']}/{repo['name']}" for repo in page_repos])
                page += 1
            
            log_operation_success(logger, operation, count=len(repos))
            return repos
            
        except requests.exceptions.Timeout as e:
            log_operation_error(logger, operation, e)
            raise NetworkError(f"Timeout obteniendo repositorios: {e}")
        except requests.exceptions.RequestException as e:
            log_operation_error(logger, operation, e)
            raise GitHubAPIError(f"Error en API GitHub: {e}")
        except Exception as e:
            log_operation_error(logger, operation, e)
            raise GitHubAPIError(f"Error inesperado: {e}")
    
    def get_user_organizations(self) -> List[str]:
        """
        Obtiene organizaciones del usuario.
        
        Returns:
            Lista de nombres de organizaciones
        
        Raises:
            GitHubAPIError: Si hay error en la API
            NetworkError: Si hay error de red
        """
        operation = "get_user_organizations"
        log_operation_start(logger, operation)
        
        try:
            url = f"{self.api_base}/user/orgs"
            
            response = self.session.get(url, headers=self.headers, timeout=self.timeout)
            response.raise_for_status()
            
            orgs = response.json()
            org_names = [org["login"] for org in orgs]
            
            log_operation_success(logger, operation, count=len(org_names))
            return org_names
            
        except requests.exceptions.Timeout as e:
            log_operation_error(logger, operation, e)
            raise NetworkError(f"Timeout obteniendo organizaciones: {e}")
        except requests.exceptions.RequestException as e:
            log_operation_error(logger, operation, e)
            raise GitHubAPIError(f"Error en API GitHub: {e}")
        except Exception as e:
            log_operation_error(logger, operation, e)
            raise GitHubAPIError(f"Error inesperado: {e}")
    
    def get_organization_repositories(self, org: str) -> List[str]:
        """
        Obtiene repositorios de una organización.
        
        Args:
            org: Nombre de la organización
        
        Returns:
            Lista de nombres de repositorios (org/repo)
        
        Raises:
            GitHubAPIError: Si hay error en la API
            NetworkError: Si hay error de red
        """
        operation = "get_organization_repositories"
        log_operation_start(logger, operation, org=org)
        
        try:
            url = f"{self.api_base}/orgs/{org}/repos"
            
            repos = []
            page = 1
            per_page = 100
            
            while True:
                params = {"page": page, "per_page": per_page}
                response = self.session.get(url, headers=self.headers, params=params, timeout=self.timeout)
                response.raise_for_status()
                
                data = response.json()
                page_repos = data
                
                if not page_repos:
                    break
                
                repos.extend([f"{org}/{repo['name']}" for repo in page_repos])
                page += 1
            
            log_operation_success(logger, operation, org=org, count=len(repos))
            return repos
            
        except requests.exceptions.Timeout as e:
            log_operation_error(logger, operation, e, org=org)
            raise NetworkError(f"Timeout obteniendo repositorios de {org}: {e}")
        except requests.exceptions.RequestException as e:
            log_operation_error(logger, operation, e, org=org)
            raise GitHubAPIError(f"Error en API GitHub: {e}")
        except Exception as e:
            log_operation_error(logger, operation, e, org=org)
            raise GitHubAPIError(f"Error inesperado: {e}")
    
    def check_repository_workflows(self, repo: str) -> bool:
        """
        Verifica si un repositorio usa workflows con self-hosted runners.
        
        Args:
            repo: Nombre del repositorio (owner/repo)
        
        Returns:
            True si el repositorio usa self-hosted runners
        
        Raises:
            GitHubAPIError: Si hay error en la API
            NetworkError: Si hay error de red
        """
        operation = "check_repository_workflows"
        log_operation_start(logger, operation, repo=repo)
        
        try:
            url = f"{self.api_base}/repos/{repo}/contents/.github/workflows"
            
            response = self.session.get(url, headers=self.headers, timeout=self.timeout)
            
            if response.status_code == 404:
                # No hay workflows
                log_operation_success(logger, operation, repo=repo, has_workflows=False)
                return False
            
            response.raise_for_status()
            
            workflows = response.json()
            
            # Verificar si algún workflow usa self-hosted
            for workflow in workflows:
                if workflow.get("type") != "file":
                    continue
                
                download_url = workflow.get("download_url")
                if not download_url:
                    continue
                
                try:
                    workflow_response = self.session.get(download_url, headers=self.headers, timeout=self.timeout)
                    workflow_response.raise_for_status()
                    
                    content = workflow_response.text
                    
                    # Buscar indicadores de self-hosted runners
                    if ("runs-on: self-hosted" in content or
                        'runs-on: ["self-hosted"' in content or
                        'runs-on: [ "self-hosted"' in content):
                        log_operation_success(logger, operation, repo=repo, has_self_hosted=True)
                        return True
                        
                except Exception:
                    # Ignorar errores en archivos individuales
                    continue
            
            log_operation_success(logger, operation, repo=repo, has_self_hosted=False)
            return False
            
        except requests.exceptions.Timeout as e:
            log_operation_error(logger, operation, e, repo=repo)
            raise NetworkError(f"Timeout verificando workflows de {repo}: {e}")
        except requests.exceptions.RequestException as e:
            log_operation_error(logger, operation, e, repo=repo)
            raise GitHubAPIError(f"Error en API GitHub: {e}")
        except Exception as e:
            log_operation_error(logger, operation, e, repo=repo)
            raise GitHubAPIError(f"Error inesperado: {e}")
    
    def close(self):
        """Cierra la sesión HTTP."""
        if self.session:
            self.session.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
