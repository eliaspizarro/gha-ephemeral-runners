"""
Utilitarios para manejo de Docker.
Centraliza operaciones comunes con contenedores.
"""

import logging
from typing import Any, Dict, List, Optional

from docker.errors import DockerException
from docker.models.containers import Container
from error_handler import DockerError, ErrorHandler
from utils import format_container_id, setup_logger

logger = setup_logger(__name__)


class DockerUtils:
    """Utilitarios centralizados para operaciones Docker."""

    @staticmethod
    def safe_container_operation(
        operation: str, container: Container, operation_func, *args, **kwargs
    ) -> Any:
        """
        Ejecuta operación segura en contenedor con manejo de errores.

        Args:
            operation: Descripción de la operación
            container: Contenedor Docker
            operation_func: Función a ejecutar
            *args: Argumentos para la función
            **kwargs: Argumentos clave para la función

        Returns:
            Resultado de la operación

        Raises:
            DockerError: Si falla la operación
        """
        try:
            return operation_func(container, *args, **kwargs)
        except DockerException as e:
            container_id = format_container_id(container.id)
            error_msg = f"Error en {operation} para contenedor {container_id}: {str(e)}"
            logger.error(error_msg)
            raise DockerError(error_msg)
        except Exception as e:
            container_id = format_container_id(container.id)
            error_msg = f"Error inesperado en {operation} para contenedor {container_id}: {str(e)}"
            logger.error(error_msg)
            raise DockerError(error_msg)

    @staticmethod
    def get_container_info(container: Container) -> Dict[str, Any]:
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
                "id": format_container_id(container.id),
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
            container_id = format_container_id(container.id)
            logger.error(f"Error obteniendo información del contenedor {container_id}: {e}")
            return {"id": format_container_id(container.id), "status": "error", "error": str(e)}

    @staticmethod
    def is_container_running(container: Container) -> bool:
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

    @staticmethod
    def get_container_labels(container: Container) -> Dict[str, str]:
        """
        Obtiene labels de un contenedor de forma segura.

        Args:
            container: Contenedor Docker

        Returns:
            Diccionario con labels
        """
        try:
            container.reload()
            return container.labels or {}
        except Exception:
            return {}

    @staticmethod
    def get_container_environment(container: Container) -> Dict[str, str]:
        """
        Obtiene variables de entorno de un contenedor.

        Args:
            container: Contenedor Docker

        Returns:
            Diccionario con variables de entorno
        """
        try:
            container.reload()
            return container.attrs.get("Config", {}).get("Env", [])
        except Exception:
            return {}

    @staticmethod
    def format_container_name(prefix: str, name: str) -> str:
        """
        Formatea nombre de contenedor de forma consistente.

        Args:
            prefix: Prefijo del nombre
            name: Nombre base

        Returns:
            Nombre formateado
        """
        import re

        # Limpiar nombre
        clean_name = re.sub(r"[^a-zA-Z0-9_-]", "", name)

        if not clean_name:
            clean_name = "unnamed"

        return f"{prefix}-{clean_name}"

    @staticmethod
    def create_container_labels(
        runner_name: str,
        scope: str,
        scope_name: str,
        additional_labels: Optional[Dict[str, str]] = None,
    ) -> Dict[str, str]:
        """
        Crea labels estándar para contenedores de runners.

        Args:
            runner_name: Nombre del runner
            scope: Alcance (repo/org)
            scope_name: Nombre del repositorio/organización
            additional_labels: Labels adicionales (opcional)

        Returns:
            Diccionario con labels
        """
        labels = {
            "gha-ephemeral": "true",
            "runner-name": runner_name,
            "scope": scope,
            "scope_name": scope_name,
            "repo": scope_name,
        }

        if additional_labels:
            labels.update(additional_labels)

        return labels

    @staticmethod
    def validate_container_name(name: str) -> str:
        """
        Valida y normaliza nombre de contenedor.

        Args:
            name: Nombre a validar

        Returns:
            Nombre validado

        Raises:
            ValueError: Si el nombre es inválido
        """
        import re

        if not name:
            raise ValueError("El nombre del contenedor no puede estar vacío")

        # Limpiar caracteres inválidos
        clean_name = re.sub(r"[^a-zA-Z0-9_-]", "", name)

        if not clean_name:
            raise ValueError("El nombre contiene caracteres inválidos")

        if len(clean_name) > 64:
            raise ValueError("El nombre es demasiado largo (máximo 64 caracteres)")

        return clean_name

    @staticmethod
    def get_container_logs(container: Container, tail: int = 100) -> str:
        """
        Obtiene logs de un contenedor.

        Args:
            container: Contenedor Docker
            tail: Número de líneas a obtener

        Returns:
            Logs del contenedor
        """
        try:
            logs = container.logs(tail=tail, timestamps=True)
            return logs.decode("utf-8") if isinstance(logs, bytes) else str(logs)
        except Exception as e:
            container_id = format_container_id(container.id)
            logger.error(f"Error obteniendo logs del contenedor {container_id}: {e}")
            return f"Error obteniendo logs: {str(e)}"

    @staticmethod
    def wait_for_container(
        container: Container, timeout: int = 30, check_interval: int = 1
    ) -> bool:
        """
        Espera a que un contenedor esté listo.

        Args:
            container: Contenedor Docker
            timeout: Tiempo máximo de espera
            check_interval: Intervalo de verificación

        Returns:
            True si el contenedor está listo, False si timeout
        """
        import time

        start_time = time.time()

        while time.time() - start_time < timeout:
            try:
                container.reload()
                if container.status.lower() == "running":
                    return True
                elif container.status.lower() in ["exited", "dead"]:
                    return False
                time.sleep(check_interval)
            except Exception:
                time.sleep(check_interval)

        return False
