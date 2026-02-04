import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from request_router import RequestRouter

# Configuración de logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# Modelos de datos
class RunnerRequest(BaseModel):
    scope: str = Field(..., description="Tipo de scope: 'repo' u 'org'")
    scope_name: str = Field(..., description="Nombre del repositorio (owner/repo) u organización")
    runner_name: Optional[str] = Field(None, description="Nombre único del runner")
    runner_group: Optional[str] = Field(None, description="Grupo del runner")
    labels: Optional[List[str]] = Field(None, description="Labels para el runner")
    count: int = Field(1, ge=1, le=10, description="Número de runners a crear")


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


class APIResponse(BaseModel):
    status: str = "success"
    data: Optional[Any] = None
    message: str = ""
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class ErrorResponse(APIResponse):
    status: str = "error"
    data: Optional[Dict] = None


# Variables de entorno
PORT = int(os.getenv("API_GATEWAY_PORT", "8080"))
ORCHESTRATOR_PORT = os.getenv("ORCHESTRATOR_PORT", "8000")
ORCHESTRATOR_URL = f"http://orchestrator:{ORCHESTRATOR_PORT}"
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*")

# Inicializar componentes
router = RequestRouter(ORCHESTRATOR_URL)


# Lifecycle events (reemplaza @app.on_event deprecated)
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Iniciando API Gateway")
    logger.info(f"Orquestador: {ORCHESTRATOR_URL}")
    yield
    # Shutdown
    logger.info("Deteniendo API Gateway")


# Inicialización del servicio
app = FastAPI(
    title="GitHub Actions Ephemeral Runners API Gateway",
    description="Gateway para la plataforma de runners efímeros de GitHub Actions",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Middleware CORS (configurable para diferentes escenarios)
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,  # Configurable via CORS_ORIGINS env var
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)


# Middleware de logging
@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    """Middleware para logging de solicitudes."""
    start_time = datetime.utcnow()

    # Obtener información del cliente
    client_info = {
        "method": request.method,
        "url": str(request.url),
        "ip": request.client.host if request.client else "unknown",
    }

    # Log de solicitud
    logger.info(
        f"Solicitud: {client_info['method']} {client_info['url']} - IP: {client_info['ip']}"
    )

    # Procesar solicitud
    response = await call_next(request)

    # Calcular duración
    process_time = (datetime.utcnow() - start_time).total_seconds()

    # Log de respuesta
    logger.info(f"Respuesta: {response.status_code} - Duración: {process_time:.3f}s")

    return response


# Exception handler personalizado
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Manejador personalizado de excepciones HTTP."""
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(message=exc.detail, data={"error_code": exc.status_code}).dict(),
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Manejador general de excepciones."""
    logger.error(f"Excepción no manejada: {exc}")
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            message="Error interno del servidor", data={"error_type": type(exc).__name__}
        ).dict(),
    )


# Endpoints de la API
# Ver documentación completa en README.md sección "📚 Endpoints de la API"
@app.post("/api/v1/runners", response_model=APIResponse)
async def create_runners(request: RunnerRequest):
    try:
        # Validar solicitud
        router.validate_runner_request(request.dict())

        # Crear runners
        runners = await router.create_runners(request.dict())

        return APIResponse(data=runners, message=f"Creados {len(runners)} runners exitosamente")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creando runners: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")


@app.get("/api/v1/runners/{runner_id}", response_model=APIResponse)
async def get_runner_status(runner_id: str):
    try:
        status = await router.get_runner_status(runner_id)

        return APIResponse(data=status, message="Estado obtenido exitosamente")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error obteniendo estado del runner {runner_id}: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")


@app.delete("/api/v1/runners/{runner_id}", response_model=APIResponse)
async def destroy_runner(runner_id: str):
    try:
        result = await router.destroy_runner(runner_id)

        return APIResponse(data=result, message=f"Runner {runner_id} destruido exitosamente")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error destruyendo runner {runner_id}: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")


@app.get("/api/v1/runners", response_model=APIResponse)
async def list_runners():
    try:
        runners = await router.list_runners()

        return APIResponse(data=runners, message=f"Listados {len(runners)} runners activos")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listando runners: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")


@app.post("/api/v1/runners/cleanup", response_model=APIResponse)
async def cleanup_runners():
    try:
        result = await router.cleanup_runners()

        return APIResponse(data=result, message="Limpieza completada exitosamente")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error en limpieza: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")


# Health checks - Ver README.md sección "Health Checks" para detalles
@app.get("/health", response_model=APIResponse)
async def health_check():
    return APIResponse(
        data={"status": "healthy", "service": "api-gateway", "version": "1.0.0"},
        message="Gateway funcionando correctamente",
    )


@app.get("/healthz", response_model=APIResponse)
async def docker_health_check():
    try:
        # Verificar configuración básica
        return APIResponse(
            data={"status": "healthy", "service": "api-gateway", "version": "1.0.0"},
            message="Gateway saludable",
        )
    except Exception as e:
        logger.error(f"Health check falló: {e}")
        raise HTTPException(status_code=503, detail="Servicio no saludable")


@app.get("/api/v1/health", response_model=APIResponse)
async def full_health_check():
    try:
        # Verificar orquestador
        orchestrator_health = await router.health_check()

        return APIResponse(
            data={
                "gateway": {"status": "healthy", "service": "api-gateway", "version": "1.0.0"},
                "orchestrator": orchestrator_health,
                "system": {
                    "status": (
                        "healthy"
                        if orchestrator_health.get("status") == "healthy"
                        else "degradado"
                    )
                },
            },
            message="Verificación de salud completada",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error en health check: {e}")
        return APIResponse(
            data={
                "gateway": {"status": "healthy", "service": "api-gateway", "version": "1.0.0"},
                "orchestrator": {"status": "unhealthy", "error": str(e)},
                "system": {"status": "degradado"},
            },
            message="Error en verificación de salud",
        )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=PORT)
