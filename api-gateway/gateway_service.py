import os
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from .request_router import RequestRouter
from .authentication import AuthenticationLayer, RateLimiter

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
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

# Inicialización del servicio
app = FastAPI(
    title="GitHub Actions Ephemeral Runners API Gateway",
    description="Gateway para la plataforma de runners efímeros de GitHub Actions",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Variables de entorno
PORT = int(os.getenv("PORT", "8080"))
ORCHESTRATOR_URL = os.getenv("ORCHESTRATOR_URL")
API_KEY = os.getenv("API_KEY")
ENABLE_AUTH = os.getenv("ENABLE_AUTH", "false").lower() == "true"
MAX_REQUESTS = int(os.getenv("MAX_REQUESTS", "100"))
RATE_WINDOW = int(os.getenv("RATE_WINDOW", "60"))

# Validar variables obligatorias
if not ORCHESTRATOR_URL:
    logger.error("ORCHESTRATOR_URL es obligatorio")
    raise RuntimeError("ORCHESTRATOR_URL es obligatorio")

# Inicializar componentes
router = RequestRouter(ORCHESTRATOR_URL, API_KEY)
auth = AuthenticationLayer(API_KEY, ENABLE_AUTH)
rate_limiter = RateLimiter(MAX_REQUESTS, RATE_WINDOW)

# Middleware CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configurar según necesidad
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Middleware de logging
@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    """Middleware para logging de solicitudes."""
    start_time = datetime.utcnow()
    
    # Obtener información del cliente
    client_info = auth.get_client_info(request)
    
    # Log de solicitud
    logger.info(f"Solicitud: {client_info['method']} {client_info['url']} - IP: {client_info['ip']}")
    
    # Procesar solicitud
    response = await call_next(request)
    
    # Calcular duración
    process_time = (datetime.utcnow() - start_time).total_seconds()
    
    # Log de respuesta
    logger.info(f"Respuesta: {response.status_code} - Duración: {process_time:.3f}s")
    
    return response

# Middleware de rate limiting y autenticación
@app.middleware("http")
async def auth_rate_limit_middleware(request: Request, call_next):
    """Middleware de autenticación y rate limiting."""
    try:
        # Rate limiting
        await rate_limiter.check_rate_limit(request.client.host if request.client else "unknown")
        
        # Autenticación (solo para endpoints que lo requieren)
        if request.url.path.startswith("/api/v1/"):
            await auth.verify_api_key(request)
        
        return await call_next(request)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error en middleware: {e}")
        raise HTTPException(status_code=500, detail="Error interno del gateway")

# Exception handler personalizado
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Manejador personalizado de excepciones HTTP."""
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            message=exc.detail,
            data={"error_code": exc.status_code}
        ).dict()
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Manejador general de excepciones."""
    logger.error(f"Excepción no manejada: {exc}")
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            message="Error interno del servidor",
            data={"error_type": type(exc).__name__}
        ).dict()
    )

# Endpoints de la API
@app.post("/api/v1/runners", response_model=APIResponse)
async def create_runners(request: RunnerRequest):
    """
    Crea uno o más runners efímeros.
    
    Args:
        request: Parámetros para crear runners
        
    Returns:
        Lista de runners creados
    """
    try:
        # Validar solicitud
        router.validate_runner_request(request.dict())
        
        # Crear runners
        runners = await router.create_runners(request.dict())
        
        return APIResponse(
            data=runners,
            message=f"Creados {len(runners)} runners exitosamente"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creando runners: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")

@app.get("/api/v1/runners/{runner_id}", response_model=APIResponse)
async def get_runner_status(runner_id: str):
    """
    Obtiene el estado de un runner específico.
    
    Args:
        runner_id: ID del runner
        
    Returns:
        Estado del runner
    """
    try:
        status = await router.get_runner_status(runner_id)
        
        return APIResponse(
            data=status,
            message="Estado obtenido exitosamente"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error obteniendo estado del runner {runner_id}: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")

@app.delete("/api/v1/runners/{runner_id}", response_model=APIResponse)
async def destroy_runner(runner_id: str):
    """
    Destruye un runner específico.
    
    Args:
        runner_id: ID del runner a destruir
        
    Returns:
        Confirmación de destrucción
    """
    try:
        result = await router.destroy_runner(runner_id)
        
        return APIResponse(
            data=result,
            message=f"Runner {runner_id} destruido exitosamente"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error destruyendo runner {runner_id}: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")

@app.get("/api/v1/runners", response_model=APIResponse)
async def list_runners():
    """
    Lista todos los runners activos.
    
    Returns:
        Lista de runners activos
    """
    try:
        runners = await router.list_runners()
        
        return APIResponse(
            data=runners,
            message=f"Listados {len(runners)} runners activos"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listando runners: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")

@app.post("/api/v1/runners/cleanup", response_model=APIResponse)
async def cleanup_runners():
    """
    Limpia runners inactivos.
    
    Returns:
        Resultado de la limpieza
    """
    try:
        result = await router.cleanup_runners()
        
        return APIResponse(
            data=result,
            message="Limpieza completada exitosamente"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error en limpieza: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")

# Endpoints de health check
@app.get("/health", response_model=APIResponse)
async def health_check():
    """
    Verificación básica de salud del gateway.
    
    Returns:
        Estado del servicio
    """
    return APIResponse(
        data={
            "status": "healthy",
            "service": "api-gateway",
            "version": "1.0.0",
            "auth_enabled": ENABLE_AUTH,
            "rate_limiting": {
                "max_requests": MAX_REQUESTS,
                "rate_window": RATE_WINDOW
            }
        },
        message="Gateway funcionando correctamente"
    )

@app.get("/healthz", response_model=APIResponse)
async def kubernetes_health_check():
    """
    Health check nativo para Kubernetes.
    Retorna HTTP 200 para healthy, HTTP 503 para unhealthy.
    
    Returns:
        Estado del servicio para Kubernetes
    """
    try:
        # Verificar configuración básica
        if not ENABLE_AUTH or not MAX_REQUESTS or not RATE_WINDOW:
            raise HTTPException(status_code=503, detail="Configuración del servicio inválida")
        
        return APIResponse(
            data={
                "status": "healthy",
                "service": "api-gateway",
                "version": "1.0.0"
            },
            message="Gateway saludable"
        )
    except Exception as e:
        logger.error(f"Health check falló: {e}")
        raise HTTPException(status_code=503, detail="Servicio no saludable")

@app.get("/api/v1/health", response_model=APIResponse)
async def full_health_check():
    """
    Verificación completa de salud incluyendo orquestador.
    
    Returns:
        Estado completo del sistema
    """
    try:
        # Verificar orquestador
        orchestrator_health = await router.health_check()
        
        return APIResponse(
            data={
                "gateway": {
                    "status": "healthy",
                    "service": "api-gateway",
                    "version": "1.0.0"
                },
                "orchestrator": orchestrator_health,
                "system": {
                    "status": "healthy" if orchestrator_health.get("status") == "healthy" else "degradado",
                    "auth_enabled": ENABLE_AUTH,
                    "rate_limiting": {
                        "max_requests": MAX_REQUESTS,
                        "window_seconds": RATE_WINDOW
                    }
                }
            },
            message="Verificación de salud completada"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error en health check: {e}")
        return APIResponse(
            data={
                "gateway": {
                    "status": "healthy",
                    "service": "api-gateway",
                    "version": "1.0.0"
                },
                "orchestrator": {
                    "status": "unhealthy",
                    "error": str(e)
                },
                "system": {
                    "status": "degradado",
                    "auth_enabled": ENABLE_AUTH,
                    "rate_limiting": {
                        "max_requests": MAX_REQUESTS,
                        "window_seconds": RATE_WINDOW
                    }
                }
            },
            message="Error en verificación de salud"
        )

# Eventos de startup/shutdown
@app.on_event("startup")
async def startup_event():
    """Inicialización del gateway."""
    logger.info("Iniciando API Gateway")
    logger.info(f"Orquestador: {ORCHESTRATOR_URL}")
    logger.info(f"Autenticación: {'habilitada' if ENABLE_AUTH else 'deshabilitada'}")
    logger.info(f"Rate limiting: {MAX_REQUESTS} solicitudes por {RATE_WINDOW}s")
    logger.info("API Gateway iniciado exitosamente")

@app.on_event("shutdown")
async def shutdown_event():
    """Limpieza al detener el gateway."""
    logger.info("Deteniendo API Gateway")
    # Limpiar rate limiter
    rate_limiter.cleanup_old_entries()
    logger.info("API Gateway detenido")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=PORT)
