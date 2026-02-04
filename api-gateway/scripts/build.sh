#!/bin/bash

# Build script para GHA API Gateway
# Simple wrapper para docker build - no duplica lógica del Dockerfile

set -e  # Exit on error

# Variables
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
API_GATEWAY_DIR="$(dirname "$SCRIPT_DIR")"
DOCKER_DIR="$API_GATEWAY_DIR/docker"
IMAGE_NAME="${REGISTRY:-localhost}/gha-api-gateway"
IMAGE_TAG="${IMAGE_VERSION:-latest}"

echo "🏗️  Building GHA API Gateway Docker Image"
echo "📁 API Gateway dir: $API_GATEWAY_DIR"
echo "🐳 Docker dir: $DOCKER_DIR"
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
