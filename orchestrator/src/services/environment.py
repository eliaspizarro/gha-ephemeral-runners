import logging
import os
from typing import Any, Dict, List, Optional

from src.utils.helpers import PlaceholderResolver

logger = logging.getLogger(__name__)


class EnvironmentManager:
    """
    Gestiona variables de entorno para runners con soporte para placeholders.

    Carga variables con prefijo 'runnerenv_' y resuelve placeholders dinámicos.
    Soporta múltiples configuraciones según la imagen del runner.
    """

    def __init__(self, runner_image: str):
        self.runner_image = runner_image
        self.placeholder_resolver = PlaceholderResolver()
        self._cached_config: Optional[Dict[str, str]] = None

    def load_runner_environment(self) -> Dict[str, str]:
        """
        Carga variables de entorno con prefijo runnerenv_.
        Las variables deben venir del compose.yaml a través del .env del host.

        Returns:
            Diccionario de variables de entorno para el runner
        """
        if self._cached_config is not None:
            return self._cached_config

        runner_env = {}

        # Cargar todas las variables con prefijo runnerenv_ del entorno del contenedor
        for key, value in os.environ.items():
            if key.startswith("runnerenv_"):
                # Remover prefijo "runnerenv_"
                env_key = key.replace("runnerenv_", "", 1)  # Reemplazar solo la primera ocurrencia
                runner_env[env_key] = value
                logger.debug(f"Variable runnerenv encontrada: {env_key}")

        self._cached_config = runner_env
        logger.info(f"Cargadas {len(runner_env)} variables de entorno para runners")

        # Si no se encontraron variables, mostrar advertencia
        if len(runner_env) == 0:
            logger.warning("No se encontraron variables runnerenv_ en el entorno del contenedor")
            logger.warning(
                "Asegúrate de que el compose.yaml esté pasando correctamente las variables runnerenv_"
            )
            logger.warning(
                "Verifica que el archivo .env del host contenga las variables runnerenv_*"
            )

        return runner_env

    def process_environment_variables(
        self, scope_name: str, runner_name: str, registration_token: str
    ) -> Dict[str, str]:
        """
        Procesa variables de entorno resolviendo placeholders.

        Args:
            scope_name: Nombre del repositorio/organización
            runner_name: Nombre único del runner
            registration_token: Token de registro

        Returns:
            Diccionario de variables procesadas
        """
        try:
            # Cargar variables base
            raw_env = self.load_runner_environment()

            if not raw_env:
                logger.warning("No se encontraron variables runnerenv_")
                return self._get_default_environment(scope_name, runner_name, registration_token)

            # Contexto para resolución de placeholders
            context = {
                "scope_name": scope_name,
                "runner_name": runner_name,
                "registration_token": registration_token,
            }

            # Procesar cada variable
            processed_env = {}
            for key, value in raw_env.items():
                resolved_value = self.placeholder_resolver.resolve_placeholders(value, context)
                processed_env[key] = resolved_value

                # Log de resolución para debugging
                if value != resolved_value:
                    logger.debug(f"Variable {key}: '{value}' -> '{resolved_value}'")

                # Log específico para REPO_URL
                if key == "REPO_URL":
                    logger.info(f"REPO_URL resuelto: '{resolved_value}'")
                    if not resolved_value or resolved_value == "https://github.com/":
                        logger.error(f"REPO_URL inválido: '{resolved_value}'")

                # Log de todas las variables procesadas para debugging
                logger.info(f"Variable procesada - {key}: '{resolved_value}'")

            logger.info(f"Procesadas {len(processed_env)} variables de entorno")
            return processed_env

        except Exception as e:
            logger.error(f"Error procesando variables de entorno: {e}")
            logger.info("Usando configuración por defecto como fallback")
            return self._get_default_environment(scope_name, runner_name, registration_token)

    def _get_default_environment(
        self, scope_name: str, runner_name: str, registration_token: str
    ) -> Dict[str, str]:
        """
        Retorna configuración por defecto para runners.
        Solo las variables mínimas que no pueden venir del .env.

        Args:
            scope_name: Nombre del repositorio
            runner_name: Nombre del runner
            registration_token: Token de registro

        Returns:
            Configuración por defecto
        """
        logger.info("Usando configuración por defecto para runners")

        # Validar que scope_name sea válido
        if not scope_name or "/" not in scope_name:
            logger.error(f"scope_name inválido: '{scope_name}'")
            # No usar hardcodeo, lanzar error
            raise ValueError(f"scope_name inválido: '{scope_name}'. Debe ser 'owner/repo'")

        repo_url = f"https://github.com/{scope_name}"
        logger.info(f"Configuración por defecto - REPO_URL: {repo_url}")

        # SOLO las variables que no pueden venir del .env
        return {
            "REPO_URL": repo_url,
            "RUNNER_TOKEN": registration_token,
            "RUNNER_NAME": runner_name,
        }

    def validate_configuration(self) -> Dict[str, Any]:
        """
        Valida la configuración actual.

        Returns:
            Diccionario con resultado de validación
        """
        try:
            raw_env = self.load_runner_environment()

            if not raw_env:
                return {
                    "valid": True,
                    "warnings": [
                        "Usando configuración por defecto - no se encontraron variables runnerenv_"
                    ],
                    "errors": [],
                    "image_compatible": True,
                }

            # Validar placeholders en cada variable
            validation_results = []
            invalid_placeholders = []

            for key, value in raw_env.items():
                result = self.placeholder_resolver.validate_template(value)
                validation_results.append(
                    {"variable": key, "template": value, "validation": result}
                )

                if not result["is_valid"]:
                    invalid_placeholders.extend(result["invalid_placeholders"])

            # Determinar compatibilidad con imagen
            image_compatible = self._check_image_compatibility(raw_env)

            return {
                "valid": len(invalid_placeholders) == 0,
                "warnings": [],
                "errors": (
                    [f"Placeholders inválidos: {set(invalid_placeholders)}"]
                    if invalid_placeholders
                    else []
                ),
                "image_compatible": image_compatible,
                "validation_details": validation_results,
            }

        except Exception as e:
            logger.error(f"Error validando configuración: {e}")
            return {
                "valid": False,
                "warnings": [],
                "errors": [f"Error en validación: {str(e)}"],
                "image_compatible": False,
            }

    def is_image_compatible(self, env_vars: Dict[str, str]) -> bool:
        """
        Verifica si las variables de entorno son compatibles con la imagen del runner.
        Lógica genérica sin hardcodeo de imágenes específicas.

        Args:
            env_vars: Variables de entorno a verificar

        Returns:
            True si es compatible, False si no
        """
        # Lógica genérica: verificar que haya variables básicas
        # Las variables específicas de cada imagen deben venir del .env
        basic_vars = ["REPO_URL", "RUNNER_TOKEN", "RUNNER_NAME"]

        for var in basic_vars:
            if var not in env_vars:
                logger.warning(f"Variable básica faltante: {var}")
                return False

        logger.info(f"Variables básicas presentes para imagen {self.runner_image}")
        return True

    def get_configuration_summary(self) -> Dict[str, Any]:
        """
        Retorna resumen de la configuración actual.

        Returns:
            Diccionario con información de configuración
        """
        raw_env = self.load_runner_environment()

        return {
            "runner_image": self.runner_image,
            "total_variables": len(raw_env),
            "variable_names": list(raw_env.keys()),
            "has_configuration": len(raw_env) > 0,
            "available_placeholders": len(self.placeholder_resolver.get_available_placeholders()),
            "orchestrator_id": self.placeholder_resolver.orchestrator_id,
        }

    def reload_configuration(self):
        """Recarga la configuración desde variables de entorno."""
        self._cached_config = None
        logger.info("Configuración recargada")

    def get_placeholder_info(self) -> Dict[str, str]:
        """
        Retorna información sobre placeholders disponibles.

        Returns:
            Diccionario placeholder -> descripción
        """
        return self.placeholder_resolver.get_available_placeholders()
