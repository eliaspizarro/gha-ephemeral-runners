#!/bin/bash

# Update version script para GHA Orchestrator
# Simple script para actualizar version.py del servicio actual

set -e  # Exit on error

# Variables
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ORCHESTRATOR_DIR="$(dirname "$SCRIPT_DIR")"
VERSION_FILE="$ORCHESTRATOR_DIR/version.py"

echo "🔄 Updating GHA Orchestrator Version"
echo "📁 Orchestrator dir: $ORCHESTRATOR_DIR"
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
"""Orchestrator Version Management - Single Source of Truth."""

__version__ = "$IMAGE_VERSION"
EOF

echo "✅ Version updated successfully!"
echo "📦 Orchestrator version: $IMAGE_VERSION"
echo ""
echo "🎯 To build: ./build.sh"
echo "🎯 To run local: python -m src.main"
