# Configuración para Nginx Proxy Manager

## Puerto a Exponer

**Solo necesitas exponer el puerto 8080** (API Gateway).

## Configuración en Nginx Proxy Manager

### 1. Proxy Host

**Domain/Subdomain**: `gha.yourdomain.com` (o el que prefieras)

**Scheme**: `http`

**Forward Hostname/IP**: `localhost` (o IP del servidor Docker)

**Forward Port**: `8080`

### 2. SSL Certificate

- Habilitar SSL Certificate
- Seleccionar certificado (Let's Encrypt recomendado)

### 3. Autenticación (Recomendado)

#### Opción A: Basic Auth
- Habilitar "Require Authentication"
- Crear usuario y contraseña

#### Opción B: API Key Header
- En "Custom Locations" agregar header:
```
X-API-Key: your-secret-key
```

### 4. Custom Locations (Opcional)

Si quieres limitar endpoints:

```
Location: /api/v1/*
Proxy Pass: http://localhost:8080/api/v1/
```

### 5. Headers (Recomendado)

```
X-Forwarded-Proto: $scheme
X-Forwarded-Host: $host
X-Forwarded-For: $proxy_add_x_forwarded_for
```

## Configuración de .env para Proxy Manager

Para usar con Nginx Proxy Manager, configura tu `.env`:

```bash
# Deshabilitar autenticación del gateway (el proxy la maneja)
ENABLE_AUTH=false
API_KEY=not-needed

# Registry y configuración
REGISTRY=TU_REGISTRY
IMAGE_VERSION=latest
GITHUB_TOKEN=tu_github_token
```

## Ejemplo de Configuración

```nginx
# Configuración automática generada por Nginx Proxy Manager
server {
    listen 443 ssl http2;
    server_name gha.yourdomain.com;
    
    # Autenticación Basic (si se habilita)
    auth_basic "Restricted Area";
    auth_basic_user_file /config/nginx/.htpasswd;
    
    location / {
        proxy_pass http://localhost:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## URLs de Acceso

Una vez configurado:

- **API Gateway**: `https://gha.yourdomain.com`
- **Documentación**: `https://gha.yourdomain.com/docs`
- **Health Check**: `https://gha.yourdomain.com/health`

## Ejemplos de Uso

### Con Basic Auth
```bash
# Crear runner (con usuario/contraseña del proxy)
curl -X POST https://gha.yourdomain.com/api/v1/runners \
  -u username:password \
  -H 'Content-Type: application/json' \
  -d '{"scope":"repo","scope_name":"owner/repo"}'

# Listar runners
curl -u username:password https://gha.yourdomain.com/api/v1/runners
```

### Sin Autenticación (si no se habilitó en proxy)
```bash
# Crear runner
curl -X POST https://gha.yourdomain.com/api/v1/runners \
  -H 'Content-Type: application/json' \
  -d '{"scope":"repo","scope_name":"owner/repo"}'

# Listar runners
curl https://gha.yourdomain.com/api/v1/runners
```

## Ventajas de usar Nginx Proxy Manager

- [OK] **SSL/TLS**: Certificados automáticos con Let's Encrypt
- [OK] **Autenticación Centralizada**: Basic Auth o API Keys
- [OK] **Rate Limiting**: Control de solicitudes
- [OK] **Logs Centralizados**: Todo el tráfico en un lugar
- [OK] **Firewall**: Protección a nivel de proxy
- [OK] **Easy Management**: Interfaz web amigable

## Notas Importantes

1. **Solo puerto 8080**: El orquestador (puerto 8000) es completamente interno
2. **GitHub API**: El sistema necesita acceso a `api.github.com` desde el servidor
3. **Docker Socket**: Asegurar que el servidor Docker tenga acceso a GitHub
4. **Firewall**: Permitir salida del servidor a `api.github.com:443`
5. **ENABLE_AUTH=false**: El proxy maneja la autenticación, no el gateway
6. **Registry**: Asegurar que el servidor pueda acceder a `TU_REGISTRY`

## Troubleshooting

### Error 502 Bad Gateway
- Verificar que el contenedor esté corriendo: `docker compose ps`
- Confirmar puerto 8080 accesible localmente

### Error de Autenticación
- Verificar configuración de Basic Auth en Nginx Proxy Manager
- Confirmar que `ENABLE_AUTH=false` en `.env`

### SSL Certificate Issues
- Verificar que el dominio apunte correctamente al servidor
- Revisar logs de Let's Encrypt en Nginx Proxy Manager
