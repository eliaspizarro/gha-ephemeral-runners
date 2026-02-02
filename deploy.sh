#!/bin/bash

set -e

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Funciones de logging
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

# Verificar dependencias
check_dependencies() {
    log_step "Verificando dependencias..."
    
    if ! command -v docker &> /dev/null; then
        log_error "Docker no está instalado"
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose no está instalado"
        exit 1
    fi
    
    log_info "Dependencias verificadas"
}

# Verificar configuración
check_config() {
    log_step "Verificando configuración..."
    
    if [ ! -f .env ]; then
        log_error "Archivo .env no encontrado"
        log_info "Ejecuta: cp .env.example .env y configúralo"
        exit 1
    fi
    
    # Verificar variable obligatoria
    if ! grep -q "GITHUB_TOKEN=" .env || grep -q "GITHUB_TOKEN=$" .env; then
        log_error "GITHUB_TOKEN es obligatorio en .env"
        exit 1
    fi
    
    log_info "Configuración verificada"
}

# Construir imágenes si no existen
build_if_needed() {
    log_step "Verificando imágenes..."
    
    # Verificar imagen del runner
    if ! docker image inspect gha-runner:latest &> /dev/null; then
        log_warn "Imagen gha-runner:latest no encontrada, construyendo..."
        docker build -t gha-runner:latest ./runner/
    fi
    
    # Construir servicios
    log_info "Construyendo servicios..."
    docker-compose build
}

# Iniciar servicios
start_services() {
    log_step "Iniciando servicios..."
    
    # Detener servicios existentes
    docker-compose down 2>/dev/null || true
    
    # Iniciar servicios
    docker-compose up -d
    
    log_info "Servicios iniciados"
}

# Esperar a que los servicios estén listos
wait_for_services() {
    log_step "Esperando a que los servicios estén listos..."
    
    # Esperar API Gateway
    log_info "Esperando API Gateway..."
    for i in {1..30}; do
        if curl -f http://localhost:8080/health &> /dev/null; then
            log_info "API Gateway está listo"
            break
        fi
        if [ $i -eq 30 ]; then
            log_error "Timeout esperando API Gateway"
            exit 1
        fi
        sleep 2
    done
    
    # Esperar Orquestador
    log_info "Esperando Orquestador..."
    for i in {1..30}; do
        if curl -f http://localhost:8000/health &> /dev/null; then
            log_info "Orquestador está listo"
            break
        fi
        if [ $i -eq 30 ]; then
            log_error "Timeout esperando Orquestador"
            exit 1
        fi
        sleep 2
    done
    
    log_info "Todos los servicios están listos"
}

# Mostrar información de despliegue
show_info() {
    log_step "Información de despliegue:"
    echo
    echo "API Gateway: http://localhost:8080"
    echo "Orquestador: http://localhost:8000"
    echo "Documentación API: http://localhost:8080/docs"
    echo
    echo "Comandos útiles:"
    echo "  Ver logs: docker-compose logs -f"
    echo "  Ver estado: docker-compose ps"
    echo "  Detener: docker-compose down"
    echo
    echo "Ejemplo de uso:"
    echo "  curl -X POST http://localhost:8080/api/v1/runners \\"
    echo "    -H 'Content-Type: application/json' \\"
    echo "    -d '{\"scope\":\"repo\",\"scope_name\":\"owner/repo\"}'"
    echo
}

# Main
main() {
    local action=${1:-"deploy"}
    
    case $action in
        "deploy")
            log_info "Iniciando despliegue de GHA Ephemeral Runners..."
            check_dependencies
            check_config
            build_if_needed
            start_services
            wait_for_services
            show_info
            log_info "Despliegue completado exitosamente"
            ;;
        "stop")
            log_info "Deteniendo servicios..."
            docker-compose down
            log_info "Servicios detenidos"
            ;;
        "restart")
            log_info "Reiniciando servicios..."
            docker-compose restart
            log_info "Servicios reiniciados"
            ;;
        "logs")
            docker-compose logs -f
            ;;
        "status")
            docker-compose ps
            ;;
        "health")
            log_info "Verificando salud de los servicios..."
            echo
            echo "API Gateway:"
            curl -s http://localhost:8080/health | jq . 2>/dev/null || curl -s http://localhost:8080/health
            echo
            echo "Orquestador:"
            curl -s http://localhost:8000/health | jq . 2>/dev/null || curl -s http://localhost:8000/health
            echo
            ;;
        *)
            echo "Uso: $0 {deploy|stop|restart|logs|status|health}"
            echo
            echo "Comandos:"
            echo "  deploy  - Despliega todos los servicios (default)"
            echo "  stop    - Detiene todos los servicios"
            echo "  restart - Reinicia todos los servicios"
            echo "  logs    - Muestra logs en tiempo real"
            echo "  status  - Muestra estado de los contenedores"
            echo "  health  - Verifica salud de los servicios"
            exit 1
            ;;
    esac
}

# Ejecutar main
main "$@"
