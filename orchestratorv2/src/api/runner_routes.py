"""
Endpoints específicos para gestión de runners.

Rol: Exponer endpoints REST para operaciones de runners.
POST /runners/create, DELETE /runners/{id}, GET /runners, POST /runners/cleanup.
Convierte requests HTTP a llamadas a casos de uso.

Depende de: casos de uso, schemas Pydantic, FastAPI.
"""

# RunnerRoutes: Endpoints CRUD y operaciones específicas
# Operaciones: create, destroy, list, cleanup, status
# Maneja validación de requests y formateo de responses
