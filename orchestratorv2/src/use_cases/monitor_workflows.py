"""
Caso de uso para monitoreo continuo de workflows.

Rol: Orquestar el monitoreo continuo de estados de GitHub.
Consulta periódicamente workflows y dispara acciones automáticas.
Mantiene el ciclo de vida de monitoreo activo.

Depende de: OrchestrationService.
"""

import logging
import threading
import time
from typing import Dict, Any, Optional

from ..shared.logging_utils import log_operation_start, log_operation_success, log_operation_error
from ..shared.constants import DEFAULT_POLL_INTERVAL, DEFAULT_CLEANUP_INTERVAL
from ..shared.domain_exceptions import OrchestrationError
from ..domain.orchestration_service import OrchestrationService

logger = logging.getLogger(__name__)


class MonitorWorkflows:
    """Caso de uso para monitoreo continuo de workflows."""
    
    def __init__(self, orchestration_service: OrchestrationService):
        """Inicializa caso de uso."""
        self.orchestration_service = orchestration_service
        
        # Estado de monitoreo
        self.monitoring_active = False
        self.monitor_thread: Optional[threading.Thread] = None
        self.poll_interval = DEFAULT_POLL_INTERVAL
        self.cleanup_interval = DEFAULT_CLEANUP_INTERVAL
        self.last_cleanup_time = 0
        
        # Estadísticas
        self.monitoring_stats = {
            "total_cycles": 0,
            "last_check_time": None,
            "errors_count": 0
        }
    
    def start_monitoring(self, poll_interval: Optional[int] = None, cleanup_interval: Optional[int] = None) -> Dict[str, Any]:
        """
        Inicia el monitoreo automático de workflows.
        
        Args:
            poll_interval: Intervalo de polling en segundos
            cleanup_interval: Intervalo de limpieza en segundos
        
        Returns:
            Resultado del inicio
        """
        operation = "start_monitoring"
        log_operation_start(logger, operation)
        
        try:
            if self.monitoring_active:
                return {
                    "success": False,
                    "message": "El monitoreo ya está activo",
                    "monitoring_active": True
                }
            
            # Actualizar configuración
            if poll_interval:
                self.poll_interval = poll_interval
            if cleanup_interval:
                self.cleanup_interval = cleanup_interval
            
            # Iniciar thread de monitoreo
            self.monitoring_active = True
            self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
            self.monitor_thread.start()
            
            result = {
                "success": True,
                "message": "Monitoreo iniciado exitosamente",
                "monitoring_active": True,
                "poll_interval": self.poll_interval,
                "cleanup_interval": self.cleanup_interval
            }
            
            log_operation_success(logger, operation, poll_interval=self.poll_interval, cleanup_interval=self.cleanup_interval)
            return result
            
        except Exception as e:
            log_operation_error(logger, operation, e)
            raise OrchestrationError(f"Error iniciando monitoreo: {e}")
    
    def stop_monitoring(self) -> Dict[str, Any]:
        """
        Detiene el monitoreo automático.
        
        Returns:
            Resultado de la detención
        """
        operation = "stop_monitoring"
        log_operation_start(logger, operation)
        
        try:
            if not self.monitoring_active:
                return {
                    "success": False,
                    "message": "El monitoreo no está activo",
                    "monitoring_active": False
                }
            
            # Detener monitoreo
            self.monitoring_active = False
            
            if self.monitor_thread and self.monitor_thread.is_alive():
                self.monitor_thread.join(timeout=5)
            
            result = {
                "success": True,
                "message": "Monitoreo detenido exitosamente",
                "monitoring_active": False,
                "total_cycles": self.monitoring_stats["total_cycles"],
                "errors_count": self.monitoring_stats["errors_count"]
            }
            
            log_operation_success(logger, operation, total_cycles=self.monitoring_stats["total_cycles"])
            return result
            
        except Exception as e:
            log_operation_error(logger, operation, e)
            raise OrchestrationError(f"Error deteniendo monitoreo: {e}")
    
    def get_monitoring_status(self) -> Dict[str, Any]:
        """
        Obtiene el estado actual del monitoreo.
        
        Returns:
            Estado del monitoreo
        """
        return {
            "monitoring_active": self.monitoring_active,
            "poll_interval": self.poll_interval,
            "cleanup_interval": self.cleanup_interval,
            "monitoring_thread_alive": self.monitor_thread.is_alive() if self.monitor_thread else False,
            "stats": self.monitoring_stats.copy()
        }
    
    def force_check(self) -> Dict[str, Any]:
        """
        Fuerza una verificación inmediata.
        
        Returns:
            Resultado de la verificación
        """
        operation = "force_check"
        log_operation_start(logger, operation)
        
        try:
            # Ejecutar ciclo de monitoreo una vez
            self._monitoring_cycle()
            
            result = {
                "success": True,
                "message": "Verificación forzada completada",
                "stats": self.monitoring_stats.copy()
            }
            
            log_operation_success(logger, operation)
            return result
            
        except Exception as e:
            self.monitoring_stats["errors_count"] += 1
            log_operation_error(logger, operation, e)
            return {
                "success": False,
                "message": f"Error en verificación forzada: {e}",
                "stats": self.monitoring_stats.copy()
            }
    
    def _monitor_loop(self) -> None:
        """Bucle principal de monitoreo."""
        logger.info("Iniciando bucle de monitoreo de workflows")
        
        while self.monitoring_active:
            try:
                self._monitoring_cycle()
                time.sleep(self.poll_interval)
                
            except Exception as e:
                self.monitoring_stats["errors_count"] += 1
                logger.error(f"Error en bucle de monitoreo: {e}")
                time.sleep(60)  # Esperar antes de reintentar
        
        logger.info("Bucle de monitoreo finalizado")
    
    def _monitoring_cycle(self) -> None:
        """Ejecuta un ciclo completo de monitoreo."""
        try:
            self.monitoring_stats["total_cycles"] += 1
            self.monitoring_stats["last_check_time"] = time.time()
            
            # Verificar si se debe ejecutar limpieza
            current_time = time.time()
            if current_time - self.last_cleanup_time >= self.cleanup_interval:
                self._execute_cleanup()
                self.last_cleanup_time = current_time
            
            # Obtener estadísticas
            stats = self.orchestration_service.get_statistics()
            
            logger.debug(f"Ciclo {self.monitoring_stats['total_cycles']}: {stats.get('total_runners', 0)} runners activos")
            
        except Exception as e:
            self.monitoring_stats["errors_count"] += 1
            logger.error(f"Error en ciclo de monitoreo: {e}")
    
    def _execute_cleanup(self) -> None:
        """Ejecuta limpieza de runners."""
        try:
            cleanup_service = __import__("..cleanup_runners", fromlist=["CleanupRunners"]).CleanupRunners(self.orchestration_service)
            result = cleanup_service.execute(dry_run=False)
            
            logger.info(f"Limpieza ejecutada: {result.get('cleaned_count', 0)} runners limpiados")
            
        except Exception as e:
            logger.error(f"Error en limpieza automática: {e}")
    
    def update_configuration(self, poll_interval: Optional[int] = None, cleanup_interval: Optional[int] = None) -> Dict[str, Any]:
        """Actualiza la configuración de monitoreo.
        
        Args:
            poll_interval: Nuevo intervalo de polling
            cleanup_interval: Nuevo intervalo de limpieza
        
        Returns:
            Resultado de la actualización
        """
        try:
            if poll_interval:
                self.poll_interval = poll_interval
            if cleanup_interval:
                self.cleanup_interval = cleanup_interval
            
            return {
                "success": True,
                "message": "Configuración actualizada",
                "poll_interval": self.poll_interval,
                "cleanup_interval": self.cleanup_interval
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"Error actualizando configuración: {e}",
                "error": str(e)
            }
