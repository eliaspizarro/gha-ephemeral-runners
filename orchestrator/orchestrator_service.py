import os
import logging
from typing import Dict, List, Optional
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from .lifecycle_manager import LifecycleManager

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Modelos de datos
class RunnerRequest(BaseModel):
    scope: str
    scope_name: str
    runner_name: Optional[str] = None
    runner_group: Optional[str] = None
    labels: Optional[List[str]] = None
    count: int = 1

class RunnerResponse(BaseModel):
    runner_id: str
    status: str
    message: str

class RunnerStatus(BaseModel):
    runner_id: str
    status: str
    container_id: Optional[str] = None
    image: Optional[str] = None
    created: Optional[str] = None
    labels: Optional[Dict] = None

# Lifecycle events (reemplaza @app.on_event deprecated)
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Iniciando servicio de orquestador")
    # Iniciar monitoreo automático
    lifecycle_manager.start_monitoring()
    logger.info("Servicio iniciado exitosamente")
    
    yield
    
    # Shutdown
    logger.info("Deteniendo servicio de orquestador")
    lifecycle_manager.stop_monitoring()
    logger.info("Servicio detenido")

# Inicialización del servicio
app = FastAPI(
    title="GitHub Actions Ephemeral Runners Orchestrator",
    description="Servicio para gestionar runners efímeros de GitHub Actions",
    version="1.0.0",
    lifespan=lifespan
)

# Variables de entorno obligatorias
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
RUNNER_IMAGE = "ghcr.io/github-runner-images/ubuntu-latest:latest"

if not GITHUB_TOKEN:
    logger.error("GITHUB_TOKEN es obligatorio")
    raise RuntimeError("GITHUB_TOKEN es obligatorio")

# Inicializar Lifecycle Manager
lifecycle_manager = LifecycleManager(GITHUB_TOKEN, RUNNER_IMAGE)

@app.post("/runners/create", response_model=List[RunnerResponse])
async def create_runners(request: RunnerRequest):
    # Crea uno o más runners efímeros
    try:
        if request.count < 1 or request.count > 10:
            raise HTTPException(
                status_code=400,
                detail="El número de runners debe estar entre 1 y 10"
            )

        runners = []
        for i in range(request.count):
            runner_name = request.runner_name
            if request.count > 1:
                runner_name = f"{request.runner_name}-{i+1}" if request.runner_name else None
            
            runner_id = lifecycle_manager.create_runner(
                scope=request.scope,
                scope_name=request.scope_name,
                runner_name=runner_name,
                runner_group=request.runner_group,
                labels=request.labels
            )

            runners.append(RunnerResponse(
                runner_id=runner_id,
                status="created",
                message="Runner creado exitosamente"
            ))

        logger.info(f"Creados {len(runners)} runners para {request.scope}/{request.scope_name}")
        return runners

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creando runners: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")

@app.get("/runners/{runner_id}/status", response_model=RunnerStatus)
async def get_runner_status(runner_id: str):
    # Obtiene el estado de un runner específico
    try:
        status = lifecycle_manager.get_runner_status(runner_id)

        if status["status"] == "not_found":
            raise HTTPException(status_code=404, detail="Runner no encontrado")

        return RunnerStatus(**status)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error obteniendo estado del runner {runner_id}: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")

@app.delete("/runners/{runner_id}")
async def destroy_runner(runner_id: str):
    # Destruye un runner específico
    try:
        success = lifecycle_manager.destroy_runner(runner_id)

        if not success:
            raise HTTPException(
                status_code=404,
                detail="Runner no encontrado o no se pudo destruir"
            )

        return {"message": f"Runner {runner_id} destruido exitosamente"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error destruyendo runner {runner_id}: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")

@app.get("/runners", response_model=List[RunnerStatus])
async def list_runners():
    # Lista todos los runners activos
    try:
        runners = lifecycle_manager.list_active_runners()
        return [RunnerStatus(**runner) for runner in runners]
    except Exception as e:
        logger.error(f"Error listando runners: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")

@app.post("/runners/cleanup")
async def cleanup_runners():
    # Limpia runners inactivos
    try:
        cleaned = lifecycle_manager.cleanup_inactive_runners()
        return {"cleaned_runners": cleaned, "message": f"Limpiados {cleaned} runners"}
    except Exception as e:
        logger.error(f"Error en limpieza: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")

@app.get("/health")
async def health_check():
    # Verificación de salud del servicio
    return {
        "status": "healthy",
        "service": "orchestrator",
        "active_runners": len(lifecycle_manager.active_runners),
        "monitoring": lifecycle_manager.monitoring
    }

@app.get("/healthz")
async def docker_health_check():
    # Health check nativo para Docker
    # Retorna HTTP 200 para healthy, HTTP 503 para unhealthy
    try:
        # Verificar estado del lifecycle manager
        if not hasattr(lifecycle_manager, 'active_runners'):
            raise HTTPException(status_code=503, detail="Lifecycle manager no inicializado")
        
        # Verificar que el número de runners activos sea manejable
        active_count = len(lifecycle_manager.active_runners)
        if active_count > 100:  # Límite razonable
            raise HTTPException(status_code=503, detail=f"Demasiados runners activos: {active_count}")
        
        return {
            "status": "healthy",
            "service": "orchestrator",
            "active_runners": active_count,
            "monitoring": lifecycle_manager.monitoring
        }
    except Exception as e:
        logger.error(f"Health check falló: {e}")
        raise HTTPException(status_code=503, detail="Servicio no saludable")

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("ORCHESTRATOR_PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
