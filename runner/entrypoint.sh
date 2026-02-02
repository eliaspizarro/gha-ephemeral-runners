#!/bin/bash

set -e

# Variables de entorno obligatorias
GITHUB_REGISTRATION_TOKEN=${GITHUB_REGISTRATION_TOKEN}
RUNNER_NAME=${RUNNER_NAME:-"ephemeral-runner-$(date +%s)-$(hostname)"}
SCOPE=${SCOPE}
SCOPE_NAME=${SCOPE_NAME}
RUNNER_GROUP=${RUNNER_GROUP:-""}
RUNNER_LABELS=${RUNNER_LABELS:-""}
IDLE_TIMEOUT=${IDLE_TIMEOUT:-3600}

# Validar variables obligatorias
if [ -z "$GITHUB_REGISTRATION_TOKEN" ]; then
    echo "ERROR: GITHUB_REGISTRATION_TOKEN es obligatorio"
    exit 1
fi

if [ -z "$SCOPE" ]; then
    echo "ERROR: SCOPE es obligatorio (repo|org)"
    exit 1
fi

if [ -z "$SCOPE_NAME" ]; then
    echo "ERROR: SCOPE_NAME es obligatorio"
    exit 1
fi

echo "Iniciando runner efímero: $RUNNER_NAME"
echo "Scope: $SCOPE/$SCOPE_NAME"
echo "Timeout de inactividad: ${IDLE_TIMEOUT}s"

# Función para cleanup al salir
cleanup() {
    echo "Realizando cleanup..."
    if [ -d "/runner" ]; then
        cd /runner
        ./config.sh remove --token "$GITHUB_REGISTRATION_TOKEN" || true
    fi
    echo "Cleanup completado"
    exit 0
}

# Configurar señales
trap cleanup SIGTERM SIGINT

# Crear directorio del runner
mkdir -p /runner
cd /runner

# Configurar runner
echo "Configurando runner..."
if [ "$SCOPE" = "repo" ]; then
    ./config.sh \
        --url "https://github.com/$SCOPE_NAME" \
        --token "$GITHUB_REGISTRATION_TOKEN" \
        --name "$RUNNER_NAME" \
        --work "_work" \
        --replace \
        --unattended \
        ${RUNNER_GROUP:+--runnergroup "$RUNNER_GROUP"} \
        ${RUNNER_LABELS:+--labels "$RUNNER_LABELS"}
elif [ "$SCOPE" = "org" ]; then
    ./config.sh \
        --url "https://github.com/$SCOPE_NAME" \
        --token "$GITHUB_REGISTRATION_TOKEN" \
        --name "$RUNNER_NAME" \
        --work "_work" \
        --replace \
        --unattended \
        ${RUNNER_GROUP:+--runnergroup "$RUNNER_GROUP"} \
        ${RUNNER_LABELS:+--labels "$RUNNER_LABELS"}
else
    echo "ERROR: Scope inválido: $SCOPE"
    exit 1
fi

echo "Runner configurado exitosamente"

# Iniciar runner con timeout de inactividad
echo "Iniciando runner..."
timeout "$IDLE_TIMEOUT" ./run.sh &
RUNNER_PID=$!

# Monitorear el proceso del runner
while kill -0 $RUNNER_PID 2>/dev/null; do
    sleep 30
done

# Verificar si el runner terminó normalmente
wait $RUNNER_PID
RUNNER_EXIT_CODE=$?

echo "Runner terminó con código: $RUNNER_EXIT_CODE"

# Cleanup y salir
cleanup
