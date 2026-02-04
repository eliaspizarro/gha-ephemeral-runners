"""
Caso de uso para creación de runners efímeros.

Rol: Orquestar el proceso completo de creación de un runner.
Valida parámetros, coordina servicios y maneja errores de creación.
Es el punto de entrada para la lógica de negocio de creación.

Depende de: OrchestrationService, ContainerManager, TokenProvider.
"""

import logging
from typing import Optional, List, Dict, Any

from ..shared.logging_utils import log_operation_start, log_operation_success, log_operation_error
from ..shared.domain_exceptions import OrchestrationError, ValidationError
from ..shared.validation_utils import validate_scope, validate_repository, validate_runner_name, validate_runner_group, validate_labels, validate_count
from ..domain.orchestration_service import OrchestrationService

logger = logging.getLogger(__name__)


class CreateRunner:
    """Caso de uso para creación de runners efímeros."""
    
    def __init__(self, orchestration_service: OrchestrationService):
        """
        Inicializa caso de uso.
        
        Args:
            orchestration_service: Servicio de orquestación
        """
        self.orchestration_service = orchestration_service
    
    def execute(
        self,
        scope: str,
        scope_name: str,
        runner_name: Optional[str] = None,
        runner_group: Optional[str] = None,
        labels: Optional[List[str]] = None,
        count: int = 1
    ) -> List[Dict[str, Any]]:
        """
        Ejecuta la creación de uno o más runners.
        
        Args:
            scope: 'repo' u 'org'
            scope_name: Nombre del repositorio u organización
            runner_name: Nombre único del runner (opcional)
            runner_group: Grupo del runner (opcional)
            labels: Labels para el runner (opcional)
            count: Número de runners a crear
        
        Returns:
            Lista de resultados de creación
        
        Raises:
            ValidationError: Si los parámetros son inválidos
            OrchestrationError: Si falla la creación
        """
        operation = "create_runner_batch"
        log_operation_start(logger, operation, scope=scope, scope_name=scope_name, count=count)
        
        try:
            # Validar parámetros
            self._validate_params(scope, scope_name, runner_name, runner_group, labels, count)
            
            results = []
            
            # Crear runners
            for i in range(count):
                try:
                    # Generar nombre único si es necesario
                    current_runner_name = runner_name
                    if count > 1:
                        current_runner_name = f"{runner_name or 'runner'}-{i + 1}"
                    
                    # Crear runner individual
                    runner_id = self.orchestration_service.create_runner(
                        scope=scope,
                        scope_name=scope_name,
                        runner_name=current_runner_name,
                        runner_group=runner_group,
                        labels=labels
                    )
                    
                    results.append({
                        "success": True,
                        "runner_id": runner_id,
                        "runner_name": current_runner_name,
                        "message": f"Runner {runner_id} creado exitosamente"
                    })
                    
                except Exception as e:
                    error_msg = f"Error creando runner {i + 1}: {str(e)}"
                    logger.error(error_msg)
                    
                    results.append({
                        "success": False,
                        "runner_id": None,
                        "runner_name": current_runner_name or f"runner-{i + 1}",
                        "message": error_msg,
                        "error": str(e)
                    })
            
            # Estadísticas
            successful = len([r for r in results if r["success"]])
            failed = len(results) - successful
            
            log_operation_success(logger, operation, 
                                 scope=scope, scope_name=scope_name, count=count,
                                 successful=successful, failed=failed)
            
            return results
            
        except Exception as e:
            log_operation_error(logger, operation, e, scope=scope, scope_name=scope_name, count=count)
            raise OrchestrationError(f"Error en creación de runners: {e}")
    
    def create_single(
        self,
        scope: str,
        scope_name: str,
        runner_name: Optional[str] = None,
        runner_group: Optional[str] = None,
        labels: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Crea un único runner.
        
        Args:
            scope: 'repo' u 'org'
            scope_name: Nombre del repositorio u organización
            runner_name: Nombre único del runner (opcional)
            runner_group: Grupo del runner (opcional)
            labels: Labels para el runner (opcional)
        
        Returns:
            Resultado de la creación
        """
        results = self.execute(
            scope=scope,
            scope_name=scope_name,
            runner_name=runner_name,
            runner_group=runner_group,
            labels=labels,
            count=1
        )
        
        return results[0] if results else {"success": False, "message": "No se pudo crear el runner"}
    
    def _validate_params(
        self,
        scope: str,
        scope_name: str,
        runner_name: Optional[str],
        runner_group: Optional[str],
        labels: Optional[List[str]],
        count: int
    ) -> None:
        """Valida todos los parámetros de entrada."""
        # Validar scope
        validate_scope(scope)
        
        # Validar scope_name
        validate_repository(scope_name)
        
        # Validar runner_name si se proporciona
        if runner_name:
            validate_runner_name(runner_name)
        
        # Validar runner_group si se proporciona
        if runner_group:
            validate_runner_group(runner_group)
        
        # Validar labels si se proporcionan
        if labels:
            validated_labels = validate_labels(labels)
            if not validated_labels:
                raise ValidationError("Labels inválidos o vacíos")
        
        # Validar count
        if count < 1 or count > 10:
            raise ValidationError("Count debe estar entre 1 y 10")
    
    def can_create_runner(self, scope: str, scope_name: str) -> bool:
        """
        Verifica si se puede crear un runner para el repositorio.
        
        Args:
            scope: 'repo' u 'org'
            scope_name: Nombre del repositorio u organización
        
        Returns:
            True si se puede crear
        """
        try:
            return self.orchestration_service.should_create_runner_for_repo(scope_name)
        except Exception:
            return False
    
    def get_runner_demand(self, scope_name: str) -> int:
        """
        Obtiene la demanda actual de runners para un repositorio.
        
        Args:
            scope_name: Nombre del repositorio
        
        Returns:
            Número de runners necesarios
        """
        try:
            return self.orchestration_service.get_repository_runner_demand(scope_name)
        except Exception:
            return 0
    
    def get_creation_recommendation(
        self, scope_name: str, current_runners: int = 0
    ) -> Dict[str, Any]:
        """
        Obtiene recomendación de creación de runners.
        
        Args:
            scope_name: Nombre del repositorio
            current_runners: Número actual de runners
        
        Returns:
            Recomendación con detalles
        """
        try:
            needed = self.get_runner_demand(scope_name)
            can_create = self.can_create_runner("repo", scope_name)
            
            recommendation = {
                "scope_name": scope_name,
                "current_runners": current_runners,
                "needed_runners": needed,
                "can_create": can_create,
                "recommended_action": "none"
            }
            
            if needed > current_runners and can_create:
                recommendation["recommended_action"] = "create"
                recommendation["runners_to_create"] = min(needed - current_runners, 5)
            elif needed > current_runners and not can_create:
                recommendation["recommended_action"] = "limit_reached"
            elif needed <= current_runners:
                recommendation["recommended_action"] = "sufficient"
            
            return recommendation
            
        except Exception as e:
            logger.error(f"Error obteniendo recomendación para {scope_name}: {e}")
            return {
                "scope_name": scope_name,
                "current_runners": current_runners,
                "error": str(e),
                "recommended_action": "error"
            }
