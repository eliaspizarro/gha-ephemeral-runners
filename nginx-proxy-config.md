# Configuración para Nginx Proxy Manager

## Configuración Básica

### 1. Proxy Host
- **Domain**: `gha.yourdomain.com`
- **Scheme**: `http`
- **Forward Hostname/IP**: `localhost`
- **Forward Port**: `8080`

### 2. SSL Certificate
- Habilitar SSL Certificate
- Seleccionar certificado Let's Encrypt

### 3. Autenticación
- Habilitar "Require Authentication"
- Crear usuario y contraseña

### 4. Configuración .env
```bash
# Para producción detrás de proxy
ENABLE_AUTH=false
CORS_ORIGINS=https://yourdomain.com
```

## URLs de Acceso

Una vez configurado:

- **API Gateway**: `https://gha.yourdomain.com`
- **Documentación**: `https://gha.yourdomain.com/docs`
- **Health Check**: `https://gha.yourdomain.com/health`
