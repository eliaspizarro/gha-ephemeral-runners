FROM python:3.12-slim

# Metadatos
LABEL maintainer="GHA Ephemeral Runners"
LABEL version="1.0.0"
LABEL description="API Gateway para runners efímeros de GitHub Actions"

# Variables de entorno
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Instalar dependencias del sistema
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        golang-go \
        && rm -rf /var/lib/apt/lists/*

# Crear directorio de la aplicación
WORKDIR /app

# Copiar requirements e instalar dependencias Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Compilar health check de Go
COPY healthcheck.go .
RUN go build -o healthcheck healthcheck.go

# Copiar código de la aplicación
COPY . .

# Exponer puerto
EXPOSE 8080

# Health check nativo en Go compilado
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD ./healthcheck || exit 1

# Comando de inicio
CMD ["python", "main.py"]
