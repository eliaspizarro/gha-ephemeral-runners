import datetime
import logging
import os
import socket
import time
from typing import Any, Dict

logger = logging.getLogger(__name__)


class PlaceholderResolver:
    """
    Resuelve placeholders dinamicos en configuraciones de runners.

    Soporta 22 placeholders organizados en categorias:
    - Basicas: scope_name, runner_name, registration_token
    - Tiempo: timestamp, timestamp_iso, timestamp_date, timestamp_time
    - Sistema: hostname, orchestrator_id, docker_network
    - Entorno: orchestrator_port, api_gateway_port, runner_image, registry_url
    - GitHub API: repo_owner, repo_name, repo_full_name, user_login
    """

    def __init__(self):
        self.orchestrator_id = f"orchestrator-{os.getpid()}"

    def resolve_placeholders(self, template: str, context: Dict[str, Any]) -> str:
        """
        Resuelve todos los placeholders en una plantilla.

        Args:
            template: Plantilla con placeholders
            context: Contexto con variables basicas

        Returns:
            Template con placeholders resueltos
        """
        try:
            # Validar contexto minimo
            required_context = ["scope_name", "runner_name", "registration_token"]
            for key in required_context:
                if key not in context:
                    logger.warning(f"Context missing required variable: {key}")
                    context[key] = f"missing_{key}"

            # Construir diccionario de sustituciones
            substitutions = self._build_substitutions(context)

            # Reemplazar placeholders
            result = template
            for placeholder, value in substitutions.items():
                result = result.replace(placeholder, str(value))

            return result

        except Exception as e:
            logger.error(f"Error resolviendo placeholders: {e}")
            return template

    def _build_substitutions(self, context: Dict[str, Any]) -> Dict[str, str]:
        """
        Construye diccionario completo de sustituciones.

        Args:
            context: Contexto basico del runner

        Returns:
            Diccionario de placeholder -> valor
        """
        now = datetime.datetime.utcnow()
        scope_name = context.get("scope_name", "")
        runner_name = context.get("runner_name", "")
        registration_token = context.get("registration_token", "")

        # Variables basicas
        substitutions = {
            "{scope_name}": scope_name,
            "{runner_name}": runner_name,
            "{registration_token}": registration_token,
            # Variables de tiempo
            "{timestamp}": str(int(time.time())),
            "{timestamp_iso}": now.isoformat() + "Z",
            "{timestamp_date}": now.strftime("%Y-%m-%d"),
            "{timestamp_time}": now.strftime("%H-%M-%S"),
            # Variables de sistema
            "{hostname}": socket.gethostname(),
            "{orchestrator_id}": self.orchestrator_id,
            "{docker_network}": os.getenv("DOCKER_NETWORK", "bridge"),
            # Variables de entorno
            "{orchestrator_port}": os.getenv("ORCHESTRATOR_PORT", "8000"),
            "{api_gateway_port}": os.getenv("API_GATEWAY_PORT", "8080"),
            "{runner_image}": os.getenv("RUNNER_IMAGE", "unknown"),
            "{registry_url}": os.getenv("REGISTRY", "unknown"),
            # Variables de GitHub API
            "{repo_owner}": self._extract_repo_owner(scope_name),
            "{repo_name}": self._extract_repo_name(scope_name),
            "{repo_full_name}": scope_name,
            "{user_login}": os.getenv("GITHUB_USER_LOGIN", "unknown"),
        }

        return substitutions

    def _extract_repo_owner(self, scope_name: str) -> str:
        """Extrae el owner del scope_name."""
        if "/" in scope_name:
            return scope_name.split("/")[0]
        return "unknown"

    def _extract_repo_name(self, scope_name: str) -> str:
        """Extrae el nombre del repo del scope_name."""
        if "/" in scope_name:
            return scope_name.split("/")[1]
        return scope_name

    def get_available_placeholders(self) -> Dict[str, str]:
        """
        Retorna lista de placeholders disponibles con descripción.

        Returns:
            Diccionario placeholder -> descripción
        """
        return {
            # Básicas
            "{scope_name}": "Nombre del repositorio/organización (ej: eliaspizarro/hello-ci)",
            "{runner_name}": "Nombre único del runner (ej: ephemeral-runner-abc123)",
            "{registration_token}": "Token efímero de registro",
            # Tiempo
            "{timestamp}": "Timestamp Unix actual",
            "{timestamp_iso}": "Timestamp ISO 8601 (ej: 2024-02-03T18:30:34Z)",
            "{timestamp_date}": "Fecha actual YYYY-MM-DD (ej: 2024-02-03)",
            "{timestamp_time}": "Hora actual HH-MM-SS (ej: 18-30-34)",
            # Sistema
            "{hostname}": "Hostname del sistema (ej: docker2)",
            "{orchestrator_id}": "ID único del orchestrator",
            "{docker_network}": "Red Docker usada",
            # Entorno
            "{orchestrator_port}": "Puerto del orchestrator (ej: 8000)",
            "{api_gateway_port}": "Puerto del API Gateway (ej: 8080)",
            "{runner_image}": "Imagen del runner usada",
            "{registry_url}": "URL del registry",
            # GitHub API
            "{repo_owner}": "Owner del repositorio (ej: eliaspizarro)",
            "{repo_name}": "Nombre del repo sin owner (ej: hello-ci)",
            "{repo_full_name}": "Nombre completo del repo (ej: eliaspizarro/hello-ci)",
            "{user_login}": "Username del token",
        }

    def validate_template(self, template: str) -> Dict[str, Any]:
        """
        Valida una plantilla y retorna información sobre placeholders.

        Args:
            template: Plantilla a validar

        Returns:
            Diccionario con resultado de validación
        """
        import re

        # Encontrar todos los placeholders
        placeholders = re.findall(r"\{[^}]+\}", template)
        available = self.get_available_placeholders()

        valid_placeholders = []
        invalid_placeholders = []

        for placeholder in placeholders:
            if placeholder in available:
                valid_placeholders.append(placeholder)
            else:
                invalid_placeholders.append(placeholder)

        return {
            "template": template,
            "total_placeholders": len(placeholders),
            "valid_placeholders": valid_placeholders,
            "invalid_placeholders": invalid_placeholders,
            "is_valid": len(invalid_placeholders) == 0,
        }
