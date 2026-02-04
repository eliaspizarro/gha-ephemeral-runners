"""
Rutas de API para health checks y monitoreo.

Rol: Exponer endpoints de salud y estado del sistema.
GET /health, GET /stats, POST /monitoring.
Proporciona información de estado y métricas.
"""

import logging
import time
from datetime import datetime
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import JSONResponse

from ..shared.infrastructure_exceptions import ErrorHandler
from ..shared.logging_utils import log_operation_start, log_operation_success, log_operation_error
from ..domain.orchestration_service import OrchestrationService
from ..use_cases.monitor_workflows import MonitorWorkflows
from ..use_cases.auto_discovery import AutoDiscovery
from .request_models import HealthCheckRequest, ConfigRequest
from .response_models import HealthResponse, StatisticsResponse, MonitoringResponse, DiscoveryResponse, ConfigResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/system", tags=["system"])

# Dependencia para obtener el servicio de orquestación
async def get_orchestration_service(request: Request) -> OrchestrationService:
    """Obtiene instancia del servicio de orquestación desde el estado de la aplicación."""
    return request.app.state.orchestration_service

# Tiempo de inicio del servidor
SERVER_START_TIME = time.time()


@router.get("/health", response_model=HealthResponse)
async def health_check(
    detailed: bool = False,
    include_stats: bool = True,
    include_config: bool = True,
    service: OrchestrationService = Depends(get_orchestration_service)
):
    """
    Verifica el estado de salud del servicio.
    
    Args:
        detailed: Incluir información detallada
        include_stats: Incluir estadísticas
        include_config: Incluir configuración
        service: Servicio de orquestación
    
    Returns:
        Estado de salud del servicio
    """
    operation = "health_check_api"
    log_operation_start(logger, operation, detailed=detailed)
    
    try:
        uptime = int(time.time() - SERVER_START_TIME)
        
        # Estado básico
        status = "healthy"
        message = "Servicio funcionando correctamente"
        
        response = HealthResponse(
            status=status,
            message=message,
            uptime_seconds=uptime,
            version="0.1.0",
            environment="development"
        )
        
        # Agregar información detallada si se solicita
        if detailed:
            try:
                # Estadísticas del servicio
                if include_stats:
                    stats = service.get_statistics()
                    response.stats = stats
                
                # Configuración
                if include_config:
                    response.config = {
                        "poll_interval": service.poll_interval,
                        "cleanup_interval": service.cleanup_interval,
                        "max_runners_per_repo": service.max_runners_per_repo,
                        "monitoring_active": service.monitoring_active
                    }
                
                # Información del sistema
                response.system_stats = {
                    "uptime_seconds": uptime,
                    "memory_usage_mb": 0.0,  # TODO: Implementar
                    "cpu_usage_percent": 0.0,  # TODO: Implementar
                    "disk_usage_gb": 0.0,  # TODO: Implementar
                    "network_connections": 0,  # TODO: Implementar
                    "docker_containers": len(service.active_runners),
                    "python_version": "3.9+",  # TODO: Obtener dinámicamente
                    "git_hash": "unknown",  # TODO: Obtener del repo
                    "build_time": datetime.utcnow().isoformat()
                }
                
            except Exception as e:
                logger.warning(f"Error obteniendo información detallada: {e}")
        
        log_operation_success(logger, operation, status=status, uptime=uptime)
        return response
        
    except Exception as e:
        log_operation_error(logger, operation, e)
        error_response = ErrorHandler.handle_error(e, operation)
        raise HTTPException(status_code=error_response.status_code, detail=error_response.detail)


@router.get("/stats", response_model=StatisticsResponse)
async def get_statistics(
    service: OrchestrationService = Depends(get_orchestration_service)
):
    """
    Obtiene estadísticas del servicio.
    
    Args:
        service: Servicio de orquestación
    
    Returns:
        Estadísticas del servicio
    """
    operation = "get_statistics_api"
    log_operation_start(logger, operation)
    
    try:
        stats = service.get_statistics()
        
        response = StatisticsResponse(
            success=True,
            timestamp=datetime.utcnow(),
            total_runners=stats.get("total_runners", 0),
            state_distribution=stats.get("state_distribution", {}),
            repository_distribution=stats.get("repository_distribution", {}),
            monitoring_active=stats.get("monitoring_active", False),
            last_cleanup_time=stats.get("last_cleanup_time", ""),
            errors_count=0,  # TODO: Implementar contador de errores
            uptime_seconds=int(time.time() - SERVER_START_TIME),
            repositories_with_demand=0  # TODO: Implementar desde GitHub service
        )
        
        log_operation_success(logger, operation, total_runners=stats.get("total_runners", 0))
        return response
        
    except Exception as e:
        log_operation_error(logger, operation, e)
        error_response = ErrorHandler.handle_error(e, operation)
        raise HTTPException(status_code=error_response.status_code, detail=error_response.detail)


@router.post("/monitoring/start", response_model=MonitoringResponse)
async def start_monitoring(
    poll_interval: Optional[int] = None,
    cleanup_interval: Optional[int] = None,
    service: OrchestrationService = Depends(get_orchestration_service)
):
    """
    Inicia el monitoreo automático.
    
    Args:
        poll_interval: Intervalo de polling
        cleanup_interval: Intervalo de limpieza
        service: Servicio de orquestación
    
    Returns:
        Resultado del inicio
    """
    operation = "start_monitoring_api"
    log_operation_start(logger, operation, poll_interval=poll_interval, cleanup_interval=cleanup_interval)
    
    try:
        # Crear caso de uso de monitoreo
        monitor_use_case = MonitorWorkflows(service)
        
        result = monitor_use_case.start_monitoring(poll_interval, cleanup_interval)
        
        response = MonitoringResponse(
            success=result["success"],
            monitoring_active=result["monitoring_active"],
            message=result["message"],
            poll_interval=result.get("poll_interval"),
            cleanup_interval=result.get("cleanup_interval"),
            total_cycles=result.get("total_cycles", 0),
            errors_count=result.get("errors_count", 0),
            last_check_time=result.get("last_check_time")
        )
        
        log_operation_success(logger, operation, monitoring_active=result["monitoring_active"])
        return response
        
    except Exception as e:
        log_operation_error(logger, operation, e)
        error_response = ErrorHandler.handle_error(e, operation)
        raise HTTPException(status_code=error_response.status_code, detail=error_response.detail)


@router.post("/monitoring/stop", response_model=MonitoringResponse)
async def stop_monitoring(
    service: OrchestrationService = Depends(get_orchestration_service)
):
    """
    Detiene el monitoreo automático.
    
    Args:
        service: Servicio de orquestación
    
    Returns:
        Resultado de la detención
    """
    operation = "stop_monitoring_api"
    log_operation_start(logger, operation)
    
    try:
        # Crear caso de uso de monitoreo
        monitor_use_case = MonitorWorkflows(service)
        
        result = monitor_use_case.stop_monitoring()
        
        response = MonitoringResponse(
            success=result["success"],
            monitoring_active=result["monitoring_active"],
            message=result["message"],
            total_cycles=result.get("total_cycles", 0),
            errors_count=result.get("errors_count", 0)
        )
        
        log_operation_success(logger, operation, monitoring_active=result["monitoring_active"])
        return response
        
    except Exception as e:
        log_operation_error(logger, operation, e)
        error_response = ErrorHandler.handle_error(e, operation)
        raise HTTPException(status_code=error_response.status_code, detail=error_response.detail)


@router.get("/monitoring/status", response_model=MonitoringResponse)
async def get_monitoring_status(
    service: OrchestrationService = Depends(get_orchestration_service)
):
    """
    Obtiene el estado del monitoreo.
    
    Args:
        service: Servicio de orquestación
    
    Returns:
        Estado del monitoreo
    """
    operation = "get_monitoring_status_api"
    log_operation_start(logger, operation)
    
    try:
        # Crear caso de uso de monitoreo
        monitor_use_case = MonitorWorkflows(service)
        
        status = monitor_use_case.get_monitoring_status()
        
        response = MonitoringResponse(
            success=True,
            monitoring_active=status["monitoring_active"],
            message="Estado del monitoreo",
            poll_interval=status["poll_interval"],
            cleanup_interval=status["cleanup_interval"],
            total_cycles=status["stats"]["total_cycles"],
            errors_count=status["stats"]["errors_count"]
        )
        
        log_operation_success(logger, operation, monitoring_active=status["monitoring_active"])
        return response
        
    except Exception as e:
        log_operation_error(logger, operation, e)
        error_response = ErrorHandler.handle_error(e, operation)
        raise HTTPException(status_code=error_response.status_code, detail=error_response.detail)


@router.post("/discovery/execute", response_model=DiscoveryResponse)
async def execute_discovery(
    dry_run: bool = False,
    service: OrchestrationService = Depends(get_orchestration_service)
):
    """
    Ejecuta el descubrimiento automático de repositorios.
    
    Args:
        dry_run: Simular sin crear runners
        service: Servicio de orquestación
    
    Returns:
        Resultado del descubrimiento
    """
    operation = "execute_discovery_api"
    log_operation_start(logger, operation, dry_run=dry_run)
    
    try:
        # Crear caso de uso de descubrimiento
        discovery_use_case = AutoDiscovery(service)
        
        result = discovery_use_case.execute(dry_run=dry_run)
        
        response = DiscoveryResponse(
            success=result["success"],
            repositories_found=result["repositories_found"],
            repositories_processed=result["repositories_processed"],
            runners_created=result["runners_created"],
            dry_run=dry_run,
            processed_repos=result.get("processed_repos"),
            message=result["message"],
            execution_time=result.get("execution_time")
        )
        
        log_operation_success(logger, operation, dry_run=dry_run, repositories_found=result["repositories_found"])
        return response
        
    except Exception as e:
        log_operation_error(logger, operation, e, dry_run=dry_run)
        error_response = ErrorHandler.handle_error(e, operation)
        raise HTTPException(status_code=error_response.status_code, detail=error_response.detail)


@router.post("/config/update", response_model=ConfigResponse)
async def update_config(
    request: ConfigRequest,
    service: OrchestrationService = Depends(get_orchestration_service)
):
    """
    Actualiza la configuración del servicio.
    
    Args:
        request: Parámetros de configuración
        service: Servicio de orquestación
    
    Returns:
        Resultado de la actualización
    """
    operation = "update_config_api"
    log_operation_start(logger, operation)
    
    try:
        # Guardar configuración anterior
        previous_config = {
            "poll_interval": service.poll_interval,
            "cleanup_interval": service.cleanup_interval,
            "max_runners_per_repo": service.max_runners_per_repo,
            "auto_create_runners": getattr(service, "auto_create_runners", False)
        }
        
        # Actualizar configuración
        changes = []
        if request.poll_interval is not None:
            service.poll_interval = request.poll_interval
            changes.append(f"poll_interval: {previous_config['poll_interval']} -> {request.poll_interval}")
        
        if request.cleanup_interval is not None:
            service.cleanup_interval = request.cleanup_interval
            changes.append(f"cleanup_interval: {previous_config['cleanup_interval']} -> {request.cleanup_interval}")
        
        if request.max_runners_per_repo is not None:
            service.max_runners_per_repo = request.max_runners_per_repo
            changes.append(f"max_runners_per_repo: {previous_config['max_runners_per_repo']} -> {request.max_runners_per_repo}")
        
        if request.auto_create_runners is not None:
            service.auto_create_runners = request.auto_create_runners
            changes.append(f"auto_create_runners: {previous_config['auto_create_runners']} -> {request.auto_create_runners}")
        
        updated_config = {
            "poll_interval": service.poll_interval,
            "cleanup_interval": service.cleanup_interval,
            "max_runners_per_repo": service.max_runners_per_repo,
            "auto_create_runners": getattr(service, "auto_create_runners", False)
        }
        
        response = ConfigResponse(
            success=True,
            message="Configuración actualizada exitosamente",
            updated_config=updated_config,
            previous_config=previous_config,
            changes=changes
        )
        
        log_operation_success(logger, operation, changes=len(changes))
        return response
        
    except Exception as e:
        log_operation_error(logger, operation, e)
        error_response = ErrorHandler.handle_error(e, operation)
        raise HTTPException(status_code=error_response.status_code, detail=error_response.detail)
