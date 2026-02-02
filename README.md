# GitHub Actions Ephemeral Runners

Plataforma para crear y destruir runners self-hosted de GitHub Actions de forma EFÍMERA usando contenedores Docker.

## Características

- **Efímeros**: Crear → Usar → Destruir
- **Seguros**: Tokens temporales, sin persistencia de datos sensibles
- **Escalables**: Creación masiva de runners
- **Minimalistas**: Sin monitoreo ni métricas innecesarias
- **Repo-first**: Despliegue sin infraestructura previa

## Arquitectura

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│ API Gateway │────│ Orquestador │────│   Runner    │
│   (HTTP)    │    │  (Tokens)   │    │ (Ephemeral) │
└─────────────┘    └─────────────┘    └─────────────┘
```

### Componentes

1. **API Gateway**: Punto de entrada HTTP, autenticación y rate limiting
2. **Orquestador**: Genera tokens, crea contenedores, gestiona ciclo de vida
3. **Runner**: Contenedor efímero que ejecuta jobs y se autodestruye

## Requisitos

- Docker
- Docker Compose
- Token de GitHub con permisos para generar registration tokens

## Instalación

### Opción 1: Usando imágenes del Registry (Recomendado)

1. **Clonar repositorio**:
   ```bash
   git clone <repository-url>
   cd gha-ephemeral-runners
   ```

2. **Configurar variables de entorno**:
   ```bash
   cp .env.example .env
   # Editar .env con tu GITHUB_TOKEN y otras configuraciones
   ```

3. **Desplegar**:
   ```bash
   python3 deploy_registry.py
   ```

### Opción 2: Build local

1. **Configurar variables de entorno**:
   ```bash
   cp .env.example .env
   # Editar .env con tu GITHUB_TOKEN y otras configuraciones
   ```

2. **Construir y subir imágenes**:
   ```bash
   python3 build_and_push.py --username TU_USUARIO --password TU_PASSWORD
   ```

3. **Desplegar**:
   ```bash
   python3 deploy_registry.py
   ```

## Configuración

### Variables de Entorno Obligatorias

- `GITHUB_TOKEN`: Token de GitHub con permisos para generar registration tokens

### Variables Opcionales

- `PORT`: Puerto del API Gateway (default: 8080)
- `API_KEY`: Clave para autenticación del API Gateway
- `ENABLE_AUTH`: Habilitar autenticación (default: false)
- `MAX_REQUESTS`: Límite de rate limiting (default: 100)
- `RATE_WINDOW`: Ventana de rate limiting en segundos (default: 60)
- `RUNNER_IMAGE`: Imagen Docker para runners (default: gha-runner:latest)
- `IDLE_TIMEOUT`: Timeout de inactividad para runners (default: 3600)

## Uso

### Crear Runners

```bash
# Para un repositorio específico
curl -X POST http://localhost:8080/api/v1/runners \
  -H 'Content-Type: application/json' \
  -d '{
    "scope": "repo",
    "scope_name": "owner/repo",
    "count": 2,
    "labels": ["linux", "x64"]
  }'

# Para una organización
curl -X POST http://localhost:8080/api/v1/runners \
  -H 'Content-Type: application/json' \
  -d '{
    "scope": "org",
    "scope_name": "my-org",
    "count": 1
  }'
```

### Listar Runners Activos

```bash
curl http://localhost:8080/api/v1/runners
```

### Obtener Estado de un Runner

```bash
curl http://localhost:8080/api/v1/runners/{runner_id}
```

### Destruir un Runner

```bash
curl -X DELETE http://localhost:8080/api/v1/runners/{runner_id}
```

### Limpieza de Runners Inactivos

```bash
curl -X POST http://localhost:8080/api/v1/runners/cleanup
```

## API Documentation

Una vez desplegado, visita:
- **Swagger UI**: http://localhost:8080/docs
- **ReDoc**: http://localhost:8080/redoc

## Comandos de Gestión

```bash
# Ver estado de los servicios
python3 deploy_registry.py status

# Ver logs en tiempo real
python3 deploy_registry.py logs

# Verificar salud de los servicios
python3 deploy_registry.py health

# Reiniciar servicios
python3 deploy_registry.py restart

# Actualizar imágenes del registry
python3 deploy_registry.py pull

# Detener todos los servicios
python3 deploy_registry.py stop

# Verificar imágenes locales
python3 deploy_registry.py verify
```

## Flujo de Ejecución

1. **Solicitud**: Cliente solicita runner vía API Gateway
2. **Token**: Orquestador genera registration token temporal
3. **Contenedor**: Orquestador crea contenedor Docker con token
4. **Registro**: Runner se registra con GitHub usando el token
5. **Ejecución**: Runner recibe y ejecuta jobs
6. **Autodestrucción**: Runner se elimina automáticamente

## Seguridad

- **Tokens temporales**: Los registration tokens expiran rápidamente
- **Sin persistencia**: Ningún token sensible persiste en contenedores
- **Aislamiento**: Cada runner es un contenedor aislado
- **Autenticación opcional**: API Gateway puede requerir API key

## Monitoreo

El sistema está diseñado para ser minimalista sin monitoreo incorporado. Para monitoreo externo:

- **Health checks**: `/health` y `/api/v1/health`
- **Logs**: Disponibles vía `docker-compose logs`
- **Métricas**: Pueden agregarse externamente si es necesario

## Troubleshooting

### Runner no se registra

1. Verificar que `GITHUB_TOKEN` tenga permisos adecuados
2. Confirmar que `scope_name` sea correcto
3. Revisar logs del orquestador: `./deploy.sh logs`

### Contenedor no se inicia

1. Verificar que Docker esté corriendo
2. Confirmar acceso a Docker socket
3. Revisar logs de construcción: `docker-compose build`

### API Gateway no responde

1. Verificar que el puerto esté disponible
2. Confirmar configuración de red
3. Revisar logs del gateway: `./deploy.sh logs gateway`

## Licencia

MIT License - ver archivo LICENSE para detalles.
