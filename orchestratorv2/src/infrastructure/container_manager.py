"""
Implementación de gestión de contenedores Docker.

Rol: Gestión completa de contenedores Docker para runners.
Crea, detiene, elimina y monitorea contenedores.
Implementa el contrato ContainerManager del dominio.

Depende de: docker library, configuración de imagen.
"""

import logging
import time
import uuid
from typing import Any, Dict, List, Optional

# Docker imports - se manejarán cuando Docker esté disponible
try:
    import docker
    from docker.models.containers import Container
    DOCKER_AVAILABLE = True
except ImportError:
    docker = None
    Container = None
    DOCKER_AVAILABLE = False

from ..shared.infrastructure_exceptions import DockerError
from ..shared.logging_utils import log_operation_start, log_operation_success, log_operation_error, mask_sensitive_data
from ..shared.validation_utils import validate_runner_name, validate_timeout
from ..shared.constants import DEFAULT_CONTAINER_LABELS, RUNNER_CREATION_TIMEOUT, DEFAULT_TIMEOUT
from .environment_setup import EnvironmentSetup

logger = logging.getLogger(__name__)


class ContainerManager:
    """Gestor de contenedores Docker para runners efímeros."""
    
    def __init__(self, runner_image: str):
        """
        Inicializa gestor de contenedores.
        
        Args:
            runner_image: Imagen Docker para runners
        """
        if not DOCKER_AVAILABLE:
            raise DockerError("Docker no está disponible. Instale docker SDK para Python.")
        
        try:
            self.client = docker.from_env()
            self.runner_image = runner_image
            self.environment_setup = EnvironmentSetup(runner_image)
        except Exception as e:
            raise DockerError(f"Error inicializando Docker: {e}")
    
    def test_connection(self):
        """Prueba la conexión con Docker."""
        try:
            self.client.ping()
            return True
        except Exception as e:
            raise DockerError(f"Error conectando a Docker: {e}")
    
    def create_runner_container(
        self,
        registration_token: str,
        scope: str,
        scope_name: str,
        runner_name: Optional[str] = None,
        runner_group: Optional[str] = None,
        labels: Optional[List[str]] = None,
    ) -> Container:
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
        operation = "create_runner_container"
        
        try:
            # Validar y generar nombre del runner
            if not runner_name:
                runner_name = f"ephemeral-runner-{uuid.uuid4().hex[:8]}"
            
            runner_name = validate_runner_name(runner_name)
            
            # Usar Environment Setup para obtener variables de entorno
            environment = self.environment_setup.process_environment_variables(
                scope_name=scope_name,
                runner_name=runner_name,
                registration_token=registration_token,
            )
            
            # Agregar variables adicionales
            if runner_group:
                environment["RUNNER_GROUP"] = runner_group
            
            if labels:
                environment["RUNNER_LABELS"] = ",".join(labels)
            
            # Log de variables que se enviarán al contenedor
            logger.info(f"{runner_name} - Variables de entorno ({len(environment)}):")
            for key, value in environment.items():
                # Ocultar tokens en logs por seguridad
                if "TOKEN" in key:
                    masked_value = mask_sensitive_data(value)
                    logger.info(f"{runner_name} - {key}: {masked_value}")
                else:
                    logger.info(f"{runner_name} - {key}: {value}")
            
            # Crear nombre de contenedor
            container_name = self._format_container_name("gha-runner", runner_name)
            
            # Crear labels estándar
            container_labels = self._create_container_labels(
                runner_name=runner_name, scope=scope, scope_name=scope_name
            )
            
            # Agregar labels adicionales
            if labels:
                for label in labels:
                    container_labels[f"custom-label-{label}"] = label
            
            log_operation_start(logger, operation, 
                               runner_name=runner_name, scope=scope, scope_name=scope_name,
                               container_name=container_name)
            
            # Crear contenedor
            container = self.client.containers.run(
                self.runner_image,
                name=container_name,
                environment=environment,
                detach=True,
                labels=container_labels,
            )
            
            log_operation_success(logger, operation, 
                                 runner_name=runner_name, container_id=container.id[:12],
                                 container_name=container_name)
            
            # Esperar y mostrar logs iniciales
            time.sleep(3)
            self._log_container_output(container, runner_name)
            
            return container
            
        except Exception as e:
            log_operation_error(logger, operation, e, 
                                 runner_name=runner_name, scope=scope, scope_name=scope_name)
            raise DockerError(f"Error creando contenedor runner: {e}")
    
    def stop_container(self, container: Container, timeout: int = DEFAULT_TIMEOUT) -> bool:
        """
        Detiene un contenedor de runner.
        
        Args:
            container: Contenedor a detener
            timeout: Timeout para detener
        
        Returns:
            True si se detuvo exitosamente
        """
        operation = "stop_container"
        runner_name = container.labels.get("runner-name", "unknown")
        
        try:
            log_operation_start(logger, operation, runner_name=runner_name, container_id=container.id[:12])
            
            # Verificar que el contenedor existe antes de detenerlo
            try:
                container.reload()
                if container.status not in ["running", "paused", "restarting"]:
                    logger.info(f"{runner_name} - Contenedor ya no está corriendo: {container.status}")
                    log_operation_success(logger, operation, runner_name=runner_name, already_stopped=True)
                    return True
            except Exception:
                logger.warning(f"{runner_name} - Contenedor ya no existe")
                log_operation_success(logger, operation, runner_name=runner_name, already_stopped=True)
                return True
            
            # Mostrar logs finales antes de detener
            self._log_container_output(container, runner_name)
            
            container.stop(timeout=timeout)
            log_operation_success(logger, operation, runner_name=runner_name, container_id=container.id[:12])
            return True
            
        except Exception as e:
            log_operation_error(logger, operation, e, runner_name=runner_name, container_id=container.id[:12])
            raise DockerError(f"Error deteniendo contenedor: {e}")
    
    def remove_container(self, container: Container, timeout: int = DEFAULT_TIMEOUT) -> bool:
        """
        Elimina un contenedor de runner.
        
        Args:
            container: Contenedor a eliminar
            timeout: Timeout para eliminar
        
        Returns:
            True si se eliminó exitosamente
        """
        operation = "remove_container"
        runner_name = container.labels.get("runner-name", "unknown")
        
        try:
            log_operation_start(logger, operation, runner_name=runner_name, container_id=container.id[:12])
            
            # Detener primero si está corriendo
            if container.status == "running":
                self.stop_container(container, timeout)
            
            container.remove(force=True)
            log_operation_success(logger, operation, runner_name=runner_name, container_id=container.id[:12])
            return True
            
        except Exception as e:
            log_operation_error(logger, operation, e, runner_name=runner_name, container_id=container.id[:12])
            raise DockerError(f"Error eliminando contenedor: {e}")
    
    def get_runner_containers(self) -> List[Container]:
        """
        Obtiene todos los contenedores de runners efímeros activos.
        
        Returns:
            Lista de contenedores activos
        """
        operation = "get_runner_containers"
        
        try:
            log_operation_start(logger, operation)
            
            containers = self.client.containers.list(filters={"label": "gha-ephemeral=true"})
            
            log_operation_success(logger, operation, count=len(containers))
            return containers
            
        except Exception as e:
            log_operation_error(logger, operation, e)
            raise DockerError(f"Error listando contenedores runners: {e}")
    
    def get_container_by_name(self, runner_name: str) -> Optional[Container]:
        """
        Busca un contenedor por el nombre del runner.
        
        Args:
            runner_name: Nombre del runner
        
        Returns:
            Contenedor encontrado o None
        """
        operation = "get_container_by_name"
        
        try:
            log_operation_start(logger, operation, runner_name=runner_name)
            
            containers = self.client.containers.list(
                all=True, filters={"label": f"runner-name={runner_name}"}
            )
            
            container = containers[0] if containers else None
            
            if container:
                log_operation_success(logger, operation, runner_name=runner_name, container_id=container.id[:12])
            else:
                log_operation_success(logger, operation, runner_name=runner_name, found=False)
            
            return container
            
        except Exception as e:
            log_operation_error(logger, operation, e, runner_name=runner_name)
            raise DockerError(f"Error buscando contenedor por nombre: {e}")
    
    def get_container_info(self, container: Container) -> Dict[str, Any]:
        """
        Obtiene información completa de un contenedor.
        
        Args:
            container: Contenedor Docker
        
        Returns:
            Diccionario con información del contenedor
        """
        try:
            container.reload()  # Actualizar estado
            
            return {
                "id": container.id[:12],
                "name": container.name,
                "status": container.status,
                "image": container.image.tags[0] if container.image.tags else "unknown",
                "created": container.attrs["Created"],
                "labels": container.labels,
                "ports": container.ports,
                "mounts": container.attrs.get("Mounts", []),
                "networks": container.attrs.get("NetworkSettings", {}).get("Networks", {}),
                "ip_address": container.attrs.get("NetworkSettings", {}).get("IPAddress", ""),
                "state": container.attrs.get("State", {}),
            }
        except Exception as e:
            logger.error(f"Error obteniendo información del contenedor {container.id[:12]}: {e}")
            return {"id": container.id[:12], "status": "error", "error": str(e)}
    
    def is_container_running(self, container: Container) -> bool:
        """
        Verifica si un contenedor está corriendo.
        
        Args:
            container: Contenedor Docker
        
        Returns:
            True si está corriendo, False en caso contrario
        """
        try:
            container.reload()
            return container.status.lower() == "running"
        except Exception:
            return False
    
    def get_container_logs(self, container: Container, tail: int = 50) -> str:
        """
        Obtiene logs de un contenedor de runner.
        
        Args:
            container: Contenedor Docker
            tail: Número de líneas a obtener
        
        Returns:
            Logs del contenedor
        """
        try:
            logs = container.logs(tail=tail, timestamps=True)
            return logs.decode('utf-8') if logs else ""
        except Exception as e:
            logger.error(f"Error obteniendo logs del contenedor {container.id[:12]}: {e}")
            return "Error obteniendo logs"
    
    def _format_container_name(self, prefix: str, runner_name: str) -> str:
        """
        Formatea nombre de contenedor.
        
        Args:
            prefix: Prefijo para el nombre
            runner_name: Nombre del runner
        
        Returns:
            Nombre formateado
        """
        clean_name = runner_name.replace("_", "-").replace(" ", "-")
        return f"{prefix}-{clean_name}"
    
    def _create_container_labels(
        self, runner_name: str, scope: str, scope_name: str
    ) -> Dict[str, str]:
        """
        Crea labels estándar para contenedores de runners.
        
        Args:
            runner_name: Nombre del runner
            scope: 'repo' u 'org'
            scope_name: Nombre del repositorio u organización
        
        Returns:
            Diccionario de labels
        """
        labels = DEFAULT_CONTAINER_LABELS.copy()
        labels.update({
            "runner-name": runner_name,
            "scope": scope,
            "scope_name": scope_name,
            "repo": scope_name,  # Para compatibilidad
        })
        return labels
    
    def _log_container_output(self, container: Container, runner_name: str) -> None:
        """
        Muestra logs del contenedor en formato estándar.
        
        Args:
            container: Contenedor Docker
            runner_name: Nombre del runner
        """
        try:
            logs = self.get_container_logs(container, tail=20)
            if logs and logs != "Error obteniendo logs":
                logger.info(f"{runner_name} - Logs del contenedor:")
                for line in logs.split("\n"):
                    if line.strip():
                        logger.info(f"{runner_name} - {line.strip()}")
        except Exception as e:
            logger.error(f"{runner_name} - Error obteniendo logs: {e}")
