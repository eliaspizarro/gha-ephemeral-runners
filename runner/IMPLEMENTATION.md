# Implementación del Runner

## Responsabilidad Principal
Ejecutar jobs de GitHub Actions como contenedor efímero y autodestruirse después de completar el trabajo.

## Inputs
- GITHUB_REGISTRATION_TOKEN: Token temporal para registro
- RUNNER_NAME: Nombre único del runner
- RUNNER_GROUP: Grupo de runners (opcional)
- SCOPE: Tipo de scope (repo/org)
- SCOPE_NAME: Nombre del repositorio u organización

## Outputs
- Estado de registro
- Logs de ejecución de jobs
- Código de salida del job

## Componentes a Implementar

### 1. Registration Service
- Registrar runner con GitHub usando el token proporcionado
- Configurar runner con scope específico
- Manejar errores de registro

### 2. Job Executor
- Iniciar el listener de GitHub Actions
- Ejecutar jobs recibidos
- Reportar resultados a GitHub

### 3. Self-Destruct Mechanism
- Autodestruirse después de completar jobs
- Timeout para runners inactivos
- Limpieza de recursos locales

## Requerimientos Técnicos
- Basado en imagen oficial de GitHub Actions runner
- Entrypoint personalizado
- Manejo de señales (SIGTERM, SIGINT)
- Variables de entorno obligatorias
- Logs estructurados

## Configuración
- Nombre único generado automáticamente si no se proporciona
- Labels configurables vía variables de entorno
- Timeout configurable para inactividad
