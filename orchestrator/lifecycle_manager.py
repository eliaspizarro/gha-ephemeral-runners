import logging
import os
import threading
import time
from typing import Dict, List, Optional

import requests
from container_manager import ContainerManager
from docker.models.containers import Container
from token_generator import TokenGenerator

logger = logging.getLogger(__name__)


class LifecycleManager:
    def __init__(self, github_runner_token: str, runner_image: str):
        self.token_generator = TokenGenerator(github_runner_token)
        self.container_manager = ContainerManager(runner_image)
        self.active_runners: Dict[str, Container] = {}
        self.monitoring = False
        self.monitor_thread: Optional[threading.Thread] = None

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
            runner_name: Nombre único del runner
            runner_group: Grupo del runner
            labels: Labels para el runner

        Returns:
            ID del runner creado

        Raises:
            ValueError: Si los parámetros son inválidos
            Exception: Si falla la creación
        """
        try:
            logger.info(f"Creando runner para {scope}/{scope_name}")

            # Generar token de registro
            registration_token = self.token_generator.generate_registration_token(
                scope, scope_name
            )

            # Crear contenedor
            container = self.container_manager.create_runner_container(
                registration_token=registration_token,
                scope=scope,
                scope_name=scope_name,
                runner_name=runner_name,
                runner_group=runner_group,
                labels=labels,
            )

            # Guardar referencia
            runner_id = container.labels.get("runner-name", container.id[:12])
            self.active_runners[runner_id] = container

            logger.info(f"{runner_id} - INFO - Runner creado exitosamente")
            return runner_id

        except Exception as e:
            logger.error(f"Error creando runner: {e}")
            raise

    def get_runner_status(self, runner_id: str) -> Dict:
        """
        Obtiene el estado de un runner.

        Args:
            runner_id: ID del runner

        Returns:
            Diccionario con estado del runner
        """
        container = self.active_runners.get(runner_id)
        if not container:
            container = self.container_manager.get_container_by_name(runner_id)

        if not container:
            return {"status": "not_found", "runner_id": runner_id}

        try:
            container.reload()
            status = container.status.lower()

            return {
                "status": status,
                "runner_id": runner_id,
                "container_id": container.id[:12],
                "image": container.image.tags[0] if container.image.tags else "unknown",
                "created": container.attrs["Created"],
                "labels": container.labels,
            }
        except Exception as e:
            logger.error(f"Error obteniendo estado del runner {runner_id}: {e}")
            return {"status": "error", "runner_id": runner_id, "error": str(e)}

    def destroy_runner(self, runner_id: str, timeout: int = 30) -> bool:
        """
        Destruye un runner específico.

        Args:
            runner_id: ID del runner a destruir
            timeout: Timeout para detener el contenedor

        Returns:
            True si se destruyó exitosamente
        """
        container = self.active_runners.get(runner_id)
        if not container:
            container = self.container_manager.get_container_by_name(runner_id)

        if not container:
            logger.warning(f"Runner no encontrado: {runner_id}")
            return False

        try:
            success = self.container_manager.stop_container(container, timeout)
            if success:
                self.active_runners.pop(runner_id, None)
                logger.info(f"{runner_id} - INFO - Runner destruido")
            return success
        except Exception as e:
            logger.error(f"Error destruyendo runner {runner_id}: {e}")
            return False

    def list_active_runners(self) -> List[Dict]:
        """
        Lista todos los runners activos.

        Returns:
            Lista de estados de runners activos
        """
        containers = self.container_manager.get_runner_containers()
        runners = []

        for container in containers:
            runner_id = container.labels.get("runner-name", container.id[:12])
            status = self.get_runner_status(runner_id)
            runners.append(status)

        return runners

    def cleanup_inactive_runners(self) -> int:
        """
        Purga runners efímeros: destruye todos menos los que tienen workflows activos.

        Returns:
            Número de runners purgados
        """
        try:
            cleaned_count = 0
            runners_to_keep = set()  # Runners que tienen workflows activos
            runners_to_remove = []

            # FASE 1: Identificar runners en uso
            for runner_id, container in self.active_runners.items():
                try:
                    container.reload()
                    
                    # Contenedores muertos siempre se eliminan
                    if container.status not in ["running", "paused", "restarting"]:
                        runners_to_remove.append(runner_id)
                        continue
                    
                    # Verificar si tiene workflows activos
                    repo = container.labels.get("repo")
                    if repo:
                        active_workflows = self.get_active_workflows_for_repo(repo)
                        if active_workflows > 0:
                            runners_to_keep.add(runner_id)
                            logger.debug(f"Runner {runner_id} en uso: {active_workflows} workflows activos para {repo}")
                        else:
                            runners_to_remove.append(runner_id)
                            
                except Exception as e:
                    logger.error(f"Error verificando runner {runner_id}: {e}")
                    runners_to_remove.append(runner_id)

            # FASE 2: Purgar runners no usados
            for runner_id in runners_to_remove:
                if runner_id not in runners_to_keep:  # Doble seguridad
                    success = self.destroy_runner(runner_id)
                    if success:
                        cleaned_count += 1
                        logger.info(f"Runner {runner_id} purgado (sin workflows activos)")

            if cleaned_count > 0:
                logger.info(f"Purga completada: {cleaned_count} runners eliminados, {len(runners_to_keep)} runners activos mantenidos")

            return cleaned_count

        except Exception as e:
            logger.error(f"Error en purga de runners: {e}")
            return 0

    def start_monitoring(self, cleanup_interval: int = 300):
        """
        Inicia el monitoreo automático de runners.

        Args:
            cleanup_interval: Intervalo de limpieza en segundos
        """
        if self.monitoring:
            logger.warning("Monitoreo ya está activo")
            return

        self.monitoring = True
        self.monitor_thread = threading.Thread(
            target=self._monitor_loop, args=(cleanup_interval,), daemon=True
        )
        self.monitor_thread.start()
        logger.info("Monitoreo iniciado")

    def stop_monitoring(self):
        """Detiene el monitoreo automático."""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        logger.info("Monitoreo detenido")

    def _monitor_loop(self, cleanup_interval: int):
        """Bucle de monitoreo con descubrimiento y purga automática."""
        import os
        
        # Usar intervalo específico para purga (5 minutos por defecto)
        purge_interval = int(os.getenv("RUNNER_PURGE_INTERVAL", "300"))
        
        while self.monitoring:
            try:
                # Purga de runners no usados (cada 5 minutos)
                self.cleanup_inactive_runners()

                # Descubrir y crear runners automáticamente (cada cleanup_interval)
                self.check_and_create_runners_for_jobs()

                # Usar el intervalo más corto para mayor reactividad
                sleep_time = min(purge_interval, cleanup_interval)
                time.sleep(sleep_time)
                
            except Exception as e:
                logger.error(f"Error en bucle de monitoreo: {e}")
                time.sleep(60)  # Esperar antes de reintentar

    def check_and_create_runners_for_jobs(self):
        """Descubre automáticamente repos que necesitan runners y los crea."""
        try:
            # Obtener todos los repos del usuario/organización
            repos = self.get_user_repositories()

            if not repos:
                logger.debug("No se encontraron repositorios para monitorear")
                return

            logger.debug(f"Monitoreando {len(repos)} repositorios")

            for repo in repos:
                try:
                    # Verificar si el repo usa self-hosted runners
                    if self.repo_uses_self_hosted_runners(repo):
                        # Verificar si hay jobs en cola
                        queued_jobs = self.get_queued_jobs_for_repo(repo)

                        if queued_jobs > 0:
                            logger.info(f"Detectados {queued_jobs} jobs en cola para {repo}")

                            # Verificar runners activos para este repo (lógica directa)
                            active_runners = 0
                            for runner_id, container in self.active_runners.items():
                                try:
                                    container.reload()
                                    if container.status == "running":
                                        labels = container.labels
                                        if labels.get("repo") == repo or labels.get("scope_name") == repo:
                                            active_runners += 1
                                except:
                                    # Runner ya no existe, remover de active_runners
                                    self.active_runners.pop(runner_id, None)

                            # Crear runners si faltan
                            if active_runners < queued_jobs:
                                needed = queued_jobs - active_runners
                                logger.info(f"Creando {needed} runners para {repo}")

                                for i in range(needed):
                                    runner_name = f"auto-runner-{int(time.time())}-{i}"
                                    self.create_runner(
                                        scope="repo", scope_name=repo, runner_name=runner_name
                                    )

                    else:
                        logger.debug(f"Repo {repo} no usa self-hosted runners")

                except Exception as e:
                    logger.error(f"Error procesando repo {repo}: {e}")
                    continue

        except Exception as e:
            logger.error(f"Error verificando jobs automáticos: {e}")

    def get_user_repositories(self) -> List[str]:
        """Obtiene todos los repositorios accesibles del usuario."""
        try:
            # Verificar modo de descubrimiento
            discovery_mode = os.getenv("DISCOVERY_MODE", "all")

            if discovery_mode == "organization":
                # Solo repos de organización
                org_repos = self.get_organization_repositories()
                if org_repos:
                    logger.info(f"Modo organización: Encontrados {len(org_repos)} repos")
                    return org_repos
                else:
                    logger.warning("Modo organización: No se encontraron organizaciones")
                    return []

            # Modo 'all' (default): Intentar organización primero, luego personales
            org_repos = self.get_organization_repositories()
            if org_repos:
                logger.info(f"Modo all: Encontrados {len(org_repos)} repos en organización")
                return org_repos

            # Si no hay organización, buscar repos personales
            logger.info("Modo all: Buscando repositorios personales...")
            url = "https://api.github.com/user/repos"
            response = requests.get(url, headers=self.token_generator.headers, timeout=30.0)

            if response.status_code == 200:
                repos = response.json()
                user_repos = [repo["full_name"] for repo in repos]
                logger.info(f"Modo all: Encontrados {len(user_repos)} repos personales")
                return user_repos
            else:
                logger.error(f"Error obteniendo repos personales: {response.status_code}")
                return []

        except Exception as e:
            logger.error(f"Error obteniendo repositorios: {e}")
            return []

    def get_organization_repositories(self) -> List[str]:
        """Intenta obtener repositorios de organización."""
        try:
            # Obtener organizaciones del usuario
            url = "https://api.github.com/user/orgs"
            response = requests.get(url, headers=self.token_generator.headers, timeout=30.0)

            if response.status_code == 200:
                orgs = response.json()
                if orgs:
                    # Usar la primera organización encontrada
                    org_name = orgs[0]["login"]
                    logger.info(f"Detectada organización: {org_name}")

                    # Obtener repos de la organización
                    org_url = f"https://api.github.com/orgs/{org_name}/repos"
                    org_response = requests.get(
                        org_url, headers=self.token_generator.headers, timeout=30.0
                    )

                    if org_response.status_code == 200:
                        repos = org_response.json()
                        org_repos = [repo["full_name"] for repo in repos]
                        return org_repos
                    else:
                        logger.error(
                            f"Error obteniendo repos de {org_name}: {org_response.status_code}"
                        )

            return []

        except Exception as e:
            logger.debug(f"No se encontraron organizaciones: {e}")
            return []

    def repo_uses_self_hosted_runners(self, repo: str) -> bool:
        """Verifica si un repositorio usa runners self-hosted en sus workflows."""
        try:
            owner, name = repo.split("/")

            # Obtener lista de archivos de workflow
            url = f"https://api.github.com/repos/{owner}/{name}/contents/.github/workflows"
            response = requests.get(url, headers=self.token_generator.headers, timeout=30.0)

            if response.status_code == 200:
                workflows = response.json()

                for workflow in workflows:
                    if workflow.get("name", "").endswith((".yml", ".yaml")):
                        # Obtener contenido del workflow
                        workflow_url = workflow.get("download_url")
                        if workflow_url:
                            workflow_response = requests.get(
                                workflow_url, headers=self.token_generator.headers, timeout=30.0
                            )

                            if workflow_response.status_code == 200:
                                content = workflow_response.text
                                # Buscar patrones de self-hosted
                                if (
                                    "runs-on: self-hosted" in content
                                    or 'runs-on: ["self-hosted"' in content
                                    or 'runs-on: [ "self-hosted"' in content
                                ):
                                    logger.debug(f"Repo {repo} usa self-hosted runners")
                                    return True

            return False

        except Exception as e:
            logger.debug(f"Error verificando workflow de {repo}: {e}")
            return False

    def _get_workflow_runs_by_status(self, repo: str, status: str) -> int:
        """Método genérico para obtener workflows por estado (reutilizable)."""
        try:
            owner, name = repo.split("/")

            # Obtener runs del repositorio
            url = f"https://api.github.com/repos/{owner}/{name}/actions/runs"
            response = requests.get(
                url,
                headers=self.token_generator.headers,
                params={"status": status},
                timeout=30.0,
            )

            if response.status_code == 200:
                runs = response.json()
                workflow_runs = runs.get("workflow_runs", [])

                # Filtrar runs que podrían necesitar self-hosted
                job_count = 0
                for run in workflow_runs:
                    # Asumimos que si el repo usa self-hosted, estos jobs lo necesitan
                    job_count += 1

                return job_count

            return 0

        except Exception as e:
            logger.error(f"Error verificando workflows con status '{status}' para {repo}: {e}")
            return 0

    def get_active_workflows_for_repo(self, repo: str) -> int:
        """Verifica workflows en ejecución para un repositorio."""
        return self._get_workflow_runs_by_status(repo, "in_progress")

    def get_queued_jobs_for_repo(self, repo: str) -> int:
        """Verifica jobs en cola para un repositorio."""
        return self._get_workflow_runs_by_status(repo, "queued")
