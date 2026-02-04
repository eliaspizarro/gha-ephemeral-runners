"""
Excepciones específicas de infraestructura técnica.

Rol: Definir excepciones para errores técnicos externos.
DockerError, GitHubAPIError, ConfigurationError.
Excepciones que representan fallas en dependencias externas.

Depende de: excepciones base de Python.
"""

import logging
from typing import Dict, Any, Optional

# FastAPI imports - se manejarán cuando FastAPI esté disponible
try:
    from fastapi import HTTPException
    FASTAPI_AVAILABLE = True
except ImportError:
    HTTPException = None
    FASTAPI_AVAILABLE = False

logger = logging.getLogger(__name__)

# Excepciones base de infraestructura
class InfrastructureError(Exception):
    """Error base de infraestructura técnica."""
    pass


class DockerError(InfrastructureError):
    """Error relacionado con operaciones de Docker."""
    pass


class GitHubAPIError(InfrastructureError):
    """Error relacionado con GitHub API."""
    pass


class ConfigurationError(InfrastructureError):
    """Error de configuración del sistema."""
    pass


class NetworkError(InfrastructureError):
    """Error de conectividad o red."""
    pass


class ValidationError(InfrastructureError):
    """Error de validación de datos."""
    pass


class ErrorHandler:
    """Manejador centralizado de errores técnicos."""

    @staticmethod
    def handle_error(error: Exception, operation: str, logger) -> Any:
        """
        Maneja errores de infraestructura de forma centralizada.
        
        Args:
            error: Excepción ocurrida
            operation: Operación donde ocurrió el error
            logger: Logger para registrar el error
        
        Returns:
            HTTPException si FastAPI está disponible, sino dict con error
        """
        error_type = type(error).__name__
        error_message = str(error)
        
        # Mapear errores conocidos
        if isinstance(error, DockerError):
            status_code = 500
            detail = f"Error de Docker en {operation}: {error_message}"
        elif isinstance(error, GitHubAPIError):
            status_code = 502
            detail = f"Error de GitHub API en {operation}: {error_message}"
        elif isinstance(error, ConfigurationError):
            status_code = 500
            detail = f"Error de configuración en {operation}: {error_message}"

        elif isinstance(error, (ValueError, KeyError)):
            return HTTPException(status_code=400, detail=f"Error en datos: {error_msg}")

        elif isinstance(error, NetworkError):
            return HTTPException(status_code=503, detail="Error de conexión")

        else:
            status_code = 500
            detail = f"Error inesperado en {operation}: {error_message}"
        
        logger.error(f"{operation} - {error_type}: {error_message}")
        
        # Retornar HTTPException si FastAPI está disponible
        if FASTAPI_AVAILABLE and HTTPException:
            return HTTPException(status_code=status_code, detail=detail)
        else:
            # Retornar diccionario con información de error
            return {
                "status_code": status_code,
                "detail": detail,
                "error_type": error_type,
                "operation": operation
            }

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
