FROM ubuntu:22.04

# Metadatos
LABEL maintainer="GHA Ephemeral Runners"
LABEL version="1.0.0"
LABEL description="Runner efímero de GitHub Actions"

# Variables de entorno
ENV DEBIAN_FRONTEND=noninteractive
ENV RUNNER_VERSION=2.311.0
ENV RUNNER_USER=runner

# Instalar dependencias del sistema
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        curl \
        wget \
        jq \
        git \
        ca-certificates \
        gnupg \
        lsb-release \
        python3 \
        python3-pip \
        sudo \
        && rm -rf /var/lib/apt/lists/*

# Instalar Docker CLI
RUN curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg && \
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null && \
    apt-get update && \
    apt-get install -y --no-install-recommends docker-ce-cli && \
    rm -rf /var/lib/apt/lists/*

# Crear usuario del runner
RUN groupadd -r $RUNNER_USER && \
    useradd -r -g $RUNNER_USER -m -s /bin/bash $RUNNER_USER && \
    echo "$RUNNER_USER ALL=(ALL) NOPASSWD: ALL" >> /etc/sudoers

# Crear directorios
RUN mkdir -p /runner && \
    chown -R $RUNNER_USER:$RUNNER_USER /runner

# Descargar y extraer GitHub Actions runner
RUN cd /tmp && \
    curl -L -o actions-runner-linux-x64-${RUNNER_VERSION}.tar.gz \
        https://github.com/actions/runner/releases/download/v${RUNNER_VERSION}/actions-runner-linux-x64-${RUNNER_VERSION}.tar.gz && \
    tar xzf ./actions-runner-linux-x64-${RUNNER_VERSION}.tar.gz && \
    rm actions-runner-linux-x64-${RUNNER_VERSION}.tar.gz && \
    mv * /runner/ && \
    chown -R $RUNNER_USER:$RUNNER_USER /runner

# Instalar dependencias Python del runner
WORKDIR /runner
RUN pip install --no-cache-dir -r /runner/requirements.txt

# Copiar entrypoint y scripts
COPY entrypoint.sh /runner/entrypoint.sh
RUN chmod +x /runner/entrypoint.sh

# Cambiar a usuario del runner
USER $RUNNER_USER

# Exponer puerto (si es necesario para health checks)
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD pgrep -f "config.sh\|run.sh" > /dev/null || exit 1

# Comando de inicio
ENTRYPOINT ["/runner/entrypoint.sh"]
