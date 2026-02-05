"""
Utilitarios para manejo de Docker.
Centraliza operaciones comunes con contenedores.
"""

import logging
import time
from typing import Any, Dict, List, Optional

import docker
from src.utils.helpers import DockerError, ErrorHandler, setup_logger

logger = setup_logger(__name__)


class DockerUtils:
    """Utilitarios centralizados para operaciones Docker."""

    @staticmethod
    def format_container_id(container_id: str) -> str:
        """Formatea ID de contenedor a 12 caracteres."""
        return container_id[:12] if container_id else "unknown"

    @staticmethod
    def get_container_info(container: Any) -> Dict[str, Any]:
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
                "id": self.format_container_id(container.id),
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
            container_id = self.format_container_id(container.id)
            logger.error(f"Error obteniendo información del contenedor {container_id}: {e}")
            return {"id": self.format_container_id(container.id), "status": "error", "error": str(e)}

    @staticmethod
    def is_container_running(container: Any) -> bool:
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
    def get_container_labels(container: Any) -> Dict[str, str]:
        """
        Obtiene labels de un contenedor de forma segura.

        Args:
            container: Contenedor Docker

        Returns:
            Diccionario con labels
        """
        try:
            container.reload()
            labels = container.labels
            return labels if isinstance(labels, dict) else {}
        except Exception:
            return {}

    @staticmethod
    def get_container_environment(container: Any) -> Dict[str, str]:
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
    def wait_for_container(
        container: Any, timeout: int = 30, check_interval: int = 1
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
