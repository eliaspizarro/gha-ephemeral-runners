#!/bin/bash

# Build script para GHA Orchestrator
# Simple wrapper para docker build - no duplica lógica del Dockerfile

set -e  # Exit on error

# Variables
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ORCHESTRATOR_DIR="$(dirname "$SCRIPT_DIR")"
DOCKER_DIR="$ORCHESTRATOR_DIR/docker"
IMAGE_NAME="${REGISTRY:-localhost}/gha-orchestrator"
IMAGE_TAG="${IMAGE_VERSION:-latest}"

echo "🏗️  Building GHA Orchestrator Docker Image"
echo "📁 Orchestrator dir: $ORCHESTRATOR_DIR"
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
cd "$ORCHESTRATOR_DIR"
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
echo "🎯 To run: docker run -p 8000:8000 $IMAGE_NAME:$IMAGE_TAG"
