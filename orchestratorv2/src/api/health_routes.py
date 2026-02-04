"""
Endpoints de health checks y estado del sistema.

Rol: Proveer endpoints para monitoreo de salud del servicio.
GET /health, GET /status, GET /metrics.
Usado por orquestadores de contenedores y sistemas de monitoreo.

Depende de: casos de uso de monitoreo, FastAPI.
"""

# HealthRoutes: Endpoints para health checks
# Operaciones: health_check, system_status, metrics
# Retorna estado de servicios, configuración y métricas básicas
