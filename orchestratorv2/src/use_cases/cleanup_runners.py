"""
Caso de uso para limpieza masiva de runners.

Rol: Orquestar la limpieza de múltiples runners inactivos.
Identifica candidatos, ejecuta limpieza en batch y reporta resultados.
Implementa la lógica de purga basada en workflows activos.

Depende de: OrchestrationService.
"""

import logging
from typing import Dict, Any, List

from ..shared.logging_utils import log_operation_start, log_operation_success, log_operation_error
from ..shared.domain_exceptions import OrchestrationError
from ..domain.orchestration_service import OrchestrationService

logger = logging.getLogger(__name__)


class CleanupRunners:
    """Caso de uso para limpieza masiva de runners."""
    
    def __init__(self, orchestration_service: OrchestrationService):
        """Inicializa caso de uso."""
        self.orchestration_service = orchestration_service
    
    def execute(self, dry_run: bool = False) -> Dict[str, Any]:
        """
        Ejecuta la limpieza masiva de runners inactivos.
        
        Args:
            dry_run: Si es True, solo simula la limpieza sin ejecutar
        
        Returns:
            Resultado de la limpieza
        """
        operation = "cleanup_runners"
        log_operation_start(logger, operation, dry_run=dry_run)
        
        try:
            if dry_run:
                # Simulación: identificar candidatos sin eliminar
                candidates = self._identify_cleanup_candidates()
                
                result = {
                    "success": True,
                    "dry_run": True,
                    "candidates_count": len(candidates),
                    "candidates": candidates,
                    "message": f"Se identificaron {len(candidates)} runners para limpieza (dry run)"
                }
                
                log_operation_success(logger, operation, dry_run=True, candidates=len(candidates))
                return result
            
            # Ejecución real
            cleaned_count = self.orchestration_service.cleanup_inactive_runners()
            
            result = {
                "success": True,
                "dry_run": False,
                "cleaned_count": cleaned_count,
                "message": f"Se limpiaron {cleaned_count} runners inactivos"
            }
            
            log_operation_success(logger, operation, dry_run=False, cleaned_count=cleaned_count)
            return result
            
        except Exception as e:
            log_operation_error(logger, operation, e, dry_run=dry_run)
            raise OrchestrationError(f"Error en limpieza de runners: {e}")
    
    def get_cleanup_candidates(self) -> List[Dict[str, Any]]:
        """
        Obtiene la lista de runners que pueden ser limpiados.
        
        Returns:
            Lista de candidatos para limpieza
        """
        try:
            return self._identify_cleanup_candidates()
        except Exception as e:
            logger.error(f"Error obteniendo candidatos de limpieza: {e}")
            return []
    
    def _identify_cleanup_candidates(self) -> List[Dict[str, Any]]:
        """
        Identifica runners que pueden ser limpiados.
        
        Returns:
            Lista de candidatos con información
        """
        try:
            active_runners = self.orchestration_service.list_active_runners()
            candidates = []
            
            for runner_info in active_runners:
                if self._should_cleanup_runner(runner_info):
                    candidates.append(runner_info)
            
            return candidates
            
        except Exception as e:
            logger.error(f"Error identificando candidatos: {e}")
            return []
    
    def _should_cleanup_runner(self, runner_info: Dict[str, Any]) -> bool:
        """
        Determina si un runner debe ser limpiado.
        
        Args:
            runner_info: Información del runner
        
        Returns:
            True si debe ser limpiado
        """
        try:
            # Runner debe estar en estado terminable
            status = runner_info.get("status", "")
            if status not in ["active", "container_lost"]:
                return False
            
            # Verificar si hay workflows activos para el repositorio
            repository = runner_info.get("repository", "")
            if not repository:
                return True  # Si no hay repo info, limpiar
            
            # Usar el servicio para verificar workflows activos
            active_workflows = self.orchestration_service.get_repository_runner_demand(repository)
            
            # Si no hay demanda, limpiar
            return active_workflows == 0
            
        except Exception:
            # Si hay error, ser conservador y no limpiar
            return False
    
    def get_cleanup_statistics(self) -> Dict[str, Any]:
        """
        Obtiene estadísticas de limpieza.
        
        Returns:
            Estadísticas de limpieza
        """
        try:
            candidates = self.get_cleanup_candidates()
            active_runners = self.orchestration_service.list_active_runners()
            
            return {
                "total_active_runners": len(active_runners),
                "cleanup_candidates": len(candidates),
                "cleanup_ratio": len(candidates) / len(active_runners) if active_runners else 0,
                "candidates": candidates[:10]  # Primeros 10
            }
            
        except Exception as e:
            logger.error(f"Error obteniendo estadísticas de limpieza: {e}")
            return {"error": str(e)}
