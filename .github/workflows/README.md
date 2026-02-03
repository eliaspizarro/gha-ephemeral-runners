# GitHub Actions Workflows

## Build and Push (`build-and-push.yml`)

Workflow para construir y subir imágenes Docker al registry privado.

### Trigger

**Tags con formato `vX.Y.Z`** (ej: `v1.0.0`)

```bash
# Crear tag y disparar workflow
git tag v1.0.0
git push origin v1.0.0
```

### Funcionalidades

- Build de imágenes Docker
- Push al registry privado con autenticación
- Tag versionado además de `latest`
- Verificación de acceso al registry
- Security scanning
- SBOM generation

### Configuración Requerida

#### Secrets en GitHub

Ve a tu repositorio → Settings → Secrets and variables → Actions y agrega:

```
REGISTRY_USERNAME = tu_usuario_registry
REGISTRY_PASSWORD = tu_contraseña_o_token
```

#### Variables en GitHub

Ve a tu repositorio → Settings → Secrets and variables → Actions → Variables y agrega:

```
REGISTRY = your-registry.com
```

### Flujo de Ejecución

1. **Checkout** del código
2. **Setup Python** y dependencias
3. **Setup Docker Buildx**
4. **Login al Registry** con secrets
5. **Build y Push** de imágenes
6. **Tag versionado** (v1.2.3, latest)
7. **Security Scanning** con Trivy
8. **Registry Verification** de imágenes

### Imágenes Construidas

- `gha-runner:latest` y `gha-runner:vX.Y.Z`
- `gha-orchestrator:latest` y `gha-orchestrator:vX.Y.Z`
- `gha-api-gateway:latest` y `gha-api-gateway:vX.Y.Z`

### Troubleshooting

#### Error de Autenticación

1. Verifica que los secrets estén configurados correctamente
2. Confirma que el usuario tenga permisos de push al registry
3. Revisa que la contraseña/token sea válida

#### Registry No Accesible

1. Verifica conectividad desde GitHub Actions a tu registry
2. Confirma que el registry permita conexiones externas
3. Revisa firewall o configuraciones de red

#### Build Falla

1. Revisa los logs del workflow en GitHub
2. Verifica que los Dockerfiles sean válidos
3. Confirma que el contexto de build sea correcto

### Security Considerations

- Los secrets nunca se muestran en los logs
- Las credenciales se usan solo durante el login
- Las imágenes se marcan como privadas en el registry
- El workflow solo se ejecuta para tags versionados
