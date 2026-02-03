# GitHub Actions Workflows

## Build and Push Workflow

### Trigger
- **Tags semánticos**: Se activa automáticamente con tags `vX.Y.Z` (ej: `v1.2.3`)

### Funcionalidades
- **Build x86_64**: Construye imágenes para `linux/amd64`
- **Tags dobles**: Publica con tags `:latest` y `:versión`
- **Login automático**: Usa credenciales del registry

### Configuración Requerida

#### Variables de Entorno (Repository Settings > Variables)
```
REGISTRY=your-registry.com
```

#### Secrets (Repository Settings > Secrets)
```
REGISTRY_USERNAME=your_registry_username
REGISTRY_PASSWORD=your_registry_password_or_token
```

### Flujo de Ejecución

1. **Docker Buildx** - Configura build multiplataforma
2. **Login** - Autenticación en el registry
3. **Build Images** - Construye las 2 imágenes:
   - `gha-orchestrator` 
   - `gha-api-gateway`

### Imágenes Generadas

Para cada servicio se generan dos tags:
```
your-registry.com/gha-orchestrator:latest
your-registry.com/gha-orchestrator:v1.2.3

your-registry.com/gha-api-gateway:latest
your-registry.com/gha-api-gateway:v1.2.3
```

## Release Workflow

### Trigger
- **Tags semánticos**: Se activa con tags `vX.Y.Z` (ej: `v1.2.3`)

### Funcionalidades
- **Crea GitHub Release** con changelog
- **Genera changelog** desde el tag anterior
- **Incluye assets** por defecto
- **Publica automáticamente**

### Configuración Requerida

#### Permisos del Workflow
El workflow incluye permisos necesarios en el archivo `release.yml`:
```yaml
permissions:
  contents: write  # Para crear releases
```

### Flujo de Ejecución

1. **Checkout** - Descarga el código con historial completo
2. **Get previous tag** - Identifica tag anterior para changelog
3. **Generate changelog** - Genera lista de cambios
4. **Create Release** - Publica release con changelog e instrucciones
