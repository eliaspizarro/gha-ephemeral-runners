# GitHub Actions Workflows

## Build and Release Workflow (Unificado)

### Trigger
- **Tags con prefijo v**: Se activa automáticamente con tags `v*` (ej: `v1.2.3`, `v1.2.3-alpha`, `v2.0.0-beta`)

### Funcionalidades
- **Build x86_64**: Construye imágenes para `linux/amd64`
- **Tags dobles**: Publica con tags `:latest` y `:versión`
- **Login automático**: Usa credenciales del registry
- **Verificación de imágenes**: Confirma que las imágenes existen en el registry
- **Changelog automático**: Genera changelog desde el tag anterior
- **GitHub Release**: Crea release con changelog incluido

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

#### Permisos del Workflow
El workflow incluye permisos necesarios:
```yaml
permissions:
  contents: write    # Para crear releases
  packages: write   # Para publicar imágenes
```

### Flujo de Ejecución

1. **Checkout** - Descarga el código con historial completo
2. **Docker Buildx** - Configura build multiplataforma
3. **Login** - Autenticación en el registry
4. **Build Images** - Construye las 2 imágenes:
   - `gha-orchestrator`
   - `gha-api-gateway`
5. **Verify Images** - Verifica que las imágenes existen en el registry
6. **Get previous tag** - Identifica tag anterior para changelog
7. **Generate changelog** - Genera lista de cambios
8. **Create Release** - Publica release con changelog

### Imágenes Generadas

Para cada servicio se generan dos tags:
```
your-registry.com/gha-orchestrator:latest
your-registry.com/gha-orchestrator:v1.2.3

your-registry.com/gha-api-gateway:latest
your-registry.com/gha-api-gateway:v1.2.3
```

### GitHub Release

El release se crea automáticamente con:
- **Título**: `Release vX.Y.Z`
- **Changelog**: Lista de commits desde el tag anterior
- **Formato**: Markdown con emojis y estructura clara

### Uso

Para ejecutar el workflow completo:

```bash
# Crear y push tag (usando alias personalizado)
git tag-all v1.2.3

# O manualmente
git tag v1.2.3
git push origin v1.2.3
```

### Acciones Usadas

- `actions/checkout@v5` - Checkout del código
- `docker/setup-buildx-action@v3` - Configuración de Docker Buildx
- `docker/login-action@v3` - Login al registry
- `docker/build-push-action@v6` - Build y push de imágenes
- `softprops/action-gh-release@v2` - Creación de releases

### Notas Importantes

- **Ejecución como root**: Los contenedores se ejecutan como root para evitar problemas de permisos con Docker socket
- **Unificado**: Un solo workflow reemplaza los anteriores `build-and-push.yml` y `release.yml`
- **Orden secuencial**: Build → Verify → Release para asegurar consistencia
