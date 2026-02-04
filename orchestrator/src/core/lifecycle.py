import logging
import os
import threading
import time
from typing import Any, Dict, List, Optional

import requests
from src.core.container import ContainerManager
from src.services.tokens import TokenGenerator

logger = logging.getLogger(__name__)


class LifecycleManager:
    def __init__(self, github_runner_token: str, runner_image: str):
        self.token_generator = TokenGenerator(github_runner_token)
        self.container_manager = ContainerManager(runner_image)
        self.active_runners: Dict[str, Any] = {}
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
            runner_name: Nombre único del runner (opcional)
            runner_group: Grupo del runner (opcional)
            labels: Labels para el runner (opcional)
            
        Returns:
            ID del runner creado
        """
        try:
            logger.info(f" INICIANDO CREACIÓN DE RUNNER")
            logger.info(f" Scope: {scope}/{scope_name}")
            logger.info(f"  Runner Name: {runner_name or 'auto-generado'}")
            logger.info(f"  Runner Group: {runner_group or 'default'}")
            logger.info(f"  Labels: {labels or []}")

            # Generar token de registro
            logger.info(" Generando token de registro...")
            registration_token = self.token_generator.generate_registration_token(
                scope, scope_name
            )
            logger.info(" Token de registro generado")

            # Crear contenedor
            logger.info(" Creando contenedor Docker...")
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

            logger.info(f" RUNNER CREADO EXITOSAMENTE")
            logger.info(f" Runner ID: {runner_id}")
            logger.info(f" Container ID: {container.id[:12]}")
            logger.info(f" Total runners activos: {len(self.active_runners)}")
            
            return runner_id

        except Exception as e:
            logger.error(f" Error creando runner: {e}")
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

    def destroy_runner(self, runner_id: str) -> bool:
        """
        Destruye un runner efímero.

        Args:
            runner_id: ID del runner a destruir

        Returns:
            True si se destruyó exitosamente
        """
        try:
            logger.info(f"🗑️  INICIANDO DESTRUCCIÓN DEL RUNNER: {runner_id}")
            
            container = self.active_runners.get(runner_id)
            if not container:
                container = self.container_manager.get_container_by_name(runner_id)

            if not container:
                logger.warning(f"⚠️  Runner no encontrado: {runner_id}")
                return False

            try:
                # Obtener información antes de destruir
                container.reload()
                logger.info(f"🐳 Estado actual: {container.status}")
                logger.info(f"🆔 Container ID: {container.id[:12]}")
                
                # Mostrar logs finales antes de destruir
                logger.info("📋 Logs finales del runner:")
                self.container_manager.log_container_output(container, runner_id)
                
            except Exception as e:
                logger.warning(f"⚠️  No se pudo obtener información final del contenedor: {e}")

            logger.info(f"🛑 Deteniendo contenedor del runner {runner_id}...")
            success = self.container_manager.stop_container(container)
            
            if success:
                self.active_runners.pop(runner_id, None)
                logger.info(f"✅ RUNNER DESTRUIDO EXITOSAMENTE: {runner_id}")
                logger.info(f"📊 Runners activos restantes: {len(self.active_runners)}")
            else:
                logger.error(f"❌ No se pudo destruir el runner {runner_id}")
                
            return success
            
        except Exception as e:
            logger.error(f"❌ Error destruyendo runner {runner_id}: {e}")
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
            logger.info("🧹 INICIANDO LIMPIEZA DE RUNNERS INACTIVOS")
            logger.info(f"📊 Runners activos actuales: {len(self.active_runners)}")
            
            cleaned_count = 0
            runners_to_keep = set()  # Runners que tienen workflows activos
            runners_to_remove = []

            # FASE 1: Identificar runners en uso
            logger.info("🔍 FASE 1: Analizando runners activos...")
            for runner_id, container in self.active_runners.items():
                try:
                    container.reload()
                    logger.info(f"📋 Analizando runner: {runner_id} (estado: {container.status})")
                    
                    # Contenedores muertos siempre se eliminan
                    if container.status not in ["running", "paused", "restarting"]:
                        logger.info(f"💀 Runner {runner_id} está muerto, se eliminará")
                        runners_to_remove.append(runner_id)
                        continue
                    
                    # Verificar si tiene workflows activos
                    repo = container.labels.get("repo")
                    if repo:
                        active_workflows = self.get_active_workflows_for_repo(repo)
                        logger.info(f"🔄 Runner {runner_id} tiene {active_workflows} workflows activos en {repo}")
                        
                        if active_workflows > 0:
                            runners_to_keep.add(runner_id)
                            logger.info(f"✅ Runner {runner_id} se mantiene (workflows activos)")
                        else:
                            runners_to_remove.append(runner_id)
                            logger.info(f"⏸️  Runner {runner_id} se eliminará (sin workflows activos)")
                    else:
                        logger.info(f"⚠️  Runner {runner_id} no tiene repo configurado, se eliminará")
                        runners_to_remove.append(runner_id)
                        
                except Exception as e:
                    logger.error(f"❌ Error analizando runner {runner_id}: {e}")
                    runners_to_remove.append(runner_id)

            logger.info(f"📊 Resultados del análisis:")
            logger.info(f"  ✅ Runners a mantener: {len(runners_to_keep)}")
            logger.info(f"  🗑️  Runners a eliminar: {len(runners_to_remove)}")

            # FASE 2: Eliminar runners inactivos
            logger.info("🗑️  FASE 2: Eliminando runners inactivos...")
            for runner_id in runners_to_remove:
                try:
                    logger.info(f"🛑 Eliminando runner: {runner_id}")
                    if self.destroy_runner(runner_id):
                        cleaned_count += 1
                        logger.info(f"✅ Runner {runner_id} eliminado")
                    else:
                        logger.warning(f"⚠️  No se pudo eliminar runner {runner_id}")
                except Exception as e:
                    logger.error(f"❌ Error eliminando runner {runner_id}: {e}")

            logger.info(f"🎉 LIMPIEZA COMPLETADA")
            logger.info(f"📊 Runners eliminados: {cleaned_count}")
            logger.info(f"📊 Runners activos restantes: {len(self.active_runners)}")
            
            return cleaned_count
            
        except Exception as e:
            logger.error(f"❌ Error en limpieza de runners: {e}")
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
        
        logger.info(f"🔄 INICIANDO BUCLE DE MONITOREO")
        logger.info(f"⏰ Intervalo de limpieza: {purge_interval} segundos")
        logger.info(f"⏰ Intervalo de creación: {cleanup_interval} segundos")
        logger.info(f"🔍 Modo de descubrimiento: {os.getenv('DISCOVERY_MODE', 'all')}")
        
        while self.monitoring:
            try:
                logger.info("🔄 === CICLO DE MONITOREO ===")
                
                # Purga de runners no usados (cada 5 minutos)
                logger.info("🧹 Ejecutando limpieza de runners inactivos...")
                purged = self.cleanup_inactive_runners()
                if purged > 0:
                    logger.info(f"🗑️  {purged} runners purgados")
                else:
                    logger.info("✅ No hay runners para purgar")

                # Descubrir y crear runners automáticamente (cada cleanup_interval)
                logger.info("🔍 Buscando repositorios que necesitan runners...")
                self.check_and_create_runners_for_jobs()

                # Usar el intervalo más corto para mayor reactividad
                sleep_time = min(purge_interval, cleanup_interval)
                logger.info(f"⏳ Esperando {sleep_time} segundos para próximo ciclo...")
                logger.info("🔄 === FIN DEL CICLO DE MONITOREO ===")
                time.sleep(sleep_time)
                
            except Exception as e:
                logger.error(f"❌ Error en bucle de monitoreo: {e}")
                logger.info("⏳ Esperando 60 segundos antes de reintentar...")
                time.sleep(60)  # Esperar antes de reintentar

    def check_and_create_runners_for_jobs(self):
        """Descubre automáticamente repos que necesitan runners y los crea."""
        try:
            logger.info("🔍 DESCUBRIENDO REPOSITORIOS PARA RUNNERS")
            
            # Obtener todos los repos del usuario/organización
            repos = self.get_user_repositories()

            if not repos:
                logger.info("📁 No se encontraron repositorios para monitorear")
                return

            logger.info(f"📁 Encontrados {len(repos)} repositorios para monitorear")

            for repo in repos:
                try:
                    logger.info(f"📂 Analizando repositorio: {repo}")
                    
                    # Verificar si el repo usa self-hosted runners
                    if self.repo_uses_self_hosted_runners(repo):
                        logger.info(f"✅ {repo} usa self-hosted runners")
                        
                        # Verificar si hay jobs en cola
                        queued_jobs = self.get_queued_jobs_for_repo(repo)

                        if queued_jobs > 0:
                            logger.info(f"🔄 {repo}: {queued_jobs} jobs en cola")

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
                                    logger.warning(f"⚠️  Runner {runner_id} ya no existe, removiendo de lista")
                                    self.active_runners.pop(runner_id, None)

                            logger.info(f"📊 {repo}: {active_runners} runners activos vs {queued_jobs} jobs en cola")

                            # Crear runners si faltan
                            if active_runners < queued_jobs:
                                needed = queued_jobs - active_runners
                                logger.info(f"🚀 {repo}: Creando {needed} runners adicionales")

                                for i in range(needed):
                                    runner_name = f"auto-runner-{int(time.time())}-{i}"
                                    try:
                                        logger.info(f"🐳 Creando runner {runner_name} para {repo}...")
                                        runner_id = self.create_runner(
                                            scope="repo", scope_name=repo, runner_name=runner_name
                                        )
                                        logger.info(f"✅ Runner creado: {runner_id}")
                                    except Exception as e:
                                        logger.error(f"❌ Error creando runner {runner_name} para {repo}: {e}")
                            else:
                                logger.info(f"✅ {repo}: Suficientes runners activos")

                    else:
                        logger.info(f"⏸️  {repo}: No usa self-hosted runners")

                except Exception as e:
                    logger.error(f"❌ Error procesando repo {repo}: {e}")
                    continue

        except Exception as e:
            logger.error(f"❌ Error verificando jobs automáticos: {e}")

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
