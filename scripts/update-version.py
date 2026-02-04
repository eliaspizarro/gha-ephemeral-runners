#!/usr/bin/env python3
"""
Script para actualizar versiones en toda la arquitectura modular.
Actualiza los archivos version.py de API Gateway y Orchestrator.
"""

import sys
import os
from pathlib import Path

def update_version(new_version: str):
    """Actualiza versión en todos los archivos version.py."""
    
    print(f"🔄 Updating version to {new_version}")
    
    # Actualizar API Gateway
    gateway_version = Path("api-gateway/version.py")
    if gateway_version.exists():
        gateway_version.write_text(f'"""API Gateway Version Management - Single Source of Truth."""\n\n__version__ = "{new_version}"\n')
        print(f"✅ Updated api-gateway/version.py")
    else:
        print(f"❌ api-gateway/version.py not found")
    
    # Actualizar Orchestrator  
    orchestrator_version = Path("orchestrator/version.py")
    if orchestrator_version.exists():
        orchestrator_version.write_text(f'"""Orchestrator Version Management - Single Source of Truth."""\n\n__version__ = "{new_version}"\n')
        print(f"✅ Updated orchestrator/version.py")
    else:
        print(f"❌ orchestrator/version.py not found")
    
    print(f"🎉 Version update completed!")

def main():
    """Función principal."""
    if len(sys.argv) < 2:
        print("Usage: python update-version.py <version>")
        print("Example: python update-version.py 1.2.0")
        sys.exit(1)
    
    version = sys.argv[1]
    
    # Validar formato de versión (básico)
    if not version.startswith(('v', '1', '2', '3', '4', '5', '6', '7', '8', '9', '0')):
        print("❌ Invalid version format. Use semantic versioning (e.g., 1.2.0, v1.2.0)")
        sys.exit(1)
    
    # Remover 'v' prefix si existe
    if version.startswith('v'):
        version = version[1:]
    
    update_version(version)

if __name__ == "__main__":
    main()
