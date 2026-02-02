#!/usr/bin/env python3

import os
import sys
import subprocess
import logging
from typing import List, Dict, Tuple

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DockerBuilder:
    def __init__(self, registry: str = "your-registry.com"):
        self.registry = registry
        self.images = {
            "gha-runner": "./runner",
            "gha-orchestrator": "./orchestrator", 
            "gha-api-gateway": "./api-gateway"
        }
    
    def run_command(self, cmd: List[str], cwd: str = None) -> Tuple[bool, str]:
        """
        Ejecuta un comando y retorna el resultado.
        
        Args:
            cmd: Comando a ejecutar
            cwd: Directorio de trabajo
            
        Returns:
            Tuple (exit_code, output)
        """
        try:
            logger.info(f"Ejecutando: {' '.join(cmd)}")
            result = subprocess.run(
                cmd,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=600  # 10 minutos timeout
            )
            
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
    
    def login_registry(self, username: str, password: str) -> bool:
        """
        Inicia sesión en el registry de Docker.
        
        Args:
            username: Usuario del registry
            password: Contraseña o token
            
        Returns:
            True si el login fue exitoso
        """
        cmd = ["docker", "login", self.registry, "--username", username, "--password-stdin"]
        
        try:
            logger.info(f"Iniciando sesión en {self.registry}")
            result = subprocess.run(
                cmd,
                input=password,
                text=True,
                capture_output=True,
                timeout=60
            )
            
            if result.returncode == 0:
                logger.info("Login exitoso")
                return True
            else:
                logger.error(f"Error en login: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Error en login: {e}")
            return False
    
    def build_image(self, image_name: str, context_path: str) -> bool:
        """
        Construye una imagen Docker.
        
        Args:
            image_name: Nombre de la imagen
            context_path: Ruta del contexto de build
            
        Returns:
            True si el build fue exitoso
        """
        full_image_name = f"{self.registry}/{image_name}:latest"
        cmd = ["docker", "build", "-t", full_image_name, context_path]
        
        success, output = self.run_command(cmd)
        
        if success:
            logger.info(f"Imagen {full_image_name} construida exitosamente")
        else:
            logger.error(f"Error construyendo imagen {image_name}")
        
        return success
    
    def push_image(self, image_name: str) -> bool:
        """
        Sube una imagen al registry.
        
        Args:
            image_name: Nombre de la imagen
            
        Returns:
            True si el push fue exitoso
        """
        full_image_name = f"{self.registry}/{image_name}:latest"
        cmd = ["docker", "push", full_image_name]
        
        success, output = self.run_command(cmd)
        
        if success:
            logger.info(f"Imagen {full_image_name} subida exitosamente")
        else:
            logger.error(f"Error subiendo imagen {image_name}")
        
        return success
    
    def build_and_push_all(self) -> bool:
        """
        Construye y sube todas las imágenes.
        
        Returns:
            True si todas las operaciones fueron exitosas
        """
        logger.info("Iniciando build y push de todas las imágenes...")
        
        for image_name, context_path in self.images.items():
            logger.info(f"Procesando imagen: {image_name}")
            
            # Build
            if not self.build_image(image_name, context_path):
                logger.error(f"Fallo en build de {image_name}")
                return False
            
            # Push
            if not self.push_image(image_name):
                logger.error(f"Fallo en push de {image_name}")
                return False
        
        logger.info("Todas las imágenes procesadas exitosamente")
        return True
    
    def verify_images(self) -> bool:
        """
        Verifica que las imágenes existan localmente.
        
        Returns:
            True si todas las imágenes existen
        """
        logger.info("Verificando imágenes locales...")
        
        for image_name in self.images.keys():
            full_image_name = f"{self.registry}/{image_name}:latest"
            cmd = ["docker", "image", "inspect", full_image_name]
            
            success, _ = self.run_command(cmd)
            
            if not success:
                logger.warning(f"Imagen {full_image_name} no encontrada localmente")
                return False
        
        logger.info("Todas las imágenes verificadas")
        return True
    
    def cleanup_images(self):
        """Limpia imágenes intermedias y no utilizadas."""
        logger.info("Limpiando imágenes Docker...")
        
        # Limpiar imágenes dangling
        cmd = ["docker", "image", "prune", "-f"]
        success, _ = self.run_command(cmd)
        
        if success:
            logger.info("Limpieza de imágenes completada")
        else:
            logger.warning("Error en limpieza de imágenes")

def main():
    """Función principal."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Build y push de imágenes Docker para GHA Ephemeral Runners")
    parser.add_argument("--registry", default="your-registry.com", help="Registry Docker")
    parser.add_argument("--username", help="Usuario del registry")
    parser.add_argument("--password", help="Contraseña del registry")
    parser.add_argument("--no-login", action="store_true", help="Omitir login (usar credenciales existentes)")
    parser.add_argument("--verify-only", action="store_true", help="Solo verificar imágenes existentes")
    parser.add_argument("--cleanup", action="store_true", help="Limpiar imágenes después del build")
    
    args = parser.parse_args()
    
    # Crear builder
    builder = DockerBuilder(args.registry)
    
    try:
        # Login si es necesario
        if not args.no_login and not args.verify_only:
            if not args.username or not args.password:
                logger.error("Se requieren --username y --password para login")
                sys.exit(1)
            
            if not builder.login_registry(args.username, args.password):
                logger.error("Falló login al registry")
                sys.exit(1)
        
        # Verificar solo
        if args.verify_only:
            if builder.verify_images():
                logger.info("Verificación exitosa")
                sys.exit(0)
            else:
                logger.error("Verificación fallida")
                sys.exit(1)
        
        # Build y push
        if not builder.build_and_push_all():
            logger.error("Falló build y push de imágenes")
            sys.exit(1)
        
        # Cleanup si se solicita
        if args.cleanup:
            builder.cleanup_images()
        
        logger.info("Proceso completado exitosamente")
        
    except KeyboardInterrupt:
        logger.info("Proceso interrumpido por usuario")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Error inesperado: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
