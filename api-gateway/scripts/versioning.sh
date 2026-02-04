#!/bin/bash

# Update version script para GHA API Gateway
# Simple script para actualizar version.py del servicio actual

set -e  # Exit on error

# Variables
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
API_GATEWAY_DIR="$(dirname "$SCRIPT_DIR")"
VERSION_FILE="$API_GATEWAY_DIR/version.py"

echo "🔄 Updating GHA API Gateway Version"
echo "📁 API Gateway dir: $API_GATEWAY_DIR"
echo "📄 Version file: $VERSION_FILE"
echo ""

# Mensaje de uso simple
echo "📖 Usage: $0 [version]"
echo "💡 Examples: $0 | $0 1.2.0 | $0 latest"
echo ""

# Argumento opcional con default (usando variable estándar)
IMAGE_VERSION="${1:-${IMAGE_VERSION:-latest}}"

echo "🔢 New version: $IMAGE_VERSION"
echo ""

# Verificar que el archivo version.py existe
if [ ! -f "$VERSION_FILE" ]; then
    echo "❌ Error: version.py not found at $VERSION_FILE"
    exit 1
fi

# Actualizar version.py
cat > "$VERSION_FILE" << EOF
"""API Gateway Version Management - Single Source of Truth."""

__version__ = "$IMAGE_VERSION"
EOF

echo "✅ Version updated successfully!"
echo "📦 API Gateway version: $IMAGE_VERSION"
echo ""
echo "🎯 To build: ./build.sh"
echo "🎯 To run local: python -m src.main"
