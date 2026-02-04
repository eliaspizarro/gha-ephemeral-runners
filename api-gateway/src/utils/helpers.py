"""
API Gateway - Utility Functions
Contains shared utility functions for logging and common operations.
"""

import logging
from typing import Any, Dict, Optional

from fastapi import Request

from src.config.settings import LOG_LEVEL

# Constantes de formato para logging estandarizado (mismo sistema que orchestrator)
LOG_CATEGORIES = {
    'START': '🚀 INICIO',
    'CONFIG': '⚙️ CONFIG', 
    'MONITOR': '🔄 MONITOREO',
    'SUCCESS': '✅ ÉXITO',
    'ERROR': '❌ ERROR',
    'WARNING': '⚠️ ADVERTENCIA',
    'INFO': '📋 INFO',
    'REQUEST': '🌐 REQUEST',
    'RESPONSE': '📤 RESPONSE',
    'HEALTH': '💚 HEALTH',
    'SHUTDOWN': '🛑 SHUTDOWN'
}

def format_log(category: str, action: str, detail: str = "") -> str:
    """Formatea mensaje de log consistente (mismo sistema que orchestrator)."""
    prefix = LOG_CATEGORIES.get(category, '📋 INFO')
    if detail:
        return f"{prefix} {action}: {detail}"
    return f"{prefix} {action}"

def setup_logging_config() -> None:
    """Configure basic logging for the application."""
    logging.basicConfig(
        level=LOG_LEVEL,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # Log de configuración
    logger = logging.getLogger(__name__)
    logger.info(format_log('CONFIG', 'Sistema de logging configurado'))

def log_request_info(request: Request) -> Dict[str, Any]:
    """Extract and log request information."""
    return {
        "method": request.method,
        "url": str(request.url),
        "ip": request.client.host if request.client else "unknown",
    }
