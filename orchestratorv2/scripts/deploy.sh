#!/bin/bash

# Deploy Script para OrchestratorV2
# Rol: Automatizar el proceso de despliegue de la aplicación
# Configura entorno, ejecuta contenedor y verifica despliegue

set -e  # Exit on error

# Configuración
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
DOCKER_IMAGE="orchestratorv2"
DOCKER_TAG="latest"
CONTAINER_NAME="orchestratorv2-container"
HOST_PORT="8000"
CONTAINER_PORT="8000"

# Variables de entorno por defecto
export ORCHESTRATOR_HOST="localhost"
export ORCHESTRATOR_PORT="$HOST_PORT"
export HEALTH_CHECK_TIMEOUT="10"
export HEALTH_CHECK_WAIT_TIME="5"

echo "🚀 Iniciando deploy de OrchestratorV2..."
echo "📁 Directorio del proyecto: $PROJECT_ROOT"

# Función de logging
log_info() {
    echo "ℹ️  $1"
}

log_success() {
    echo "✅ $1"
}

log_warning() {
    echo "⚠️  $1"
}

log_error() {
    echo "❌ $1"
}

# 1. Validar prerequisitos
validate_prerequisites() {
    log_info "Validando prerequisitos..."
    
    # Verificar Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker no está instalado"
        exit 1
    fi
    
    # Verificar Docker daemon
    if ! docker info &> /dev/null; then
        log_error "Docker daemon no está corriendo"
        exit 1
    fi
    
    # Verificar imagen Docker
    if ! docker images | grep -q "$DOCKER_IMAGE"; then
        log_error "Imagen Docker $DOCKER_IMAGE no encontrada. Ejecuta: ./scripts/build.sh"
        exit 1
    fi
    
    log_success "Prerequisitos validados"
}

# 2. Limpiar contenedor existente
cleanup_container() {
    log_info "Limpiando contenedor existente..."
    
    # Detener y eliminar contenedor si existe
    if docker ps -a | grep -q "$CONTAINER_NAME"; then
        log_info "Deteniendo contenedor existente..."
        docker stop "$CONTAINER_NAME" 2>/dev/null || true
        docker rm "$CONTAINER_NAME" 2>/dev/null || true
        log_success "Contenedor existente limpiado"
    fi
}

# 3. Configurar variables de entorno
setup_environment() {
    log_info "Configurando variables de entorno..."
    
    cd "$PROJECT_ROOT"
    
    # Crear archivo .env si no existe
    if [ ! -f ".env" ]; then
        log_warning ".env no encontrado, creando archivo por defecto..."
        cat > .env << EOF
# Configuración de OrchestratorV2
ENVIRONMENT=development
DEBUG=true
API_HOST=0.0.0.0
API_PORT=8000

# GitHub Configuration
GITHUB_RUNNER_TOKEN=your_token_here
GITHUB_API_BASE=https://api.github.com

# Docker Configuration
DOCKER_RUNNER_IMAGE=gha-runner:latest

# Orchestration Configuration
POLL_INTERVAL=30
CLEANUP_INTERVAL=300
MAX_RUNNERS_PER_REPO=5
AUTO_CREATE_RUNNERS=false
EOF
        log_warning "⚠️  Por favor configura .env con tus valores reales"
    fi
    
    # Cargar variables de entorno
    if [ -f ".env" ]; then
        export $(cat .env | grep -v '^#' | xargs)
        log_success "Variables de entorno cargadas desde .env"
    fi
}

# 4. Ejecutar contenedor
run_container() {
    log_info "Iniciando contenedor Docker..."
    
    cd "$PROJECT_ROOT"
    
    # Mapear puertos y volúmenes
    docker run -d \
        --name "$CONTAINER_NAME" \
        -p "${HOST_PORT}:${CONTAINER_PORT}" \
        --env-file .env \
        --restart unless-stopped \
        "${DOCKER_IMAGE}:${DOCKER_TAG}"
    
    # Verificar que el contenedor esté corriendo
    if docker ps | grep -q "$CONTAINER_NAME"; then
        log_success "Contenedor iniciado: $CONTAINER_NAME"
        docker ps | grep "$CONTAINER_NAME"
    else
        log_error "Error iniciando contenedor"
        docker logs "$CONTAINER_NAME"
        exit 1
    fi
}

# 5. Verificar despliegue
verify_deployment() {
    log_info "Verificando despliegue..."
    
    # Esperar a que el servicio esté listo
    log_info "Esperando a que el servicio esté listo..."
    sleep 10
    
    # Verificar health check del contenedor
    local health_status=$(docker inspect --format='{{.State.Health.Status}}' "$CONTAINER_NAME" 2>/dev/null || echo "unknown")
    log_info "Status health check: $health_status"
    
    # Verificar endpoint HTTP
    local max_attempts=30
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if curl -f -s "http://localhost:${HOST_PORT}/api/system/health" > /dev/null 2>&1; then
            log_success "✅ Endpoint de health responde correctamente"
            break
        fi
        
        if [ $attempt -eq $max_attempts ]; then
            log_error "❌ Endpoint de health no responde después de $max_attempts intentos"
            docker logs "$CONTAINER_NAME"
            exit 1
        fi
        
        log_info "Intento $attempt/$max_attempts - esperando..."
        sleep 2
        ((attempt++))
    done
    
    # Mostrar información del despliegue
    log_success "🎉 Despliegue verificado exitosamente"
    log_info "📊 Información del despliegue:"
    echo "  - Contenedor: $CONTAINER_NAME"
    echo "  - Imagen: ${DOCKER_IMAGE}:${DOCKER_TAG}"
    echo "  - Puerto: ${HOST_PORT}:${CONTAINER_PORT}"
    echo "  - Health: http://localhost:${HOST_PORT}/api/system/health"
    echo "  - API Docs: http://localhost:${HOST_PORT}/docs"
}

# 6. Mostrar logs
show_logs() {
    log_info "Mostrando logs del contenedor..."
    docker logs -f "$CONTAINER_NAME"
}

# 7. Detener despliegue
stop_deployment() {
    log_info "Deteniendo despliegue..."
    
    if docker ps | grep -q "$CONTAINER_NAME"; then
        docker stop "$CONTAINER_NAME"
        log_success "Contenedor detenido"
    fi
    
    if docker ps -a | grep -q "$CONTAINER_NAME"; then
        docker rm "$CONTAINER_NAME"
        log_success "Contenedor eliminado"
    fi
}

# 8. Actualizar despliegue
update_deployment() {
    log_info "Actualizando despliegue..."
    
    # Detener contenedor actual
    stop_deployment
    
    # Build nueva imagen
    log_info "Construyendo nueva imagen..."
    cd "$PROJECT_ROOT"
    ./scripts/build.sh
    
    # Iniciar nuevo contenedor
    run_container
    verify_deployment
}

# 9. Estado del despliegue
show_status() {
    log_info "Estado del despliegue:"
    
    if docker ps | grep -q "$CONTAINER_NAME"; then
        echo "🟢 Contenedor corriendo"
        docker ps | grep "$CONTAINER_NAME"
        
        # Health check status
        local health_status=$(docker inspect --format='{{.State.Health.Status}}' "$CONTAINER_NAME" 2>/dev/null || echo "unknown")
        echo "🏥 Health Status: $health_status"
        
        # Resource usage
        echo "📊 Resource Usage:"
        docker stats --no-stream "$CONTAINER_NAME" 2>/dev/null || echo "  No disponible"
    else
        echo "🔴 Contenedor no corriendo"
        
        if docker ps -a | grep -q "$CONTAINER_NAME"; then
            echo "📋 Contenedor detenido:"
            docker ps -a | grep "$CONTAINER_NAME"
        else
            echo "📋 Contenedor no encontrado"
        fi
    fi
}

# Función principal
main() {
    local start_time=$(date +%s)
    
    case "$1" in
        "deploy")
            validate_prerequisites
            cleanup_container
            setup_environment
            run_container
            verify_deployment
            ;;
        "stop")
            stop_deployment
            ;;
        "restart")
            stop_deployment
            sleep 2
            main "deploy"
            ;;
        "update")
            update_deployment
            ;;
        "logs")
            show_logs
            ;;
        "status")
            show_status
            ;;
        *)
            log_error "Comando no reconocido: $1"
            show_help
            exit 1
            ;;
    esac
    
    # Calcular tiempo total
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    
    log_success "⚡ Operación completada en ${duration}s"
}

# Mostrar ayuda
show_help() {
    echo "Uso: $0 COMANDO [OPCIONES]"
    echo ""
    echo "Comandos:"
    echo "  deploy    Despliega la aplicación"
    echo "  stop      Detiene el despliegue"
    echo "  restart   Reinicia el despliegue"
    echo "  update    Actualiza el despliegue (build + deploy)"
    echo "  logs      Muestra logs del contenedor"
    echo "  status    Muestra estado del despliegue"
    echo "  help      Muestra esta ayuda"
    echo ""
    echo "Variables de entorno:"
    echo "  DOCKER_IMAGE        Nombre de la imagen (default: orchestratorv2)"
    echo "  DOCKER_TAG          Tag de la imagen (default: latest)"
    echo "  CONTAINER_NAME      Nombre del contenedor (default: orchestratorv2-container)"
    echo "  HOST_PORT           Puerto host (default: 8000)"
    echo "  CONTAINER_PORT      Puerto contenedor (default: 8000)"
    echo ""
    echo "Ejemplos:"
    echo "  $0 deploy           # Despliega la aplicación"
    echo "  $0 restart          # Reinicia el despliegue"
    echo "  $0 logs             # Muestra logs en tiempo real"
}

# Procesar argumentos
if [ $# -eq 0 ]; then
    show_help
    exit 1
fi

case "$1" in
    --help|-h|help)
        show_help
        exit 0
        ;;
    *)
        main "$@"
        ;;
esac
