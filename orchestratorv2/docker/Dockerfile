# Dockerfile para OrchestratorV2
# Rol: Definir la imagen Docker para el servicio principal
# Basado en Python slim con dependencias necesarias
# Configura el entrypoint y el entorno de ejecución
# Incluye health check nativo compilado desde Go
# Actualizado: Febrero 2026 con últimas versiones estables

# Etapa 1: Build del health check en Go
FROM golang:1.25-alpine AS healthcheck-builder

# Instalar dependencias de build actualizadas
RUN apk add --no-cache git ca-certificates tzdata curl

# Copiar y compilar health check con optimizaciones
COPY scripts/healthcheck.go /app/
WORKDIR /app
RUN CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build \
    -ldflags="-w -s -extldflags '-static'" \
    -a -installsuffix cgo \
    -o healthcheck healthcheck.go

# Etapa 2: Build de la aplicación Python
FROM python:3.14-slim AS python-builder

# Instalar dependencias de sistema actualizadas
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    build-essential \
    libffi-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Crear directorio de trabajo
WORKDIR /app

# Copiar requirements e instalar dependencias con optimizaciones
COPY requirements.txt .
RUN pip install --no-cache-dir --user --upgrade pip setuptools wheel && \
    pip install --no-cache-dir --user -r requirements.txt

# Etapa 3: Imagen final multi-stage optimizada
FROM python:3.14-slim

# Etiquetas de metadata actualizadas
LABEL maintainer="OrchestratorV2 Team"
LABEL version="0.1.0"
LABEL description="GitHub Actions Ephemeral Runners Orchestrator V2"
LABEL python.version="3.14.0"
LABEL go.version="1.25.0"
LABEL build.date="2026-02-04"

# Variables de entorno optimizadas para Python 3.14
ENV PYTHONPATH=/app/src
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONOPTIMIZE=2

# Instalar dependencias de sistema necesarias actualizadas
RUN apt-get update && apt-get install -y \
    curl \
    ca-certificates \
    libffi8 \
    libssl3 \
    tzdata \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

WORKDIR /app

# Copiar dependencias Python desde builder
COPY --from=python-builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

# Copiar health check compilado
COPY --from=healthcheck-builder /app/healthcheck /usr/local/bin/healthcheck
RUN chmod +x /usr/local/bin/healthcheck

# Copiar código fuente
COPY src/ ./src/
COPY scripts/ ./scripts/

# Exponer puerto
EXPOSE 8000

# Health check del contenedor Docker mejorado
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD ["/usr/local/bin/healthcheck"] \
    || exit 1

# Comando de inicio optimizado para Python 3.14
CMD ["python", "-X", "utf8", "-m", "src.api.main"]

# Metadata para herramientas de orquestación actualizadas
# Build args para personalización
ARG BUILD_DATE
ARG VCS_REF
ARG VERSION

LABEL org.label-schema.build-date=$BUILD_DATE \
      org.label-schema.name="OrchestratorV2" \
      org.label-schema.description="GitHub Actions Ephemeral Runners Orchestrator" \
      org.label-schema.url="https://github.com/your-org/gha-ephemeral-runners" \
      org.label-schema.vcs-ref=$VCS_REF \
      org.label-schema.vcs-url="https://github.com/your-org/gha-ephemeral-runners.git" \
      org.label-schema.vendor="Your Organization" \
      org.label-schema.version=$VERSION \
      org.label-schema.schema-version="1.0" \
      org.label-schema.python-version="3.14.0" \
      org.label-schema.go-version="1.25.0"
