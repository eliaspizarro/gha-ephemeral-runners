"""
API Gateway - Main Entry Point
FastAPI application entry point for the API Gateway service.
"""

import asyncio
import logging
import os
import signal
import sys

import uvicorn

from src.core.gateway_service import create_app
from src.utils.helpers import format_log

logger = logging.getLogger(__name__)


async def shutdown_signal(signum, frame):
    """Handle shutdown signals gracefully."""
    logger.info(format_log('INFO', 'Recibida señal', f'{signum} - iniciando graceful shutdown'))
    
    # Dar tiempo a las solicitudes en curso para terminar
    logger.info(format_log('INFO', 'Esperando 5 segundos para finalizar solicitudes en curso'))
    await asyncio.sleep(5)
    
    logger.info(format_log('SUCCESS', 'Aplicación cerrada'))
    sys.exit(0)


def setup_signal_handlers():
    """Setup signal handlers for graceful shutdown."""
    # Para contenedores Docker
    signal.signal(signal.SIGTERM, lambda s, f: asyncio.create_task(shutdown_signal(s, f)))
    signal.signal(signal.SIGINT, lambda s, f: asyncio.create_task(shutdown_signal(s, f)))


if __name__ == "__main__":
    # Configurar handlers de señales
    setup_signal_handlers()
    
    # Create the FastAPI application
    app = create_app()
    
    # Get port from environment or use default
    port = int(os.getenv("API_GATEWAY_PORT", "8080"))
    
    logger.info(format_log('START', 'API Gateway', f'puerto {port}'))
    
    # Run the application
    try:
        uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
    except KeyboardInterrupt:
        logger.info(format_log('INFO', 'Interrupción recibida', 'cerrando...'))
    except Exception as e:
        logger.error(format_log('ERROR', 'Error al iniciar la aplicación', str(e)))
        sys.exit(1)
