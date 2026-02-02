FROM python:3.11-slim

# Metadatos
LABEL maintainer="GHA Ephemeral Runners"
LABEL version="1.0.0"
LABEL description="Orquestador de runners efímeros de GitHub Actions"

# Variables de entorno
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PORT=8000

# Instalar dependencias del sistema
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        curl \
        && rm -rf /var/lib/apt/lists/*

# Crear usuario no root
RUN groupadd -r orchestrator && \
    useradd -r -g orchestrator -d /app -s /bin/bash orchestrator

# Crear directorio de la aplicación
WORKDIR /app

# Copiar requirements e instalar dependencias Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código de la aplicación
COPY . .

# Cambiar permisos
RUN chown -R orchestrator:orchestrator /app

# Cambiar a usuario no root
USER orchestrator

# Exponer puerto
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Comando de inicio
CMD ["python", "orchestrator_service.py"]
