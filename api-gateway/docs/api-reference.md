# API Gateway - Referencia Completa

## 📖 Introducción

El API Gateway es el punto de entrada HTTP público para la plataforma de GitHub Actions Ephemeral Runners. Actúa como intermediario seguro entre los clientes y el orquestador interno, proporcionando validación, logging y manejo de errores robusto.

### Propósito Principal
- **Validación**: Validar todas las solicitudes antes de reenviarlas al orquestador
- **Enrutamiento**: Reenviar solicitudes HTTP al servicio orquestador (puerto 8000)
- **Seguridad**: Implementar CORS, logging y manejo de errores
- **Resiliencia**: Reintentos automáticos con backoff exponencial

### Arquitectura y Flujo de Datos
```
Cliente → API Gateway:8080 → Orquestador:8000 → Docker → Runner
```

### Características Principales
- ✅ **FastAPI Framework**: Alto rendimiento con validación automática
- ✅ **Reintentos Inteligentes**: Backoff exponencial (máx 3 intentos)
- ✅ **Logging Estructurado**: Formato personalizado con filtrado inteligente
- ✅ **Health Checks**: Endpoints especializados para Docker y monitoreo
- ✅ **CORS Configurable**: Soporte para orígenes múltiples
- ✅ **Graceful Shutdown**: Manejo elegante de señales SIGTERM/SIGINT

---

## ⚙️ Configuración

### Variables de Entorno

| Variable | Default | Descripción | Impacto |
|----------|---------|-------------|---------|
| `API_GATEWAY_PORT` | `8080` | Puerto de escucha del servicio | Cambia el puerto de acceso HTTP |
| `ORCHESTRATOR_PORT` | `8000` | Puerto del orquestador interno | Afecta la URL de reenvío |
| `ORCHESTRATOR_URL` | `http://orchestrator:8000` | URL completa del orquestador | Destino de todas las solicitudes |
| `CORS_ORIGINS` | `*` | Orígenes permitidos para CORS | Controla acceso desde navegadores |
| `LOG_LEVEL` | `INFO` | Nivel de logging (DEBUG/INFO/WARNING/ERROR) | Verbosidad de los logs |

### Dependencias y Requisitos

```python
# requirements.txt
fastapi==0.128.0      # Framework web principal
uvicorn==0.40.0       # Servidor ASGI
httpx==0.28.1         # Cliente HTTP asíncrono
pydantic==2.12.5      # Validación de datos
python-dotenv==1.2.1  # Manejo de variables de entorno
```

### Configuración CORS y Logging

#### CORS
- **Allow Credentials**: `true`
- **Allow Methods**: `["GET", "POST", "PUT", "DELETE"]`
- **Allow Headers**: `["*"]` (todos los headers permitidos)

#### Logging
- **Formato**: `%(asctime)s - %(name)s - %(levelname)s - %(message)s`
- **Filtrado Inteligente**: No loguea health checks internos desde localhost
- **User-Agent**: `GHA-API-Gateway/{version}`

---

## 🔐 Autenticación y Seguridad

### Headers Requeridos
```http
Content-Type: application/json
User-Agent: GHA-API-Gateway/1.1.0
```

### Rate Limiting
- Implementado a nivel de middleware de logging
- No hay rate limiting explícito (delegado al orquestador)

### Validaciones de Seguridad
- Validación exhaustiva de todos los inputs
- Sanitización de datos antes del reenvío
- Manejo seguro de errores sin exposición de detalles internos

---

## 🌐 Endpoints API

### Base URL
```
http://localhost:8080/api/v1
```

### 1. Crear Runners
```http
POST /api/v1/runners
```

**Descripción**: Crea nuevos runners efímeros para GitHub Actions

**Request Body**:
```json
{
  "scope": "repo",
  "scope_name": "owner/repo",
  "runner_name": "my-runner-01",
  "runner_group": "default",
  "labels": ["linux", "x64", "self-hosted"],
  "count": 2
}
```

**Response Exitoso (200)**:
```json
{
  "status": "success",
  "data": [
    {
      "runner_id": "runner-abc123",
      "status": "creating",
      "message": "Runner en creación"
    }
  ],
  "message": "Creados 2 runners exitosamente",
  "timestamp": "2024-02-04T23:54:00.000Z"
}
```

**Códigos de Error**:
- `400`: Datos inválidos (scope incorrecto, formato de repo inválido)
- `500`: Error interno del servidor
- `503`: Orquestador no disponible
- `504`: Timeout del orquestador

### 2. Listar Runners Activos
```http
GET /api/v1/runners
```

**Descripción**: Obtiene la lista de todos los runners activos

**Response Exitoso (200)**:
```json
{
  "status": "success",
  "data": [
    {
      "runner_id": "runner-abc123",
      "status": "running",
      "container_id": "container-def456",
      "image": "gha-runner:latest",
      "created": "2024-02-04T23:50:00.000Z",
      "labels": {
        "scope": "repo",
        "scope_name": "owner/repo"
      }
    }
  ],
  "message": "Listados 1 runners activos",
  "timestamp": "2024-02-04T23:54:00.000Z"
}
```

### 3. Obtener Estado de Runner Específico
```http
GET /api/v1/runners/{runner_id}
```

**Parámetros de Path**:
- `runner_id` (string): ID único del runner

**Response Exitoso (200)**:
```json
{
  "status": "success",
  "data": {
    "runner_id": "runner-abc123",
    "status": "running",
    "container_id": "container-def456",
    "image": "gha-runner:latest",
    "created": "2024-02-04T23:50:00.000Z",
    "labels": {
      "scope": "repo",
      "scope_name": "owner/repo"
    }
  },
  "message": "Estado obtenido exitosamente",
  "timestamp": "2024-02-04T23:54:00.000Z"
}
```

**Códigos de Error**:
- `404`: Runner no encontrado

### 4. Destruir Runner
```http
DELETE /api/v1/runners/{runner_id}
```

**Descripción**: Destruye un runner específico y libera recursos

**Response Exitoso (200)**:
```json
{
  "status": "success",
  "data": {
    "runner_id": "runner-abc123",
    "destroyed": true,
    "message": "Runner destruido exitosamente"
  },
  "message": "Runner runner-abc123 destruido exitosamente",
  "timestamp": "2024-02-04T23:54:00.000Z"
}
```

### 5. Limpiar Runners Inactivos
```http
POST /api/v1/runners/cleanup
```

**Descripción**: Elimina todos los runners inactivos o en estado error

**Response Exitoso (200)**:
```json
{
  "status": "success",
  "data": {
    "cleaned_count": 3,
    "cleaned_runners": ["runner-abc123", "runner-def456", "runner-ghi789"]
  },
  "message": "Limpieza completada exitosamente",
  "timestamp": "2024-02-04T23:54:00.000Z"
}
```

### 6. Health Check Completo
```http
GET /api/v1/health
```

**Descripción**: Verifica el estado del gateway y del orquestador

**Response Exitoso (200)**:
```json
{
  "status": "success",
  "data": {
    "status": "healthy",
    "service": "api-gateway",
    "version": "1.1.0",
    "orchestrator": "healthy"
  },
  "message": "Gateway y orchestrator funcionando correctamente",
  "timestamp": "2024-02-04T23:54:00.000Z"
}
```

**Response Degradado (200)**:
```json
{
  "status": "success",
  "data": {
    "status": "degraded",
    "service": "api-gateway",
    "version": "1.1.0",
    "orchestrator": "unreachable"
  },
  "message": "Gateway con problemas en orchestrator",
  "timestamp": "2024-02-04T23:54:00.000Z"
}
```

### 7. Health Check Básico (Docker)
```http
GET /health
```

**Descripción**: Health check básico para Docker, incluye verificación del orquestador

### 8. Health Check Simplificado (Docker)
```http
GET /healthz
```

**Descripción**: Health check mínimo para Docker sin dependencias externas

---

## 📊 Modelos de Datos

### RunnerRequest
```python
class RunnerRequest(BaseModel):
    scope: str = Field(..., description="Tipo de scope: 'repo' u 'org'")
    scope_name: str = Field(..., description="Nombre del repositorio (owner/repo) u organización")
    runner_name: Optional[str] = Field(None, description="Nombre único del runner")
    runner_group: Optional[str] = Field(None, description="Grupo del runner")
    labels: Optional[List[str]] = Field(None, description="Labels para el runner")
    count: int = Field(1, ge=1, le=10, description="Número de runners a crear")
```

**Validaciones**:
- `scope`: Debe ser "repo" u "org"
- `scope_name`: Para scope="repo" debe tener formato "owner/repo"
- `count`: Entero entre 1 y 10
- `labels`: Lista de strings no vacíos

**Ejemplo**:
```json
{
  "scope": "repo",
  "scope_name": "myorg/myrepo",
  "runner_name": "runner-01",
  "labels": ["linux", "x64"],
  "count": 1
}
```

### RunnerResponse
```python
class RunnerResponse(BaseModel):
    runner_id: str
    status: str
    message: str
```

### RunnerStatus
```python
class RunnerStatus(BaseModel):
    runner_id: str
    status: str
    container_id: Optional[str] = None
    image: Optional[str] = None
    created: Optional[str] = None
    labels: Optional[Dict] = None
```

### APIResponse
```python
class APIResponse(BaseModel):
    status: str = "success"
    data: Optional[Any] = None
    message: str = ""
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
```

### ErrorResponse
```python
class ErrorResponse(APIResponse):
    status: str = "error"
    data: Optional[Dict] = None
```

---

## ⚠️ Manejo de Errores

### Códigos de Error HTTP

| Código | Descripción | Causa Común | Solución |
|--------|-------------|-------------|----------|
| `400` | Bad Request | Datos inválidos en el request | Verificar formato y validaciones |
| `404` | Not Found | Runner no existe | Verificar ID del runner |
| `500` | Internal Server Error | Error interno del gateway | Revisar logs del servicio |
| `503` | Service Unavailable | Orquestador no disponible | Verificar estado del orquestador |
| `504` | Gateway Timeout | Timeout del orquestador | Reintentar o verificar carga |

### Formato de Respuestas de Error
```json
{
  "status": "error",
  "data": null,
  "message": "Campo obligatorio faltante: scope",
  "timestamp": "2024-02-04T23:54:00.000Z"
}
```

### Casos de Uso Comunes

#### Error de Validación
```bash
curl -X POST http://localhost:8080/api/v1/runners \
  -H "Content-Type: application/json" \
  -d '{"scope_name": "myorg/myrepo"}'
# Respuesta: 400 - Campo obligatorio faltante: scope
```

#### Formato de Repo Inválido
```bash
curl -X POST http://localhost:8080/api/v1/runners \
  -H "Content-Type: application/json" \
  -d '{"scope": "repo", "scope_name": "myorg"}'
# Respuesta: 400 - Para scope='repo', scope_name debe tener formato owner/repo
```

#### Runner No Encontrado
```bash
curl -X GET http://localhost:8080/api/v1/runners/nonexistent
# Respuesta: 404 - Runner no encontrado
```

---

## 💡 Guías de Uso

### Ejemplos con curl

#### Crear Runner para Repositorio
```bash
curl -X POST http://localhost:8080/api/v1/runners \
  -H "Content-Type: application/json" \
  -d '{
    "scope": "repo",
    "scope_name": "myorg/myrepo",
    "runner_name": "my-runner-01",
    "labels": ["linux", "x64"],
    "count": 1
  }'
```

#### Crear Runner para Organización
```bash
curl -X POST http://localhost:8080/api/v1/runners \
  -H "Content-Type: application/json" \
  -d '{
    "scope": "org",
    "scope_name": "myorg",
    "runner_group": "default",
    "labels": ["linux", "self-hosted"],
    "count": 3
  }'
```

#### Listar Todos los Runners
```bash
curl -X GET http://localhost:8080/api/v1/runners
```

#### Obtener Estado de Runner Específico
```bash
curl -X GET http://localhost:8080/api/v1/runners/runner-abc123
```

#### Destruir Runner
```bash
curl -X DELETE http://localhost:8080/api/v1/runners/runner-abc123
```

#### Limpiar Runners Inactivos
```bash
curl -X POST http://localhost:8080/api/v1/runners/cleanup
```

### Integración con Clientes HTTP

#### Python con httpx
```python
import httpx
import asyncio

async def create_runner():
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8080/api/v1/runners",
            json={
                "scope": "repo",
                "scope_name": "myorg/myrepo",
                "labels": ["linux", "x64"],
                "count": 1
            }
        )
        return response.json()

result = asyncio.run(create_runner())
print(result)
```

#### JavaScript con fetch
```javascript
async function createRunner() {
  const response = await fetch('http://localhost:8080/api/v1/runners', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      scope: 'repo',
      scope_name: 'myorg/myrepo',
      labels: ['linux', 'x64'],
      count: 1
    })
  });
  
  return await response.json();
}

createRunner().then(console.log);
```

### Mejores Prácticas

#### 1. Manejo de Reintentos
El gateway implementa reintentos automáticos, pero se recomienda:
```python
import time
import httpx

async def robust_create_runner(request_data, max_retries=3):
    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    "http://localhost:8080/api/v1/runners",
                    json=request_data
                )
                return response.json()
        except httpx.RequestError as e:
            if attempt == max_retries - 1:
                raise
            time.sleep(2 ** attempt)  # Backoff exponencial
```

#### 2. Validación Local
```python
def validate_runner_request(data):
    required_fields = ["scope", "scope_name"]
    for field in required_fields:
        if field not in data:
            raise ValueError(f"Campo obligatorio faltante: {field}")
    
    if data["scope"] not in ["repo", "org"]:
        raise ValueError("Scope debe ser 'repo' u 'org'")
    
    if data["scope"] == "repo" and "/" not in data["scope_name"]:
        raise ValueError("scope_name debe tener formato owner/repo para scope='repo'")
    
    return True
```

#### 3. Monitoreo de Salud
```python
async def check_gateway_health():
    async with httpx.AsyncClient() as client:
        response = await client.get("http://localhost:8080/health")
        return response.json()

health = asyncio.run(check_gateway_health())
if health["data"]["status"] == "healthy":
    print("Gateway funcionando correctamente")
```

---

## 📋 Referencia Rápida

### Resumen de Endpoints

| Método | Endpoint | Propósito |
|--------|----------|-----------|
| `POST` | `/api/v1/runners` | Crear runners |
| `GET` | `/api/v1/runners` | Listar runners |
| `GET` | `/api/v1/runners/{id}` | Estado de runner |
| `DELETE` | `/api/v1/runners/{id}` | Destruir runner |
| `POST` | `/api/v1/runners/cleanup` | Limpiar inactivos |
| `GET` | `/api/v1/health` | Health completo |
| `GET` | `/health` | Health básico |
| `GET` | `/healthz` | Health mínimo |

### Cheat Sheet de Comandos

```bash
# Crear runner básico
curl -X POST http://localhost:8080/api/v1/runners \
  -H "Content-Type: application/json" \
  -d '{"scope": "repo", "scope_name": "owner/repo"}'

# Verificar salud
curl http://localhost:8080/health

# Listar runners
curl http://localhost:8080/api/v1/runners

# Limpiar todo
curl -X POST http://localhost:8080/api/v1/runners/cleanup
```

### Variables de Entorno Clave
```bash
export API_GATEWAY_PORT=8080
export ORCHESTRATOR_URL=http://orchestrator:8000
export CORS_ORIGINS="*"
export LOG_LEVEL=INFO
```

---

## 🔍 Documentación Adicional

### Swagger UI
- **URL**: `http://localhost:8080/docs`
- **Descripción**: Documentación interactiva auto-generada

### ReDoc
- **URL**: `http://localhost:8080/redoc`
- **Descripción**: Documentación alternativa con mejor visualización

### Logs del Servicio
```bash
# Ver logs en tiempo real
docker logs -f api-gateway

# Logs con nivel DEBUG
LOG_LEVEL=DEBUG docker-compose up api-gateway
```

### Monitoreo
```bash
# Health check para Docker
curl http://localhost:8080/healthz

# Health check completo con orquestador
curl http://localhost:8080/health
```

---

## 📝 Notas de Implementación

### Características Técnicas Avanzadas

#### Reintentos con Backoff Exponencial
- **Máximo de reintentos**: 3
- **Backoff**: 1s, 2s, 4s entre intentos
- **Timeout por solicitud**: 30 segundos

#### Logging Inteligente
- Filtrado automático de health checks internos
- Formato estructurado con timestamp y nivel
- User-Agent personalizado para trazabilidad

#### Graceful Shutdown
- Manejo de señales SIGTERM y SIGINT
- Espera de 5 segundos para finalizar solicitudes en curso
- Cierre ordenado de recursos

### Consideraciones de Rendimiento
- **Concurrencia**: Manejo asíncrono con FastAPI
- **Memoria**: Sin persistencia de estado entre solicitudes
- **CPU**: Procesamiento ligero, delega trabajo al orquestador

### Seguridad
- **Validación de inputs**: Todos los datos son validados
- **Sin estado**: No almacena información sensible
- **Aislamiento**: Contenedor Docker separado

---

*Esta documentación está basada en la versión 1.1.0 del API Gateway. Para la información más actualizada, consulte el código fuente y los endpoints `/docs` y `/redoc` del servicio en ejecución.*
