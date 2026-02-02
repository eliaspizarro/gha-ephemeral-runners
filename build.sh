#!/bin/bash

set -e

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
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

# Verificar Docker y Docker Compose
check_dependencies() {
    log_info "Verificando dependencias..."
    
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

# Construir imágenes
build_images() {
    log_info "Construyendo imágenes Docker..."
    
    # Construir imagen del runner primero
    log_info "Construyendo imagen del runner..."
    docker build -t gha-runner:latest ./runner/
    
    # Construir resto de servicios con docker-compose
    log_info "Construyendo servicios con docker-compose..."
    docker-compose build
    
    log_info "Imágenes construidas exitosamente"
}

# Verificar variables de entorno
check_env() {
    log_info "Verificando variables de entorno..."
    
    if [ ! -f .env ]; then
        log_warn "Archivo .env no encontrado, usando .env.example"
        if [ -f .env.example ]; then
            cp .env.example .env
            log_warn "Por favor, edita .env con tus configuraciones"
        else
            log_error "No se encontró .env.example"
            exit 1
        fi
    fi
    
    # Verificar variable obligatoria
    if ! grep -q "GITHUB_TOKEN=" .env || grep -q "GITHUB_TOKEN=$" .env; then
        log_error "GITHUB_TOKEN es obligatorio en .env"
        exit 1
    fi
    
    log_info "Variables de entorno verificadas"
}

# Main
main() {
    log_info "Iniciando construcción de GHA Ephemeral Runners..."
    
    check_dependencies
    check_env
    build_images
    
    log_info "Construcción completada exitosamente"
    log_info "Para iniciar los servicios: ./deploy.sh"
}

# Ejecutar main
main "$@"
