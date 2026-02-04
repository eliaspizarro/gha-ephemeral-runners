import logging
import os
import time
import uuid
from typing import Any, Dict, List, Optional

import docker
from src.services.docker import DockerError, DockerUtils
from src.services.environment import EnvironmentManager
from src.utils.helpers import ErrorHandler, format_container_id, validate_runner_name

logger = logging.getLogger(__name__)


class ContainerManager:
    def __init__(self, runner_image: str):
        self.client = docker.from_env()
        self.runner_image = runner_image
        self.environment_manager = EnvironmentManager(runner_image)

    def create_runner_container(
        self,
        registration_token: str,
        scope: str,
        scope_name: str,
        runner_name: Optional[str] = None,
        runner_group: Optional[str] = None,
        labels: Optional[List[str]] = None,
    ) -> Any:
        """
        Crea un contenedor Docker para un runner efímero.

        Args:
            registration_token: Token de registro temporal
            scope: 'repo' u 'org'
            scope_name: Nombre del repositorio u organización
            runner_name: Nombre único del runner (opcional)
            runner_group: Grupo del runner (opcional)
            labels: Labels para el runner (opcional)

        Returns:
            Contenedor Docker creado

        Raises:
            DockerError: Si falla la creación del contenedor
        """
        try:
            logger.info("🐳 CONFIGURANDO CONTENEDOR DOCKER")
            
            # Validar y generar nombre del runner
            if not runner_name:
                runner_name = f"ephemeral-runner-{uuid.uuid4().hex[:8]}"

            runner_name = validate_runner_name(runner_name)

            # Preparar variables de entorno
            environment = self.environment_manager.process_environment_variables(
                scope_name=scope_name,
                runner_name=runner_name,
                registration_token=registration_token,
            )
            
            logger.info("📋 Variables de entorno configuradas:")
            for key, value in environment.items():
                if 'TOKEN' in key:
                    logger.info(f"  {key}: ***CONFIGURADO***")
                else:
                    logger.info(f"  {key}: {value}")

            if runner_group:
                environment["RUNNER_GROUP"] = runner_group

            if labels:
                environment["RUNNER_LABELS"] = ",".join(labels)

            # Crear nombre de contenedor
            container_name = DockerUtils.format_container_name("gha-runner", runner_name)
            logger.info(f"🏷️  Nombre del contenedor: {container_name}")

            # Crear labels estándar
            container_labels = DockerUtils.create_container_labels(
                runner_name=runner_name, scope=scope, scope_name=scope_name
            )
            logger.info(f"🏷️  Labels del contenedor: {container_labels}")

            logger.info(f"🚀 Creando contenedor con imagen: {self.runner_image}")
            
            # Crear contenedor
            container = self.client.containers.run(
                self.runner_image,
                name=container_name,
                environment=environment,
                detach=True,
                labels=container_labels,
            )

            logger.info(f"✅ Contenedor creado: {format_container_id(container.id)}")

            # Esperar y mostrar logs iniciales
            logger.info("⏳ Esperando inicialización del contenedor...")
            time.sleep(3)
            
            logger.info("📋 Logs iniciales del contenedor:")
            self.log_container_output(container, runner_name)

            logger.info(f"🎉 CONTENEDOR RUNNER CREADO EXITOSAMENTE")
            return container

        except Exception as e:
            logger.error(f"❌ Error creando contenedor runner: {e}")
            raise ErrorHandler.handle_error(e, "creando contenedor runner", logger)

    def get_runner_containers(self) -> List[Any]:
        """
        Obtiene todos los contenedores de runners efímeros activos.

        Returns:
            Lista de contenedores activos
        """
        try:
            containers = self.client.containers.list(filters={"label": "gha-ephemeral=true"})
            return containers
        except Exception as e:
            raise ErrorHandler.handle_error(e, "listando contenedores runners", logger)

    def get_container_by_name(self, runner_name: str) -> Optional[Any]:
        """
        Busca un contenedor por el nombre del runner.

        Args:
            runner_name: Nombre del runner

        Returns:
            Contenedor encontrado o None
        """
        try:
            containers = self.client.containers.list(
                all=True, filters={"label": f"runner-name={runner_name}"}
            )
            return containers[0] if containers else None
        except Exception as e:
            raise ErrorHandler.handle_error(e, "buscando contenedor por nombre", logger)

    def stop_container(self, container: Any, timeout: int = 30) -> bool:
        """
        Detiene un contenedor de runner.

        Args:
            container: Contenedor a detener
            timeout: Timeout para detener

        Returns:
            True si se detuvo exitosamente
        """
        runner_name = container.labels.get("runner-name", "unknown")

        try:
            logger.info(f"{runner_name} - INFO - Deteniendo contenedor")

            # Verificar que el contenedor existe antes de detenerlo
            try:
                container.reload()
                if container.status not in ["running", "paused", "restarting"]:
                    logger.info(
                        f"{runner_name} - INFO - Contenedor ya no está corriendo: {container.status}"
                    )
                    return True
            except Exception:
                logger.warning(f"{runner_name} - WARNING - Contenedor ya no existe")
                return True

            # Mostrar logs finales antes de detener
            self.log_container_output(container, runner_name)

            container.stop(timeout=timeout)
            logger.info(f"{runner_name} - INFO - Contenedor detenido exitosamente")
            return True
        except Exception as e:
            raise ErrorHandler.handle_error(e, "deteniendo contenedor", logger)

    def get_container_logs(self, container: Any, tail: int = 50) -> str:
        """
        Obtiene logs de un contenedor de runner.

        Args:
            container: Contenedor Docker
            tail: Número de líneas a obtener

        Returns:
            Logs del contenedor
        """
        return DockerUtils.get_container_logs(container, tail)

    def log_container_output(self, container: Any, runner_name: str) -> None:
        """
        Muestra logs del contenedor en formato estándar.

        Args:
            container: Contenedor Docker
            runner_name: Nombre del runner
        """
        try:
            logger.info(f"📋 OBTENIENDO LOGS DEL CONTENEDOR: {runner_name}")
            
            # Obtener información del contenedor primero
            try:
                container.reload()
                logger.info(f"🐳 Estado del contenedor: {container.status}")
                logger.info(f"🆔 ID del contenedor: {format_container_id(container.id)}")
                logger.info(f"🏷️  Imagen: {container.image.tags[0] if container.image.tags else 'unknown'}")
            except Exception as e:
                logger.warning(f"⚠️  No se pudo obtener información del contenedor: {e}")
            
            # Obtener logs
            logs = self.get_container_logs(container, tail=50)  # Aumentado de 20 a 50
            
            if logs and logs != "Error obteniendo logs":
                logger.info(f"📄 LOGS DEL CONTENEDOR ({len(logs.split())} líneas):")
                logger.info("=" * 60)
                for line in logs.split("\n"):
                    if line.strip():
                        logger.info(f"  {runner_name} | {line.strip()}")
                logger.info("=" * 60)
            else:
                logger.warning(f"⚠️  No se pudieron obtener logs del contenedor {runner_name}")
                
        except Exception as e:
            logger.error(f"❌ Error obteniendo logs del contenedor {runner_name}: {e}")

    def get_container_info(self, container: Any) -> Dict[str, Any]:
        """
        Obtiene información completa de un contenedor.

        Args:
            container: Contenedor Docker

        Returns:
            Diccionario con información del contenedor
        """
        return DockerUtils.get_container_info(container)

    def is_container_running(self, container: Any) -> bool:
        """
        Verifica si un contenedor está corriendo.

        Args:
            container: Contenedor Docker

        Returns:
            True si está corriendo, False en caso contrario
        """
        return DockerUtils.is_container_running(container)
