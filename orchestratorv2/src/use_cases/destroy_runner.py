"""
Caso de uso para destrucción de runners efímeros.

Rol: Orquestar el proceso completo de destrucción de un runner.
Valida existencia, coordina limpieza y maneja timeouts.
Asegura limpieza completa de recursos.

Depende de: OrchestrationService.
"""

import logging
from typing import Dict, Any

from ..shared.logging_utils import log_operation_start, log_operation_success, log_operation_error
from ..shared.domain_exceptions import RunnerNotFound, OrchestrationError
from ..shared.validation_utils import validate_timeout
from ..domain.orchestration_service import OrchestrationService

logger = logging.getLogger(__name__)


class DestroyRunner:
    """Caso de uso para destrucción de runners efímeros."""
    
    def __init__(self, orchestration_service: OrchestrationService):
        """Inicializa caso de uso."""
        self.orchestration_service = orchestration_service
    
    def execute(self, runner_id: str, timeout: int = 30) -> Dict[str, Any]:
        """
        Ejecuta la destrucción de un runner.
        
        Args:
            runner_id: ID del runner a destruir
            timeout: Timeout para destrucción
        
        Returns:
            Resultado de la destrucción
        """
        operation = "destroy_runner"
        log_operation_start(logger, operation, runner_id=runner_id, timeout=timeout)
        
        try:
            # Validar timeout
            timeout = validate_timeout(timeout)
            
            # Destruir runner
            success = self.orchestration_service.destroy_runner(runner_id, timeout)
            
            result = {
                "success": success,
                "runner_id": runner_id,
                "message": f"Runner {runner_id} {'destruido exitosamente' if success else 'no se pudo destruir'}",
                "timeout": timeout
            }
            
            log_operation_success(logger, operation, runner_id=runner_id, success=success)
            return result
            
        except RunnerNotFound as e:
            log_operation_error(logger, operation, e, runner_id=runner_id)
            return {
                "success": False,
                "runner_id": runner_id,
                "message": f"Runner no encontrado: {str(e)}",
                "error": "not_found"
            }
        except Exception as e:
            log_operation_error(logger, operation, e, runner_id=runner_id)
            raise OrchestrationError(f"Error destruyendo runner {runner_id}: {e}")
    
    def destroy_by_name(self, runner_name: str, timeout: int = 30) -> Dict[str, Any]:
        """
        Destruye un runner por nombre.
        
        Args:
            runner_name: Nombre del runner
            timeout: Timeout para destrucción
        
        Returns:
            Resultado de la destrucción
        """
        return self.execute(runner_name, timeout)
    
    def can_destroy_runner(self, runner_id: str) -> bool:
        """
        Verifica si un runner puede ser destruido.
        
        Args:
            runner_id: ID del runner
        
        Returns:
            True si puede ser destruido
        """
        try:
            status = self.orchestration_service.get_runner_status(runner_id)
            return status.get("status") in ["active", "container_lost"]
        except Exception:
            return False
