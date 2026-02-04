"""
Endpoints específicos para gestión de runners.

Rol: Exponer endpoints REST para operaciones de runners.
POST /runners/create, DELETE /runners/{id}, GET /runners, POST /runners/cleanup.
Convierte requests HTTP a llamadas a casos de uso.

Depende de: casos de uso, schemas Pydantic, FastAPI.
"""

import logging
from typing import List
from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import JSONResponse

from ..shared.infrastructure_exceptions import ErrorHandler
from ..shared.logging_utils import log_operation_start, log_operation_success, log_operation_error
from ..domain.orchestration_service import OrchestrationService
from ..use_cases.create_runner import CreateRunner
from ..use_cases.destroy_runner import DestroyRunner
from ..use_cases.cleanup_runners import CleanupRunners
from .request_models import RunnerRequest, CleanupRequest
from .response_models import RunnerResponse, RunnerStatus, CleanupResponse, BatchOperationResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/runners", tags=["runners"])

# Dependencia para obtener el servicio de orquestación
async def get_orchestration_service(request: Request) -> OrchestrationService:
    """Obtiene instancia del servicio de orquestación desde el estado de la aplicación."""
    return request.app.state.orchestration_service


@router.post("/", response_model=BatchOperationResponse)
async def create_runners(
    request: RunnerRequest,
    service: OrchestrationService = Depends(get_orchestration_service)
):
    """
    Crea uno o más runners efímeros.
    
    Args:
        request: Datos para crear runners
        service: Servicio de orquestación
    
    Returns:
        Resultado de la creación
    """
    operation = "create_runners_api"
    log_operation_start(logger, operation, scope=request.scope.value, scope_name=request.scope_name, count=request.count)
    
    try:
        create_use_case = CreateRunner(service)
        
        results = create_use_case.execute(
            scope=request.scope.value,
            scope_name=request.scope_name,
            runner_name=request.runner_name,
            runner_group=request.runner_group,
            labels=request.labels,
            count=request.count
        )
        
        successful = len([r for r in results if r["success"]])
        failed = len(results) - successful
        
        response = BatchOperationResponse(
            success=successful > 0,
            total_operations=len(results),
            successful_operations=successful,
            failed_operations=failed,
            results=results,
            message=f"Operación completada: {successful} exitosos, {failed} fallidos"
        )
        
        log_operation_success(logger, operation, successful=successful, failed=failed)
        return response
        
    except Exception as e:
        log_operation_error(logger, operation, e)
        error_response = ErrorHandler.handle_error(e, operation)
        raise HTTPException(status_code=error_response.status_code, detail=error_response.detail)


@router.delete("/{runner_id}", response_model=RunnerResponse)
async def destroy_runner(
    runner_id: str,
    timeout: int = 30,
    service: OrchestrationService = Depends(get_orchestration_service)
):
    """
    Destruye un runner específico.
    
    Args:
        runner_id: ID del runner a destruir
        timeout: Timeout para destrucción
        service: Servicio de orquestación
    
    Returns:
        Resultado de la destrucción
    """
    operation = "destroy_runner_api"
    log_operation_start(logger, operation, runner_id=runner_id, timeout=timeout)
    
    try:
        destroy_use_case = DestroyRunner(service)
        
        result = destroy_use_case.execute(runner_id, timeout)
        
        response = RunnerResponse(
            success=result["success"],
            runner_id=result["runner_id"],
            message=result["message"],
            error=result.get("error")
        )
        
        log_operation_success(logger, operation, runner_id=runner_id, success=result["success"])
        return response
        
    except Exception as e:
        log_operation_error(logger, operation, e, runner_id=runner_id)
        error_response = ErrorHandler.handle_error(e, operation)
        raise HTTPException(status_code=error_response.status_code, detail=error_response.detail)


@router.get("/{runner_id}/status", response_model=RunnerStatus)
async def get_runner_status(
    runner_id: str,
    service: OrchestrationService = Depends(get_orchestration_service)
):
    """
    Obtiene el estado de un runner.
    
    Args:
        runner_id: ID del runner
        service: Servicio de orquestación
    
    Returns:
        Estado del runner
    """
    operation = "get_runner_status_api"
    log_operation_start(logger, operation, runner_id=runner_id)
    
    try:
        status = service.get_runner_status(runner_id)
        
        response = RunnerStatus(
            runner_id=status.get("runner_id", runner_id),
            status=status.get("status", "unknown"),
            container_id=status.get("container_info", {}).get("id"),
            image=status.get("container_info", {}).get("image"),
            created=status.get("container_info", {}).get("created"),
            updated=status.get("container_info", {}).get("updated"),
            repository=status.get("repository"),
            runner_group=status.get("runner_group"),
            labels=status.get("labels"),
            state=status.get("state"),
            metadata=status.get("container_info", {})
        )
        
        log_operation_success(logger, operation, runner_id=runner_id, status=status.get("status"))
        return response
        
    except Exception as e:
        log_operation_error(logger, operation, e, runner_id=runner_id)
        error_response = ErrorHandler.handle_error(e, operation)
        raise HTTPException(status_code=error_response.status_code, detail=error_response.detail)


@router.get("/", response_model=List[RunnerStatus])
async def list_active_runners(
    service: OrchestrationService = Depends(get_orchestration_service)
):
    """
    Lista todos los runners activos.
    
    Args:
        service: Servicio de orquestación
    
    Returns:
        Lista de runners activos
    """
    operation = "list_active_runners_api"
    log_operation_start(logger, operation)
    
    try:
        runners = service.list_active_runners()
        
        response = []
        for runner_info in runners:
            response.append(RunnerStatus(
                runner_id=runner_info.get("runner_id", "unknown"),
                status=runner_info.get("status", "unknown"),
                container_id=runner_info.get("container_info", {}).get("id"),
                image=runner_info.get("container_info", {}).get("image"),
                created=runner_info.get("container_info", {}).get("created"),
                updated=runner_info.get("container_info", {}).get("updated"),
                repository=runner_info.get("repository"),
                runner_group=runner_info.get("runner_group"),
                labels=runner_info.get("labels"),
                state=runner_info.get("state"),
                metadata=runner_info.get("container_info", {})
            ))
        
        log_operation_success(logger, operation, count=len(response))
        return response
        
    except Exception as e:
        log_operation_error(logger, operation, e)
        error_response = ErrorHandler.handle_error(e, operation)
        raise HTTPException(status_code=error_response.status_code, detail=error_response.detail)


@router.post("/cleanup", response_model=CleanupResponse)
async def cleanup_runners(
    request: CleanupRequest,
    service: OrchestrationService = Depends(get_orchestration_service)
):
    """
    Limpia runners inactivos.
    
    Args:
        request: Parámetros de limpieza
        service: Servicio de orquestación
    
    Returns:
        Resultado de la limpieza
    """
    operation = "cleanup_runners_api"
    log_operation_start(logger, operation, dry_run=request.dry_run, force=request.force)
    
    try:
        cleanup_use_case = CleanupRunners(service)
        
        result = cleanup_use_case.execute(dry_run=request.dry_run)
        
        response = CleanupResponse(
            success=result["success"],
            cleaned_count=result.get("cleaned_count", 0),
            dry_run=request.dry_run,
            candidates_count=result.get("candidates_count"),
            candidates=result.get("candidates"),
            message=result["message"]
        )
        
        log_operation_success(logger, operation, dry_run=request.dry_run, cleaned_count=result.get("cleaned_count", 0))
        return response
        
    except Exception as e:
        log_operation_error(logger, operation, e, dry_run=request.dry_run)
        error_response = ErrorHandler.handle_error(e, operation)
        raise HTTPException(status_code=error_response.status_code, detail=error_response.detail)
