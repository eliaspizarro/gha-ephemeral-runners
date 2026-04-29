# Git Aliases para Automatización

## Alias de Release

He creado un alias git para automatizar todo el proceso de commit, push y tag:

### Configuración del Alias

```bash
git config --global alias.release "!git add . && git commit -m \"$1\" && git push origin main && git tag \"$2\" && git push origin \"$2\""
```

### Uso

```bash
# Sintaxis: git release "mensaje del commit" "versión del tag"
git release "feat: Add new feature" "v1.3.0"
```

### Qué hace el alias

1. **git add .** - Agrega todos los cambios al staging
2. **git commit -m "mensaje"** - Hace commit con el mensaje especificado
3. **git push origin main** - Sube los cambios al main
4. **git tag "versión"** - Crea el tag con la versión especificada
5. **git push origin "versión"** - Publica el tag (activa el workflow)

### Ejemplos

```bash
# Para una nueva feature
git release "feat: Add GitHub offline runners cleanup" "v1.3.0"

# Para un fix
git release "fix: Resolve runner version issue" "v1.3.1"

# Para una actualización menor
git release "chore: Update documentation" "v1.3.2"
```

### Verificar Alias Configurado

```bash
git config --global --get alias.release
```

### Eliminar Alias

```bash
git config --global --unset alias.release
```

## Alias Adicionales Útiles

### Alias para ver tags recientes
```bash
git config --global alias.tags "tag -l --sort=-version:refname"
```

### Alias para ver commits entre tags
```bash
git config --global alias.between "!git log --oneline --graph $1..$2"
```

### Uso de aliases adicionales
```bash
# Ver tags ordenados por versión (más reciente primero)
git tags

# Ver commits entre dos versiones
git.between v1.2.0 v1.3.0
```

## Workflow Completo con Alias

Ahora puedes hacer todo el proceso en un solo comando:

```bash
# Antes (múltiples comandos)
git add .
git commit -m "feat: Add GitHub offline runners cleanup"
git push origin main
git tag v1.3.0
git push origin v1.3.0

# Ahora (un solo comando)
git release "feat: Add GitHub offline runners cleanup" "v1.3.0"
```

Esto activará automáticamente el workflow de build and release en GitHub Actions.
