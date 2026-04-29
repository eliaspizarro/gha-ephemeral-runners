# Limpieza de Runners Offline en GitHub

## Problema

Los runners efímeros dejan entradas "offline" en GitHub después de ser destruidos localmente:
```
GitHub Settings > Actions > Runners:
auto-runner-12345 [offline]  <- Sigue apareciendo
auto-runner-12346 [offline]  <- Sigue apareciendo
```

## Solución Implementada

He creado un sistema de limpieza automática para eliminar runners offline de GitHub API.

### Componentes

1. **GitHubRunnerCleanup** (`orchestrator/src/core/github_cleanup.py`)
   - Consulta GitHub API para encontrar runners offline
   - Elimina runners offline via API calls
   - Soporte para diferentes ámbitos (user, repo, org)

2. **Integración en LifecycleManager**
   - Se ejecuta automáticamente después de limpieza local
   - Configurable via variable de entorno

### Configuración

Agrega esta variable a tu `.env`:

```bash
# Activar limpieza automática de runners offline en GitHub
GITHUB_CLEANUP_ENABLED=true
```

### Modos de Operación

#### Automático (Recomendado)
- Se ejecuta cada `RUNNER_PURGE_INTERVAL` segundos
- Limpia runners offline después de limpieza local
- Zero configuration después de activar

#### Manual via API
```bash
# Limpiar runners offline (producción)
curl -X POST http://localhost:8080/api/v1/runners/cleanup-github

# Modo prueba (solo muestra lo que se eliminaría)
curl -X POST http://localhost:8080/api/v1/runners/cleanup-github?dry_run=true
```

### Endpoints Disponibles

```bash
# API Gateway (8080)
POST /api/v1/runners/cleanup-github     - Limpieza de GitHub
GET  /api/v1/runners/github-status     - Estado de runners en GitHub

# Orchestrator (8000) - Interno
POST /runners/cleanup-github            - Limpieza directa
```

### Logs Esperados

```
2026-04-29 22:56:21 | INFO | CONFIG | Limpiando runners offline de GitHub
2026-04-29 22:56:22 | INFO | GitHub runners: 5 totales, 3 offline
2026-04-29 22:56:23 | INFO | Eliminando runner offline: auto-runner-12345 (ID: 67890)
2026-04-29 22:56:24 | INFO | Runner 67890 eliminado de GitHub
2026-04-29 22:56:25 | SUCCESS | Cleanup GitHub: 3/3 runners eliminados
```

### Seguridad

- **Solo runners offline**: Nunca elimina runners activos
- **Token con scopes adecuados**: Requiere `repo` y `admin:org`
- **Logging completo**: Todas las acciones son registradas
- **Dry run mode**: Modo prueba para verificar antes de ejecutar

### Activación

1. **Editar `.env`**:
   ```bash
   GITHUB_CLEANUP_ENABLED=true
   ```

2. **Reiniciar servicios**:
   ```bash
   cd deploy
   docker compose down
   docker compose up -d
   ```

3. **Verificar funcionamiento**:
   ```bash
   docker compose logs orchestrator | grep -i github
   ```

### Resultado

Después de activar esta función:
- **GitHub Actions**: Solo muestra runners activos
- **Settings > Actions > Runners**: Limpio, sin entradas offline
- **Monitoreo**: Más fácil identificar problemas reales

### Troubleshooting

#### Si no limpia runners:
1. Verificar `GITHUB_CLEANUP_ENABLED=true`
2. Verificar scopes del token (`repo`, `admin:org`)
3. Revisar logs para errores de API

#### Si elimina runners activos:
- **No debería pasar**: El sistema solo elimina runners offline
- **Verificar logs**: Confirma que los runners estaban realmente offline

#### Si hay errores de permisos:
```
Error obteniendo runners de GitHub: 403
```
- Verificar que el token tenga scopes correctos
- Revisar que el token no haya expirado
