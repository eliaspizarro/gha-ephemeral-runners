"""
Utilitarios comunes para el orchestrator.
Centraliza funciones repetitivas para evitar duplicación de código.
"""

import logging
import os
import re
from typing import Any, Dict, Optional


def setup_logger(name: str) -> logging.Logger:
    """
    Configura y retorna un logger estandarizado.

    Args:
        name: Nombre del logger

    Returns:
        Logger configurado
    """
    return logging.getLogger(name)


def setup_logging_config():
    """
    Configura el logging básico para toda la aplicación.
    Debe llamarse una sola vez al inicio.
    """
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s, %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Reducir verbosidad de uvicorn
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.error").setLevel(logging.ERROR)


def get_env_var(key: str, default: str = None, required: bool = False) -> str:
    """
    Obtiene variable de entorno con validación.

    Args:
        key: Nombre de la variable
        default: Valor por defecto
        required: Si es obligatoria

    Returns:
        Valor de la variable

    Raises:
        RuntimeError: Si es obligatoria y no está presente
    """
    value = os.getenv(key, default)
    if required and not value:
        raise RuntimeError(f"{key} es obligatorio")
    return value


def format_container_id(container_id: str) -> str:
    """
    Formatea ID de contenedor a 12 caracteres.

    Args:
        container_id: ID completo del contenedor

    Returns:
        ID formateado a 12 caracteres
    """
    return container_id[:12] if container_id else "unknown"


def validate_runner_name(runner_name: str) -> str:
    """
    Valida y normaliza nombre de runner.

    Args:
        runner_name: Nombre a validar

    Returns:
        Nombre validado

    Raises:
        ValueError: Si el nombre es inválido
    """
    if not runner_name:
        raise ValueError("runner_name no puede estar vacío")

    # Eliminar caracteres inválidos
    clean_name = re.sub(r"[^a-zA-Z0-9_-]", "", runner_name)

    if not clean_name:
        raise ValueError("runner_name contiene caracteres inválidos")

    return clean_name


def create_response(success: bool, message: str, data: Any = None) -> Dict[str, Any]:
    """
    Crea una respuesta estandarizada.

    Args:
        success: Si la operación fue exitosa
        message: Mensaje de respuesta
        data: Datos adicionales (opcional)

    Returns:
        Diccionario con respuesta estandarizada
    """
    response = {"success": success, "message": message}

    if data is not None:
        response["data"] = data

    return response
