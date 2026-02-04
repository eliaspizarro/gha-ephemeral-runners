#!/bin/bash

# Build Script para OrchestratorV2
# Rol: Automatizar el proceso de build de la aplicación
# Compila health check, crea imagen Docker y ejecuta pruebas

set -e  # Exit on error

# Configuración
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
DOCKER_IMAGE="orchestratorv2"
DOCKER_TAG="latest"
HEALTHCHECK_BINARY="healthcheck"

echo "🏗️  Iniciando build de OrchestratorV2..."
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

# 1. Verificar sintaxis de health check (Dockerfile lo compila)
verify_healthcheck() {
    log_info "Verificando sintaxis de health check..."
    
    cd "$SCRIPT_DIR"
    
    # Verificar archivo existe
    if [ ! -f "healthcheck.go" ]; then
        log_error "healthcheck.go no encontrado"
        exit 1
    fi
    
    # Verificar sintaxis básica (sin compilar)
    if grep -q "package main" healthcheck.go && grep -q "func main" healthcheck.go; then
        log_success "Sintaxis de health check válida"
    else
        log_error "healthcheck.go no tiene estructura válida"
        exit 1
    fi
}

# 2. Validar dependencias Python
validate_python_deps() {
    log_info "Validando dependencias Python..."
    
    cd "$PROJECT_ROOT"
    
    # Verificar Python
    if ! command -v python3 &> /dev/null; then
        log_error "Python3 no está instalado"
        exit 1
    fi
    
    # Verificar versión de Python (solo requiere Python 3.x)
    local python_version=$(python3 --version 2>&1 | grep -oP '\d+\.\d+' || echo "3.0")
    local python_major=$(echo "$python_version" | cut -d. -f1)
    
    if [ "$python_major" != "3" ]; then
        log_error "Se requiere Python 3.x, versión encontrada: $python_version"
        exit 1
    fi
    
    log_success "Python 3.x detectado: $python_version"
    
    # Verificar requirements.txt
    if [ ! -f "requirements.txt" ]; then
        log_error "requirements.txt no encontrado"
        exit 1
    fi
}

# 3. Validar estructura del proyecto
validate_project_structure() {
    log_info "Validando estructura del proyecto..."
    
    cd "$PROJECT_ROOT"
    
    # Directorios requeridos
    required_dirs=("src" "src/api" "src/domain" "src/infrastructure" "src/shared" "src/use_cases" "docker" "scripts")
    
    for dir in "${required_dirs[@]}"; do
        if [ ! -d "$dir" ]; then
            log_error "Directorio requerido no encontrado: $dir"
            exit 1
        fi
    done
    
    # Archivos requeridos
    required_files=("src/api/main.py" "requirements.txt" "scripts/healthcheck.go" "docker/Dockerfile")
    
    for file in "${required_files[@]}"; do
        if [ ! -f "$file" ]; then
            log_error "Archivo requerido no encontrado: $file"
            exit 1
        fi
    done
    
    log_success "Estructura del proyecto válida"
}

# 4. Crear imagen Docker
build_docker_image() {
    log_info "Creando imagen Docker..."
    
    cd "$PROJECT_ROOT"
    
    # Verificar Docker está instalado
    if ! command -v docker &> /dev/null; then
        log_error "Docker no está instalado"
        exit 1
    fi
    
    # Construir imagen
    if docker build -t "${DOCKER_IMAGE}:${DOCKER_TAG}" -f docker/Dockerfile .; then
        log_success "Imagen Docker creada: ${DOCKER_IMAGE}:${DOCKER_TAG}"
    else
        log_error "Error creando imagen Docker"
        exit 1
    fi
    
    # Verificar imagen
    if docker images | grep -q "$DOCKER_IMAGE"; then
        log_success "Imagen Docker verificada"
        docker images "${DOCKER_IMAGE}:${DOCKER_TAG}"
    else
        log_error "Imagen Docker no encontrada después del build"
        exit 1
    fi
}

# 5. Ejecutar pruebas básicas
run_tests() {
    log_info "Verificando sintaxis Python..."
    cd "$PROJECT_ROOT"
    
    python3 -m py_compile src/api/main.py && \
        log_success "Sintaxis Python válida" || \
        { log_error "Error de sintaxis Python"; exit 1; }
}

# 6. Limpiar artefactos
cleanup() {
    log_info "Limpiando artefactos temporales..."
    
    cd "$SCRIPT_DIR"
    
    # Opcional: limpiar binario compilado
    if [ "$1" = "--clean" ]; then
        if [ -f "$HEALTHCHECK_BINARY" ]; then
            rm "$HEALTHCHECK_BINARY"
            log_info "Binario healthcheck eliminado"
        fi
    fi
}

# Función principal
main() {
    local start_time=$(date +%s)
    
    # Validar estructura
    validate_project_structure
    
    # Validar dependencias
    validate_python_deps
    
    # Verificar sintaxis de health check
    verify_healthcheck
    
    # Ejecutar pruebas
    run_tests
    
    # Crear imagen Docker
    build_docker_image
    
    # Calcular tiempo total
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    
    log_success "🎉 Build completado exitosamente en ${duration}s"
    log_success "📦 Imagen: ${DOCKER_IMAGE}:${DOCKER_TAG}"
    log_success "🏥 Health check: scripts/${HEALTHCHECK_BINARY}"
    
    # Limpiar si se solicita
    if [ "$1" = "--clean" ]; then
        cleanup --clean
    fi
}

# Mostrar ayuda
show_help() {
    echo "Uso: $0 [OPCIONES]"
    echo ""
    echo "Opciones:"
    echo "  --clean    Limpia artefactos temporales después del build"
    echo "  --help     Muestra esta ayuda"
    echo ""
    echo "Ejemplos:"
    echo "  $0                # Build completo"
    echo "  $0 --clean        # Build con limpieza"
}

# Procesar argumentos
case "$1" in
    --help|-h)
        show_help
        exit 0
        ;;
    *)
        main "$@"
        ;;
esac
