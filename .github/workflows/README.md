# GitHub Actions Workflows

## Secrets Requeridos

Para que los workflows funcionen correctamente con el registry privado, necesitas configurar los siguientes secrets en tu repositorio de GitHub:

### Registry Secrets

- **`REGISTRY_USERNAME`**: Usuario del registry `your-registry.com`
- **`REGISTRY_PASSWORD`**: Contraseña o token de acceso al registry

### Configuración en GitHub

1. Ve a tu repositorio en GitHub
2. Settings → Secrets and variables → Actions
3. Agrega los siguientes secrets:

```
REGISTRY_USERNAME = tu_usuario_registry
REGISTRY_PASSWORD = tu_contraseña_o_token
```

## Workflows Disponibles

### Build and Push (`build-and-push.yml`)

**Trigger**: Tags con formato `vX.Y.Z` (ej: `v1.0.0`)

**Funcionalidades**:
- Build de imágenes Docker
- Push al registry privado con autenticación
- Tag versionado además de `latest`
- Verificación de acceso al registry
- Security scanning
- SBOM generation

**Uso**:
```bash
# Crear tag y disparar workflow
git tag v1.0.0
git push origin v1.0.0
```

## Variables de Entorno

El workflow usa las siguientes variables:

- `REGISTRY`: `your-registry.com` (hardcodeado)
- `REGISTRY_USERNAME`: Desde secrets
- `REGISTRY_PASSWORD`: Desde secrets

## Troubleshooting

### Error de Autenticación

Si obtienes errores de autenticación:

1. Verifica que los secrets estén configurados correctamente
2. Confirma que el usuario tenga permisos de push al registry
3. Revisa que la contraseña/token sea válida

### Registry No Accesible

El workflow incluye verificación de acceso al registry. Si falla:

1. Verifica conectividad desde GitHub Actions a tu registry
2. Confirma que el registry permita conexiones externas
3. Revisa firewall o configuraciones de red

### Build Falla

Si el build falla:

1. Revisa los logs del workflow en GitHub
2. Verifica que los Dockerfiles sean válidos
3. Confirma que el contexto de build sea correcto

## Security Considerations

- Los secrets nunca se muestran en los logs
- Las credenciales se usan solo durante el login
- Las imágenes se marcan como privadas en el registry
- El workflow solo se ejecuta para tags versionados
