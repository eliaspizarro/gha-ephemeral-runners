#!/usr/bin/env python3

import os
import sys
import subprocess
import time
import argparse
import logging
from typing import List, Tuple, Dict, Optional

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DeployManager:
    def __init__(self, registry: str = "your-registry.com"):
        self.registry = registry
        # Leer variables de entorno
        self.load_env()
        
        # Construir lista de imágenes basada en configuración
        image_version = os.getenv("IMAGE_VERSION", "latest")
        self.images = [
            f"{registry}/gha-runner:{image_version}",
            f"{registry}/gha-orchestrator:{image_version}",
            f"{registry}/gha-api-gateway:{image_version}"
        ]
    
    def load_env(self):
        """Carga variables de entorno desde archivo .env."""
        try:
            if os.path.exists(".env"):
                with open(".env", "r") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            key, value = line.split("=", 1)
                            os.environ[key] = value
        except Exception as e:
            logger.warning(f"Error cargando .env: {e}")
    
    def run_command(self, cmd: List[str], cwd: str = None, capture_output: bool = True) -> Tuple[bool, str]:
        """
        Ejecuta un comando y retorna el resultado.
        
        Args:
            cmd: Comando a ejecutar
            cwd: Directorio de trabajo
            capture_output: Si capturar output
            
        Returns:
            Tuple (exit_code, output)
        """
        try:
            logger.info(f"Ejecutando: {' '.join(cmd)}")
            
            if capture_output:
                result = subprocess.run(
                    cmd,
                    cwd=cwd,
                    capture_output=True,
                    text=True,
                    timeout=300
                )
                output = result.stdout
                if result.stderr:
                    output += f"\nSTDERR: {result.stderr}"
            else:
                result = subprocess.run(cmd, cwd=cwd, timeout=300)
                output = ""
            
            if result.returncode == 0:
                logger.info("Comando ejecutado exitosamente")
                return True, output
            else:
                logger.error(f"Error en comando (código {result.returncode}): {output}")
                return False, output
                
        except subprocess.TimeoutExpired:
            logger.error("Timeout en ejecución del comando")
            return False, "Timeout en ejecución"
        except Exception as e:
            logger.error(f"Error inesperado: {e}")
            return False, str(e)
    
    def check_dependencies(self) -> bool:
        """Verifica que las dependencias estén instaladas."""
        logger.info("Verificando dependencias...")
        
        dependencies = {
            "docker": "Docker",
            "docker-compose": "Docker Compose",
            "python3": "Python 3"
        }
        
        for cmd, name in dependencies.items():
            success, _ = self.run_command([cmd, "--version"])
            if not success:
                logger.error(f"{name} no está instalado")
                return False
        
        logger.info("Dependencias verificadas")
        return True
    
    def check_config(self) -> bool:
        """Verifica la configuración del entorno."""
        logger.info("Verificando configuración...")
        
        if not os.path.exists(".env"):
            logger.error("Archivo .env no encontrado")
            logger.info("Ejecuta: cp .env.example .env y configúralo")
            return False
        
        # Leer y verificar variables obligatorias
        try:
            with open(".env", "r") as f:
                env_content = f.read()
            
            required_vars = ["GITHUB_TOKEN", "REGISTRY"]
            for var in required_vars:
                if f"{var}=" not in env_content or f"{var}=$" in env_content:
                    logger.error(f"{var} es obligatorio en .env")
                    return False
            
        except Exception as e:
            logger.error(f"Error leyendo .env: {e}")
            return False
        
        logger.info("Configuración verificada")
        return True
    
    def pull_images(self) -> bool:
        """Descarga las imágenes del registry."""
        logger.info("Descargando imágenes del registry...")
        
        for image in self.images:
            logger.info(f"Descargando: {image}")
            
            success, output = self.run_command(["docker", "pull", image])
            if not success:
                logger.error(f"Error descargando {image}")
                return False
            
            # Tag local para compatibilidad (solo para runner)
            if "gha-runner:latest" in image:
                success, _ = self.run_command(["docker", "tag", image, "gha-runner:latest"])
                if not success:
                    logger.warning("Error creando tag local para runner")
        
        logger.info("Imágenes descargadas exitosamente")
        return True
    
    def verify_images(self) -> bool:
        """Verifica que las imágenes existan localmente."""
        logger.info("Verificando imágenes locales...")
        
        for image in self.images:
            success, _ = self.run_command(["docker", "image", "inspect", image])
            if not success:
                logger.warning(f"Imagen {image} no encontrada localmente")
                return False
        
        logger.info("Imágenes verificadas")
        return True
    
    def start_services(self) -> bool:
        """Inicia los servicios."""
        logger.info("Iniciando servicios...")
        
        # Detener servicios existentes
        self.run_command(["docker-compose", "down"], capture_output=False)
        
        # Iniciar servicios
        success, output = self.run_command(["docker-compose", "up", "-d"])
        if not success:
            logger.error("Error iniciando servicios")
            return False
        
        logger.info("Servicios iniciados")
        return True
    
    def wait_for_services(self) -> bool:
        """Espera a que los servicios estén listos."""
        logger.info("Esperando a que los servicios estén listos...")
        
        # Esperar API Gateway
        logger.info("Esperando API Gateway...")
        for i in range(30):
            success, _ = self.run_command(
                ["curl", "-f", "http://localhost:8080/health"],
                capture_output=False
            )
            if success:
                logger.info("API Gateway está listo")
                break
            if i == 29:
                logger.error("Timeout esperando API Gateway")
                return False
            time.sleep(2)
        
        logger.info("Todos los servicios están listos")
        return True
    
    def stop_services(self) -> bool:
        """Detiene los servicios."""
        logger.info("Deteniendo servicios...")
        success, _ = self.run_command(["docker-compose", "down"])
        if success:
            logger.info("Servicios detenidos")
        return success
    
    def restart_services(self) -> bool:
        """Reinicia los servicios."""
        logger.info("Reiniciando servicios...")
        success, _ = self.run_command(["docker-compose", "restart"])
        if success:
            logger.info("Servicios reiniciados")
        return success
    
    def show_logs(self) -> bool:
        """Muestra logs en tiempo real."""
        logger.info("Mostrando logs (Ctrl+C para salir)...")
        return self.run_command(["docker-compose", "logs", "-f"], capture_output=False)[0]
    
    def show_status(self) -> bool:
        """Muestra estado de los contenedores."""
        logger.info("Estado de los contenedores:")
        return self.run_command(["docker-compose", "ps"])[0]
    
    def show_health(self) -> bool:
        """Verifica salud de los servicios."""
        logger.info("Verificando salud de los servicios...")
        
        try:
            import json
            
            # API Gateway
            logger.info("API Gateway:")
            success, output = self.run_command(["curl", "-s", "http://localhost:8080/health"])
            if success:
                try:
                    health_data = json.loads(output)
                    print(json.dumps(health_data, indent=2))
                except:
                    print(output)
            else:
                print("No disponible")
            
            print()
            
        except Exception as e:
            logger.error(f"Error verificando salud: {e}")
            return False
        
        return True
    
    def show_info(self):
        """Muestra información de despliegue."""
        logger.info("Información de despliegue:")
        print()
        print("API Gateway: http://localhost:8080")
        print(f"Registry: {self.registry}")
        print(f"Image Version: {os.getenv('IMAGE_VERSION', 'latest')}")
        print("Imágenes usadas:")
        for image in self.images:
            print(f"  - {image}")
        print()
        print("Comandos útiles:")
        print("  Ver logs: python3 deploy_registry.py logs")
        print("  Ver estado: python3 deploy_registry.py status")
        print("  Detener: python3 deploy_registry.py stop")
        print("  Actualizar imágenes: python3 deploy_registry.py pull")
        print()
        print("Variables de entorno:")
        print(f"  REGISTRY: {os.getenv('REGISTRY', 'No configurado')}")
        print(f"  IMAGE_VERSION: {os.getenv('IMAGE_VERSION', 'latest')}")
        print(f"  ENABLE_AUTH: {os.getenv('ENABLE_AUTH', 'false')}")
        print()
    
    def deploy(self) -> bool:
        """Ejecuta el despliegue completo."""
        logger.info("Iniciando despliegue con imágenes del registry...")
        
        steps = [
            ("dependencias", self.check_dependencies),
            ("configuración", self.check_config),
            ("imágenes", self.verify_images),
            ("descarga", self.pull_images),
            ("inicio", self.start_services),
            ("espera", self.wait_for_services)
        ]
        
        for step_name, step_func in steps:
            logger.info(f"Verificando {step_name}...")
            if not step_func():
                logger.error(f"Fallo en {step_name}")
                return False
        
        self.show_info()
        logger.info("Despliegue completado exitosamente")
        return True

def main():
    """Función principal."""
    parser = argparse.ArgumentParser(description="Deploy script para GHA Ephemeral Runners con registry")
    parser.add_argument("--registry", default="your-registry.com", help="Registry Docker")
    parser.add_argument("action", nargs="?", default="deploy", 
                       choices=["deploy", "pull", "verify", "stop", "restart", "logs", "status", "health"],
                       help="Acción a ejecutar")
    
    args = parser.parse_args()
    
    # Crear deploy manager
    deployer = DeployManager(args.registry)
    
    try:
        if args.action == "deploy":
            success = deployer.deploy()
        elif args.action == "pull":
            success = deployer.pull_images()
        elif args.action == "verify":
            success = deployer.verify_images()
        elif args.action == "stop":
            success = deployer.stop_services()
        elif args.action == "restart":
            success = deployer.restart_services()
        elif args.action == "logs":
            success = deployer.show_logs()
        elif args.action == "status":
            success = deployer.show_status()
        elif args.action == "health":
            success = deployer.show_health()
        else:
            logger.error(f"Acción desconocida: {args.action}")
            success = False
        
        if not success:
            sys.exit(1)
            
    except KeyboardInterrupt:
        logger.info("Proceso interrumpido por usuario")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Error inesperado: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
