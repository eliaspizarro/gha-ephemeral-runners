"""
Utilitarios de configuración y manejo de logging.

Rol: Configurar logging centralizado para toda la aplicación.
Define formateadores, handlers y niveles de logging.
Provee funciones helper para logging específico del dominio.

Depende de: logging library, configuración de entorno.
"""

import logging
import os
import sys
from typing import Optional


def setup_logger(name: str, level: Optional[str] = None) -> logging.Logger:
    """
    Configura y retorna un logger estandarizado.

    Args:
        name: Nombre del logger
        level: Nivel de logging (opcional)

    Returns:
        Logger configurado
    """
    logger = logging.getLogger(name)
    
    if not logger.handlers:
        # Configurar handler solo si no existe
        handler = logging.StreamHandler(sys.stdout)
        
        # Formato detallado para producción
        formatter = logging.Formatter(
            fmt="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        handler.setFormatter(formatter)
        
        logger.addHandler(handler)
    
    # Configurar nivel
    log_level = getattr(logging, (level or os.getenv("LOG_LEVEL", "INFO")).upper())
    logger.setLevel(log_level)
    
    return logger


def setup_logging_config() -> None:
    """
    Configura el logging básico para toda la aplicación.
    Debe llamarse una sola vez al inicio.
    """
    # Configurar logging raíz
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # Reducir verbosidad de librerías externas
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.error").setLevel(logging.ERROR)
    logging.getLogger("docker").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """
    Obtiene logger configurado para un módulo específico.

    Args:
        name: Nombre del módulo

    Returns:
        Logger configurado
    """
    return logging.getLogger(name)


def format_domain_log(operation: str, entity_id: str, message: str) -> str:
    """
    Formatea mensaje de log para entidades de dominio.

    Args:
        operation: Operación realizada
        entity_id: ID de la entidad
        message: Mensaje adicional

    Returns:
        Mensaje formateado
    """
    return f"{operation} | {entity_id} | {message}"


def format_infrastructure_log(component: str, operation: str, details: str) -> str:
    """
    Formatea mensaje de log para componentes de infraestructura.

    Args:
        component: Componente (Docker, GitHub, etc.)
        operation: Operación realizada
        details: Detalles adicionales

    Returns:
        Mensaje formateado
    """
    return f"{component} | {operation} | {details}"


def mask_sensitive_data(data: str, mask_char: str = "*", visible_chars: int = 4) -> str:
    """
    Enmascara datos sensibles en logs.

    Args:
        data: Dato sensible (token, password, etc.)
        mask_char: Carácter para enmascarar
        visible_chars: Caracteres visibles al inicio

    Returns:
        Dato enmascarado
    """
    if not data or len(data) <= visible_chars:
        return mask_char * 8
    
    return data[:visible_chars] + mask_char * (len(data) - visible_chars)


def log_operation_start(logger: logging.Logger, operation: str, **kwargs) -> None:
    """
    Registra inicio de operación con contexto.

    Args:
        logger: Logger a usar
        operation: Descripción de operación
        **kwargs: Contexto adicional
    """
    context = " | ".join([f"{k}={v}" for k, v in kwargs.items()])
    logger.info(f"INICIO | {operation} | {context}")


def log_operation_success(logger: logging.Logger, operation: str, **kwargs) -> None:
    """
    Registra éxito de operación con contexto.

    Args:
        logger: Logger a usar
        operation: Descripción de operación
        **kwargs: Contexto adicional
    """
    context = " | ".join([f"{k}={v}" for k, v in kwargs.items()])
    logger.info(f"ÉXITO | {operation} | {context}")


def log_operation_error(logger: logging.Logger, operation: str, error: Exception, **kwargs) -> None:
    """
    Registra error de operación con contexto.

    Args:
        logger: Logger a usar
        operation: Descripción de operación
        error: Excepción capturada
        **kwargs: Contexto adicional
    """
    context = " | ".join([f"{k}={v}" for k, v in kwargs.items()])
    logger.error(f"ERROR | {operation} | {type(error).__name__}: {str(error)} | {context}")
