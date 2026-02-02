# Implementación del Orquestador

## Responsabilidad Principal
Gestionar el ciclo de vida de runners efímeros: generar tokens, crear contenedores y coordinar su destrucción.

## Inputs
- GITHUB_TOKEN: Token de GitHub con permisos para generar registration tokens
- SCOPE: Tipo de scope (repo/org)
- SCOPE_NAME: Nombre del repositorio u organización
- RUNNER_COUNT: Número de runners a crear (opcional, default: 1)

## Outputs
- Runner IDs generados
- Estados de los runners
- Logs de creación/destrucción

## Componentes a Implementar

### 1. Token Generator
- Función para generar registration tokens via GitHub API
- Soporte para repo y org scope
- Manejo de errores de API

### 2. Container Manager
- Crear contenedores Docker para runners
- Inyectar registration token como variable de entorno
- Configurar nombre y etiquetas del contenedor

### 3. Lifecycle Manager
- Monitorear estado de runners
- Coordinar destrucción automática
- Limpieza de recursos

## Requerimientos Técnicos
- Lenguaje: Python 3.11+
- Dependencias: requests, docker
- Variables de entorno obligatorias
- Logs estructurados
- Salida con código de error en fallos

## API Interna
- POST /runners/create
- GET /runners/{id}/status
- DELETE /runners/{id}
