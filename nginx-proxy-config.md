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

### 3. Custom Locations (Opcional)

Si quieres limitar endpoints:

```
Location: /api/v1/*
Proxy Pass: http://localhost:8080/api/v1/
```

### 4. Headers (Opcional pero recomendado)

```
X-Forwarded-Proto: $scheme
X-Forwarded-Host: $host
X-Forwarded-For: $proxy_add_x_forwarded_for
```

## Ejemplo de Configuración

```nginx
# Configuración automática generada por Nginx Proxy Manager
server {
    listen 443 ssl http2;
    server_name gha.yourdomain.com;
    
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

```bash
# Crear runner
curl -X POST https://gha.yourdomain.com/api/v1/runners \
  -H 'Content-Type: application/json' \
  -d '{"scope":"repo","scope_name":"owner/repo"}'

# Listar runners
curl https://gha.yourdomain.com/api/v1/runners
```

## Notas Importantes

1. **Solo puerto 8080**: El orquestador (puerto 8000) es completamente interno
2. **GitHub API**: El sistema necesita acceso a `api.github.com` desde el servidor
3. **Docker Socket**: Asegurar que el servidor Docker tenga acceso a GitHub
4. **Firewall**: Permitir salida del servidor a `api.github.com:443`
