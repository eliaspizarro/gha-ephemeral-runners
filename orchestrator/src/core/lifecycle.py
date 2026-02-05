import logging
import os
import threading
import time
from typing import Any, Dict, List, Optional
from functools import wraps

import requests
from src.core.container import ContainerManager
from src.services.docker import DockerUtils
from src.services.tokens import TokenGenerator
from src.utils.helpers import format_log

logger = logging.getLogger(__name__)


def handle_lifecycle_errors(func):
    """Decorador para manejar errores estandarizados."""
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        try:
            return func(self, *args, **kwargs)
        except Exception as e:
            logger.error(f"❌ Error en {func.__name__}: {e}")
            raise
    return wrapper


class LifecycleManager:
    def __init__(self, github_runner_token: str, runner_image: str):
        self.token_generator = TokenGenerator(github_runner_token)
        self.container_manager = ContainerManager(runner_image)
        self.active_runners: Dict[str, Any] = {}
        self.monitoring = False
        self.monitor_thread: Optional[threading.Thread] = None

    def _github_api_call(self, endpoint: str, params: Dict = None) -> Dict:
        """Método genérico para llamadas a GitHub API."""
        url = f"{self.token_generator.api_base}/{endpoint}"
        response = requests.get(url, headers=self.token_generator.headers, 
                              params=params, timeout=30.0)
        return response.json() if response.status_code == 200 else {}

    
    @handle_lifecycle_errors
    def create_runner(
        self,
        scope: str,
        scope_name: str,
        runner_name: Optional[str] = None,
        runner_group: Optional[str] = None,
        labels: Optional[List[str]] = None,
    ) -> str:
        """Crea un runner efímero."""
        logger.info(f"🚀 Creando runner para {scope}/{scope_name}")
        
        registration_token = self.token_generator.generate_registration_token(scope, scope_name)
        container = self.container_manager.create_runner_container(
            registration_token=registration_token,
            scope=scope,
            scope_name=scope_name,
            runner_name=runner_name,
            runner_group=runner_group,
            labels=labels,
        )

        runner_id = DockerUtils.get_container_labels(container).get("runner-name", container.id[:12])
        self.active_runners[runner_id] = container
        container_id = DockerUtils.format_container_id(container.id)
        logger.info(f"✅ Runner creado: {runner_id} (container: {container_id})")
        return runner_id

    @handle_lifecycle_errors
    def get_runner_status(self, runner_id: str) -> Dict:
        """Obtiene el estado de un runner."""
        container = self.active_runners.get(runner_id)
        if not container:
            return {"status": "error", "runner_id": runner_id, "error": "Runner no encontrado"}
        
        try:
            info = DockerUtils.get_container_info(container)
            return {
                "status": "running" if info["status"] == "running" else "stopped",
                "runner_id": runner_id,
                "container_id": info["id"],
                "image": info["image"],
                "created": info["created"],
                "labels": info["labels"],
            }
        except Exception as e:
            return {"status": "error", "runner_id": runner_id, "error": str(e)}

    @handle_lifecycle_errors
    def destroy_runner(self, runner_id: str) -> bool:
        """Destruye un runner efímero."""
        logger.info(f"🗑️  Destruyendo runner: {runner_id}")
        
        container = self.active_runners.get(runner_id)
        if not container:
            container = self.container_manager.get_container_by_name(runner_id)

        if not container:
            logger.warning(f"⚠️  Runner no encontrado: {runner_id}")
            return False

        try:
            container.reload()
            status = container.status
            container_id = DockerUtils.format_container_id(container.id)
            logger.info(f"🐳 Estado: {status} (ID: {container_id})")
        except Exception as e:
            logger.warning(f"⚠️ No se pudo obtener información final: {e}")

        logger.info(f"🛑 Destruyendo runner: {runner_id}")
        success = self.container_manager.stop_container(container)
        
        if success:
            self.active_runners.pop(runner_id, None)
            logger.info(f"✅ Runner destruido: {runner_id}")
        else:
            logger.error(f"❌ No se pudo destruir el runner {runner_id}")
            
        return success

    @handle_lifecycle_errors
    def list_active_runners(self) -> List[Dict]:
        """Lista todos los runners activos."""
        containers = self.container_manager.get_runner_containers()
        return [self.get_runner_status(DockerUtils.get_container_labels(container).get("runner-name", container.id[:12])) 
                for container in containers]

    @handle_lifecycle_errors
    def cleanup_inactive_runners(self) -> int:
        """Purga runners efímeros: destruye todos menos los que tienen workflows activos."""
        logger.info(format_log('CONFIG', 'Limpieza de runners inactivos'))
        
        cleaned_count = 0
        runners_to_remove = []

        for runner_id, container in self.active_runners.items():
            try:
                container.reload()
                
                if not DockerUtils.is_container_running(container):
                    logger.info(f"💀 Runner {runner_id} está muerto, se eliminará")
                    runners_to_remove.append(runner_id)
                    continue
                
                labels = DockerUtils.get_container_labels(container)
                repo = labels.get("repo")
                if repo and self.get_active_workflows_for_repo(repo) == 0:
                    runners_to_remove.append(runner_id)
                        
            except Exception as e:
                logger.error(f"❌ Error analizando runner {runner_id}: {e}")
                runners_to_remove.append(runner_id)

        logger.info(format_log('INFO', f'Análisis: {len(self.active_runners) - len(runners_to_remove)} activos, {len(runners_to_remove)} para eliminar'))

        for runner_id in runners_to_remove:
            try:
                if self.destroy_runner(runner_id):
                    cleaned_count += 1
            except Exception as e:
                logger.error(f"❌ Error eliminando runner {runner_id}: {e}")

        if cleaned_count > 0:
            logger.info(format_log('SUCCESS', f'{cleaned_count} runners purgados'))
        else:
            logger.info(format_log('SUCCESS', 'No hay runners para purgar'))
        
        return cleaned_count

    def start_monitoring(self, cleanup_interval: int = 300):
        """Inicia el monitoreo automático de runners."""
        if self.monitoring:
            logger.warning("Monitoreo ya está activo")
            return

        self.monitoring = True
        self.monitor_thread = threading.Thread(
            target=self._monitor_loop, args=(cleanup_interval,), daemon=True
        )
        self.monitor_thread.start()
        logger.info(format_log('SUCCESS', 'Monitoreo iniciado'))

    def stop_monitoring(self):
        """Detiene el monitoreo automático."""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        logger.info(format_log('SUCCESS', 'Monitoreo detenido'))

    def _monitor_loop(self, cleanup_interval: int):
        """Bucle de monitoreo con descubrimiento y purga automática."""
        purge_interval = int(os.getenv("RUNNER_PURGE_INTERVAL", "300"))
        
        logger.info(format_log('MONITOR', 'Iniciando sistema automático', f'limpieza={purge_interval}s, creación={cleanup_interval}s'))
        
        cycle_count = 0
        while self.monitoring:
            try:
                cycle_count += 1
                logger.info(format_log('MONITOR', f'Ciclo {cycle_count}'))
                
                self.cleanup_inactive_runners()
                self.check_and_create_runners_for_jobs()
                
                active_count = len(self.active_runners)
                logger.info(format_log('INFO', f'Estado: {active_count} runners activos'))
                
                sleep_time = min(purge_interval, cleanup_interval)
                logger.info(format_log('INFO', f'Próximo ciclo en {sleep_time}s'))
                time.sleep(sleep_time)
                
            except Exception as e:
                logger.error(format_log('ERROR', f'Error en ciclo {cycle_count}', str(e)))
                logger.info(format_log('INFO', 'Esperando 60s antes de reintentar'))
                time.sleep(60)

    def check_and_create_runners_for_jobs(self):
        """Descubre automáticamente repos que necesitan runners y los crea."""
        repos = self.get_user_repositories()

        if not repos:
            logger.debug("📁 No se encontraron repositorios para monitorear")
            return

        logger.info(f"🔍 Analizando {len(repos)} repositorios...")
        
        repos_with_runners = 0
        repos_with_jobs = 0
        runners_created = 0

        for repo in repos:
            try:
                if self.repo_uses_self_hosted_runners(repo):
                    repos_with_runners += 1
                    
                    queued_jobs = self.get_queued_jobs_for_repo(repo)

                    if queued_jobs > 0:
                        repos_with_jobs += 1
                        logger.info(f"🔄 {repo}: {queued_jobs} jobs en cola")

                        active_runners = sum(1 for runner_id, container in self.active_runners.items()
                                          if self._runner_belongs_to_repo(container, repo))

                        logger.info(f"📊 {repo}: {active_runners} runners vs {queued_jobs} jobs")

                        if active_runners < queued_jobs:
                            needed = queued_jobs - active_runners
                            logger.info(f"🚀 {repo}: Creando {needed} runners")

                            for i in range(needed):
                                runner_name = f"auto-runner-{int(time.time())}-{i}"
                                try:
                                    runner_id = self.create_runner(
                                        scope="repo", scope_name=repo, runner_name=runner_name
                                    )
                                    runners_created += 1
                                except Exception as e:
                                    logger.error(f"❌ Error creando runner para {repo}: {e}")

            except Exception as e:
                logger.error(f"❌ Error procesando repo {repo}: {e}")
                continue

        logger.info(f"📊 Resumen: {repos_with_runners} repos con runners, {repos_with_jobs} con jobs, {runners_created} runners creados")

    def _runner_belongs_to_repo(self, container: Any, repo: str) -> bool:
        """Verifica si un runner pertenece a un repositorio."""
        try:
            if not DockerUtils.is_container_running(container):
                return False
            
            labels = DockerUtils.get_container_labels(container)
            return labels.get("repo") == repo or labels.get("scope_name") == repo
        except:
            self.active_runners.pop(DockerUtils.get_container_labels(container).get("runner-name", container.id[:12]), None)
            return False

    def get_runner_detailed_info(self, runner_name: str) -> Dict:
        """Obtiene información detallada de un runner usando DockerUtils."""
        try:
            container = self.container_manager.get_runner_container(runner_name)
            if container:
                return DockerUtils.get_container_info(container)
            return {}
        except Exception as e:
            logger.error(f"❌ Error obteniendo información del runner {runner_name}: {e}")
            return {}

    def debug_runner_environment(self, runner_name: str) -> Dict:
        """Obtiene variables de entorno de un runner para debugging."""
        try:
            container = self.container_manager.get_runner_container(runner_name)
            if container:
                return DockerUtils.get_container_environment(container)
            return {}
        except Exception as e:
            logger.error(f"❌ Error obteniendo entorno del runner {runner_name}: {e}")
            return {}

    def get_user_repositories(self) -> List[str]:
        """Obtiene todos los repositorios accesibles del usuario."""
        discovery_mode = os.getenv("DISCOVERY_MODE", "all")

        if discovery_mode == "organization":
            org_repos = self.get_organization_repositories()
            user_repos = self._get_user_repositories()
            return list(set(org_repos + user_repos))
        else:
            return self._get_user_repositories()

    def _get_user_repositories(self) -> List[str]:
        """Obtiene todos los repositorios personales del usuario."""
        repos = []
        page = 1
        per_page = 100

        while True:
            url = f"{self.token_generator.api_base}/user/repos"
            response = requests.get(
                url,
                headers=self.token_generator.headers,
                params={"type": "owner", "page": page, "per_page": per_page},
                timeout=30.0,
            )

            if response.status_code != 200:
                break

            page_repos = response.json()
            if not page_repos:
                break

            repos.extend([repo["full_name"] for repo in page_repos])
            page += 1

        return repos

    def get_organization_repositories(self) -> List[str]:
        """Obtiene todos los repositorios de la organización."""
        return self._get_user_repositories()  # Misma lógica para ambos casos

    def repo_uses_self_hosted_runners(self, repo: str) -> bool:
        """Verifica si un repositorio usa self-hosted runners."""
        try:
            owner, name = repo.split("/")
            url = f"{self.token_generator.api_base}/repos/{owner}/{name}/contents/.github/workflows"
            response = requests.get(url, headers=self.token_generator.headers, timeout=30.0)

            if response.status_code != 200:
                return False

            workflows = response.json()
            for workflow in workflows:
                if workflow.get("name", "").endswith((".yml", ".yaml")):
                    workflow_url = workflow.get("download_url")
                    if workflow_url:
                        workflow_response = requests.get(
                            workflow_url, headers=self.token_generator.headers, timeout=30.0
                        )

                        if workflow_response.status_code == 200:
                            content = workflow_response.text
                            if any(pattern in content for pattern in [
                                "runs-on: self-hosted",
                                'runs-on: ["self-hosted"',
                                'runs-on: [ "self-hosted"'
                            ]):
                                logger.debug(f"Repo {repo} usa self-hosted runners")
                                return True

            return False

        except Exception as e:
            logger.debug(f"Error verificando workflow de {repo}: {e}")
            return False

    def get_active_workflows_for_repo(self, repo: str) -> int:
        """Verifica workflows en ejecución para un repositorio."""
        return len(self._github_api_call(f"repos/{repo}/actions/runs", {"status": "in_progress"}).get("workflow_runs", []))

    def get_queued_jobs_for_repo(self, repo: str) -> int:
        """Verifica jobs en cola para un repositorio."""
        return len(self._github_api_call(f"repos/{repo}/actions/runs", {"status": "queued"}).get("workflow_runs", []))
