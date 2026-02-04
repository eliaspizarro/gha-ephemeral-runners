#!/bin/bash

# Build script para GHA API Gateway
# Simple wrapper para docker build - no duplica lógica del Dockerfile

set -e  # Exit on error

# Variables
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
API_GATEWAY_DIR="$(dirname "$SCRIPT_DIR")"
DOCKER_DIR="$API_GATEWAY_DIR/docker"

echo "🏗️  Building GHA API Gateway Docker Image"
echo "📁 API Gateway dir: $API_GATEWAY_DIR"
echo "🐳 Docker dir: $DOCKER_DIR"
echo ""

# Mensaje de uso simple
echo "📖 Usage: $0 [registry] [version]"
echo "💡 Examples: $0 | $0 myreg.com | $0 localhost 1.2.0"
echo ""

# Argumentos opcionales con defaults (usando variables estándar)
REGISTRY="${1:-${REGISTRY:-localhost}}"
IMAGE_VERSION="${2:-${IMAGE_VERSION:-latest}}"

# Aplicar variables a las variables del script
IMAGE_NAME="${REGISTRY}/gha-api-gateway"
IMAGE_TAG="$IMAGE_VERSION"

echo "📦 Image: $IMAGE_NAME:$IMAGE_TAG"
echo ""

# Verificar que Dockerfile existe
if [ ! -f "$DOCKER_DIR/Dockerfile" ]; then
    echo "❌ Error: Dockerfile not found at $DOCKER_DIR/Dockerfile"
    exit 1
fi

# Ejecutar docker build
echo "🚀 Running docker build..."
cd "$API_GATEWAY_DIR"
docker build \
    -f docker/Dockerfile \
    --build-arg REGISTRY="$REGISTRY" \
    --build-arg IMAGE_VERSION="$IMAGE_VERSION" \
    -t "$IMAGE_NAME:$IMAGE_TAG" \
    -t "$IMAGE_NAME:latest" \
    .

echo ""
echo "✅ Build completed successfully!"
echo "📦 Image: $IMAGE_NAME:$IMAGE_TAG"
echo ""
echo "🎯 To run: docker run -p 8080:8080 $IMAGE_NAME:$IMAGE_TAG"
