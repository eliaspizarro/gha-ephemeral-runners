#!/usr/bin/env python3

import os
import sys
import subprocess
import logging
from typing import List, Tuple

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DockerBuilder:
    def __init__(self, registry: str, image_version: str):
        self.registry = registry
        self.image_version = image_version
        self.images = {
            "gha-orchestrator": "./orchestrator", 
            "gha-api-gateway": "./api-gateway"
        }
    
    def run_command(self, cmd: List[str]) -> Tuple[bool, str]:
        try:
            logger.info(f"Ejecutando: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
            
            if result.returncode == 0:
                logger.info("Comando ejecutado exitosamente")
                return True, result.stdout
            else:
                logger.error(f"Error en comando: {result.stderr}")
                return False, result.stderr
                
        except subprocess.TimeoutExpired:
            logger.error("Timeout en ejecución del comando")
            return False, "Timeout en ejecución"
        except Exception as e:
            logger.error(f"Error inesperado: {e}")
            return False, str(e)
    
    def build_image(self, image_name: str, context_path: str) -> bool:
        full_image_name = f"{self.registry}/{image_name}:{self.image_version}"
        cmd = ["docker", "build", "-t", full_image_name, context_path]
        
        success, output = self.run_command(cmd)
        
        if success:
            logger.info(f"Imagen {full_image_name} construida exitosamente")
        else:
            logger.error(f"Error construyendo imagen {image_name}")
        
        return success
    
    def push_image(self, image_name: str) -> bool:
        full_image_name = f"{self.registry}/{image_name}:{self.image_version}"
        cmd = ["docker", "push", full_image_name]
        
        success, output = self.run_command(cmd)
        
        if success:
            logger.info(f"Imagen {full_image_name} subida exitosamente")
        else:
            logger.error(f"Error subiendo imagen {image_name}")
        
        return success
    
    def build_and_push_all(self) -> bool:
        logger.info("Iniciando build y push de todas las imágenes...")
        
        for image_name, context_path in self.images.items():
            logger.info(f"Procesando imagen: {image_name}")
            
            if not self.build_image(image_name, context_path):
                logger.error(f"Fallo en build de {image_name}")
                return False
            
            if not self.push_image(image_name):
                logger.error(f"Fallo en push de {image_name}")
                return False
        
        logger.info("Todas las imágenes procesadas exitosamente")
        return True
    
    def cleanup_images(self):
        logger.info("Limpiando imágenes Docker...")
        
        cmd = ["docker", "image", "prune", "-f"]
        success, _ = self.run_command(cmd)
        
        if success:
            logger.info("Limpieza de imágenes completada")
        else:
            logger.warning("Error en limpieza de imágenes")

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Build y push de imágenes Docker para GHA Ephemeral Runners")
    parser.add_argument("--cleanup", action="store_true", help="Limpiar imágenes después del build")
    parser.add_argument("--dry-run", action="store_true", help="Simular ejecución sin hacer cambios")
    
    args = parser.parse_args()
    
    # Cargar variables del archivo .env
    env_file = os.path.join(os.getcwd(), '.env')
    registry = None
    image_version = None
    
    if os.path.exists(env_file):
        logger.info(f"Cargando variables desde {env_file}")
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    if key == "REGISTRY":
                        registry = value
                        logger.info(f"Variable cargada: {key}")
                    elif key == "IMAGE_VERSION":
                        image_version = value
                        logger.info(f"Variable cargada: {key}")
    
    # Validar variables obligatorias
    if not registry:
        logger.error("REGISTRY no encontrado en el archivo .env")
        sys.exit(1)
    
    if not image_version:
        logger.error("IMAGE_VERSION no encontrado en el archivo .env")
        sys.exit(1)
    
    logger.info(f"Usando registry: {registry}")
    logger.info(f"Usando image version: {image_version}")
    
    # Crear builder
    builder = DockerBuilder(registry, image_version)
    
    if args.dry_run:
        logger.info("DRY RUN - Simulando ejecución:")
        for image_name, context_path in builder.images.items():
            full_image_name = f"{builder.registry}/{image_name}:{builder.image_version}"
            logger.info(f"  Build: {context_path} -> {full_image_name}")
            logger.info(f"  Push: {full_image_name}")
        logger.info("DRY RUN completado")
        sys.exit(0)
    
    if not builder.build_and_push_all():
        logger.error("Falló build y push de imágenes")
        sys.exit(1)
    
    if args.cleanup:
        builder.cleanup_images()
    
    logger.info("Proceso completado exitosamente")

if __name__ == "__main__":
    main()
