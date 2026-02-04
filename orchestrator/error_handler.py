"""
Manejador centralizado de errores para el orchestrator.
Proporciona manejo consistente de errores y logging.
"""

import logging
from typing import Any, Dict, Optional

from fastapi import HTTPException
from utils import setup_logger

logger = setup_logger(__name__)


class OrchestratorError(Exception):
    """Error base del orchestrator."""

    pass


class ValidationError(OrchestratorError):
    """Error de validación."""

    pass


class DockerError(OrchestratorError):
    """Error relacionado con Docker."""

    pass


class GitHubError(OrchestratorError):
    """Error relacionado con GitHub API."""

    pass


class ConfigurationError(OrchestratorError):
    """Error de configuración."""

    pass


class ErrorHandler:
    """Manejador centralizado de errores."""

    @staticmethod
    def handle_error(
        error: Exception, operation: str, context: Optional[Dict[str, Any]] = None
    ) -> HTTPException:
        """
        Maneja errores de forma centralizada.

        Args:
            error: Excepción capturada
            operation: Descripción de la operación
            context: Contexto adicional (opcional)

        Returns:
            HTTPException apropiada
        """
        error_type = type(error).__name__
        error_msg = str(error)

        # Logging detallado
        logger.error(f"Error en {operation}: {error_type} - {error_msg}")
        if context:
            logger.error(f"Contexto: {context}")

        # Mapeo de errores a HTTP status codes
        if isinstance(error, ValidationError):
            return HTTPException(status_code=400, detail=f"Error de validación: {error_msg}")

        elif isinstance(error, DockerError):
            return HTTPException(status_code=500, detail=f"Error de Docker: {error_msg}")

        elif isinstance(error, GitHubError):
            return HTTPException(status_code=502, detail=f"Error de GitHub API: {error_msg}")

        elif isinstance(error, ConfigurationError):
            return HTTPException(status_code=500, detail=f"Error de configuración: {error_msg}")

        elif isinstance(error, (ValueError, KeyError)):
            return HTTPException(status_code=400, detail=f"Error en datos: {error_msg}")

        elif isinstance(error, ConnectionError):
            return HTTPException(status_code=503, detail="Error de conexión")

        else:
            return HTTPException(status_code=500, detail="Error interno del servidor")

    @staticmethod
    def log_error(
        error: Exception,
        operation: str,
        context: Optional[Dict[str, Any]] = None,
        level: str = "error",
    ) -> None:
        """
        Registra error con contexto detallado.

        Args:
            error: Excepción capturada
            operation: Descripción de la operación
            context: Contexto adicional (opcional)
            level: Nivel de logging (error, warning, info)
        """
        log_func = getattr(logger, level)

        error_type = type(error).__name__
        error_msg = str(error)

        log_msg = f"Error en {operation}: {error_type} - {error_msg}"

        if context:
            log_msg += f" | Contexto: {context}"

        log_func(log_msg)

    @staticmethod
    def create_error_response(
        success: bool,
        message: str,
        error_details: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Crea respuesta de error estandarizada.

        Args:
            success: Si la operación fue exitosa
            message: Mensaje principal
            error_details: Detalles del error (opcional)
            data: Datos adicionales (opcional)

        Returns:
            Diccionario con respuesta estandarizada
        """
        response = {"success": success, "message": message}

        if error_details:
            response["error_details"] = error_details

        if data:
            response["data"] = data

        return response
