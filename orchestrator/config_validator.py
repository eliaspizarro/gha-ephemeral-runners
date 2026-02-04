import logging
import os
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ConfigValidator:
    """
    Validador de configuración para el sistema de runners efímeros.

    Valida variables de entorno, configuración de imágenes y placeholders.
    """

    def __init__(self):
        self.required_env_vars = ["GITHUB_RUNNER_TOKEN", "RUNNER_IMAGE"]

        self.optional_env_vars = [
            "AUTO_CREATE_RUNNERS",
            "RUNNER_CHECK_INTERVAL",
        ]

        # Sin hardcodeo - cualquier imagen es soportada vía runnerenv_

    def validate_environment(self) -> Dict[str, Any]:
        """
        Valida todas las variables de entorno del sistema.

        Returns:
            Diccionario con resultado de validación
        """
        results = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "missing_required": [],
            "invalid_optional": [],
            "runner_env_vars": {},
        }

        # Validar variables obligatorias
        for var in self.required_env_vars:
            value = os.getenv(var)
            if not value:
                results["missing_required"].append(var)
                results["valid"] = False
            else:
                # Validaciones específicas
                if var == "GITHUB_RUNNER_TOKEN":
                    if not self._validate_github_token(value):
                        results["invalid_optional"].append(f"{var}: formato inválido")
                        results["valid"] = False
                elif var == "RUNNER_IMAGE":
                    if not self._validate_runner_image(value):
                        results["invalid_optional"].append(f"{var}: imagen no soportada")
                        results["warnings"].append(
                            f"Imagen {value} no está en la lista de soportadas"
                        )

        # Validar variables opcionales
        for var in self.optional_env_vars:
            value = os.getenv(var)
            if value:
                # Validaciones específicas para opcionales
                if var == "RUNNER_CHECK_INTERVAL":
                    try:
                        interval = int(value)
                        if interval < 10:
                            results["invalid_optional"].append(f"{var}: debe ser >= 10 segundos")
                            results["valid"] = False
                    except ValueError:
                        results["invalid_optional"].append(f"{var}: debe ser un número")
                        results["valid"] = False

                elif var == "AUTO_CREATE_RUNNERS":
                    if value.lower() not in ["true", "false"]:
                        results["invalid_optional"].append(f"{var}: debe ser true/false")
                        results["valid"] = False

                elif var in ["API_GATEWAY_PORT", "ORCHESTRATOR_PORT"]:
                    try:
                        port = int(value)
                        if not (1 <= port <= 65535):
                            results["invalid_optional"].append(f"{var}: puerto inválido (1-65535)")
                            results["valid"] = False
                    except ValueError:
                        results["invalid_optional"].append(f"{var}: debe ser un número")
                        results["valid"] = False

        # Validar variables de entorno de runners
        runner_vars = self._validate_runner_env_vars()
        results["runner_env_vars"] = runner_vars

        if not runner_vars["valid"]:
            results["valid"] = False
            results["errors"].extend(runner_vars["errors"])

        # Generar errores y warnings finales
        if results["missing_required"]:
            results["errors"].append(
                f"Variables obligatorias faltantes: {results['missing_required']}"
            )

        if results["invalid_optional"]:
            results["errors"].append(f"Variables inválidas: {results['invalid_optional']}")

        return results

    def _validate_github_token(self, token: str) -> bool:
        """
        Valida formato de token de GitHub.

        Args:
            token: Token a validar

        Returns:
            True si tiene formato válido
        """
        # Tokens personales empiezan con ghp_
        # Tokens de integración empiezan con gho_, ghu_, ghs_
        pattern = r"^gh[pouhs]_[A-Za-z0-9_]{36,255}$"
        return bool(re.match(pattern, token))

    def _validate_runner_image(self, image: str) -> bool:
        """
        Valida si la imagen del runner es compatible.
        Lógica genérica sin hardcodeo de imágenes específicas.

        Args:
            image: Nombre de la imagen

        Returns:
            True si es soportada (siempre true para sistema genérico)
        """
        # Sistema genérico: cualquier imagen es soportada vía runnerenv_
        logger.info(f"Imagen detectada: {image} (sistema genérico, cualquier imagen es soportada)")
        return True

    def _validate_runner_env_vars(self) -> Dict[str, Any]:
        """
        Valida variables de entorno de runners (runnerenv_*).

        Returns:
            Diccionario con resultado de validación
        """
        results = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "variables_found": 0,
            "invalid_placeholders": [],
        }

        # Encontrar todas las variables runnerenv_
        runner_env_vars = {}
        for key, value in os.environ.items():
            if key.startswith("runnerenv_"):
                env_key = key[11:]  # Remover prefijo
                runner_env_vars[env_key] = value

        results["variables_found"] = len(runner_env_vars)

        if not runner_env_vars:
            results["warnings"].append("No se encontraron variables runnerenv_*")
            return results

        # Validar placeholders en cada variable
        placeholder_pattern = r"\{[^}]+\}"

        for env_key, env_value in runner_env_vars.items():
            placeholders = re.findall(placeholder_pattern, env_value)

            for placeholder in placeholders:
                if not self._is_valid_placeholder(placeholder):
                    results["invalid_placeholders"].append(f"{env_key}: {placeholder}")
                    results["valid"] = False

        if results["invalid_placeholders"]:
            results["errors"].append(
                f"Placeholders inválidos encontrados: {results['invalid_placeholders']}"
            )

        return results

    def _is_valid_placeholder(self, placeholder: str) -> bool:
        """
        Verifica si un placeholder es válido.

        Args:
            placeholder: Placeholder a validar

        Returns:
            True si es válido
        """
        valid_placeholders = {
            # Básicas
            "{scope_name}",
            "{runner_name}",
            "{registration_token}",
            # Tiempo
            "{timestamp}",
            "{timestamp_iso}",
            "{timestamp_date}",
            "{timestamp_time}",
            # Sistema
            "{hostname}",
            "{orchestrator_id}",
            "{docker_network}",
            # Entorno
            "{orchestrator_port}",
            "{api_gateway_port}",
            "{runner_image}",
            "{registry_url}",
            # GitHub API
            "{repo_owner}",
            "{repo_name}",
            "{repo_full_name}",
            "{user_login}",
        }
        return placeholder in valid_placeholders

    def get_validation_summary(self) -> Dict[str, Any]:
        """
        Retorna resumen completo de validación.

        Returns:
            Diccionario con resumen
        """
        env_validation = self.validate_environment()

        return {
            "overall_valid": env_validation["valid"],
            "total_errors": len(env_validation["errors"]),
            "total_warnings": len(env_validation["warnings"]),
            "required_vars_found": len(self.required_env_vars)
            - len(env_validation["missing_required"]),
            "runner_env_vars_found": env_validation["runner_env_vars"]["variables_found"],
            "validation_details": env_validation,
        }

    def get_configuration_recommendations(self) -> List[str]:
        """
        Retorna recomendaciones de configuración.

        Returns:
            Lista de recomendaciones
        """
        recommendations = []

        # Verificar variables obligatorias
        for var in self.required_env_vars:
            if not os.getenv(var):
                recommendations.append(f"Configurar variable obligatoria: {var}")

        # Verificar variables de runners
        runner_vars_count = len([k for k in os.environ.keys() if k.startswith("runnerenv_")])
        if runner_vars_count == 0:
            recommendations.append(
                "Considerar configurar variables runnerenv_* para mayor flexibilidad"
            )

        # Recomendaciones de rendimiento
        check_interval = os.getenv("RUNNER_CHECK_INTERVAL", "300")
        try:
            interval = int(check_interval)
            if interval < 60:
                recommendations.append(
                    "RUNNER_CHECK_INTERVAL menor a 60 segundos puede causar carga excesiva"
                )
            elif interval > 600:
                recommendations.append(
                    "RUNNER_CHECK_INTERVAL mayor a 600 segundos puede retrasar la ejecución"
                )
        except ValueError:
            recommendations.append("Corregir RUNNER_CHECK_INTERVAL - debe ser un número")

        return recommendations
