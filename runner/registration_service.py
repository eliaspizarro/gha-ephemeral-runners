import os
import subprocess
import logging
import time
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

class RegistrationService:
    def __init__(self):
        self.runner_dir = "/runner"
        self.config_script = os.path.join(self.runner_dir, "config.sh")
        self.run_script = os.path.join(self.runner_dir, "run.sh")
        self.remove_script = os.path.join(self.runner_dir, "config.sh")
    
    def register_runner(self, 
                       registration_token: str,
                       scope: str,
                       scope_name: str,
                       runner_name: str,
                       runner_group: Optional[str] = None,
                       labels: Optional[str] = None) -> bool:
        """
        Registra el runner con GitHub.
        
        Args:
            registration_token: Token de registro temporal
            scope: 'repo' u 'org'
            scope_name: Nombre del repositorio u organización
            runner_name: Nombre único del runner
            runner_group: Grupo del runner (opcional)
            labels: Labels para el runner (opcional)
            
        Returns:
            True si el registro fue exitoso
        """
        try:
            # Asegurar que el directorio del runner existe
            os.makedirs(self.runner_dir, exist_ok=True)
            
            # Construir URL de GitHub
            if scope == "repo":
                github_url = f"https://github.com/{scope_name}"
            elif scope == "org":
                github_url = f"https://github.com/{scope_name}"
            else:
                logger.error(f"Scope inválido: {scope}")
                return False
            
            # Construir comando de configuración
            cmd = [
                self.config_script,
                "--url", github_url,
                "--token", registration_token,
                "--name", runner_name,
                "--work", "_work",
                "--replace",
                "--unattended"
            ]
            
            # Agregar parámetros opcionales
            if runner_group:
                cmd.extend(["--runnergroup", runner_group])
            
            if labels:
                cmd.extend(["--labels", labels])
            
            logger.info(f"Registrando runner: {runner_name}")
            logger.debug(f"Comando: {' '.join(cmd)}")
            
            # Ejecutar configuración
            result = subprocess.run(
                cmd,
                cwd=self.runner_dir,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode == 0:
                logger.info("Runner registrado exitosamente")
                return True
            else:
                logger.error(f"Error en registro: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            logger.error("Timeout en registro del runner")
            return False
        except Exception as e:
            logger.error(f"Error inesperado en registro: {e}")
            return False
    
    def unregister_runner(self, registration_token: str) -> bool:
        """
        Desregistra el runner de GitHub.
        
        Args:
            registration_token: Token de registro
            
        Returns:
            True si el desregistro fue exitoso
        """
        try:
            cmd = [
                self.remove_script,
                "remove",
                "--token", registration_token
            ]
            
            logger.info("Desregistrando runner")
            
            result = subprocess.run(
                cmd,
                cwd=self.runner_dir,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                logger.info("Runner desregistrado exitosamente")
                return True
            else:
                logger.warning(f"Error en desregistro: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            logger.error("Timeout en desregistro del runner")
            return False
        except Exception as e:
            logger.error(f"Error inesperado en desregistro: {e}")
            return False
    
    def start_runner(self, idle_timeout: int = 3600) -> int:
        """
        Inicia el listener del runner.
        
        Args:
            idle_timeout: Timeout de inactividad en segundos
            
        Returns:
            PID del proceso del runner
        """
        try:
            # Iniciar runner con timeout
            cmd = ["timeout", str(idle_timeout), self.run_script]
            
            logger.info(f"Iniciando runner con timeout: {idle_timeout}s")
            
            # Ejecutar en background
            process = subprocess.Popen(
                cmd,
                cwd=self.runner_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True
            )
            
            logger.info(f"Runner iniciado con PID: {process.pid}")
            return process.pid
            
        except Exception as e:
            logger.error(f"Error iniciando runner: {e}")
            return 0
    
    def wait_for_runner(self, pid: int) -> int:
        """
        Espera a que el runner termine.
        
        Args:
            pid: PID del proceso del runner
            
        Returns:
            Código de salida del proceso
        """
        try:
            import psutil
            
            process = psutil.Process(pid)
            exit_code = process.wait(timeout=86400)  # 24 horas max
            
            logger.info(f"Runner terminó con código: {exit_code}")
            return exit_code
            
        except psutil.NoSuchProcess:
            logger.warning("Proceso del runner no encontrado")
            return -1
        except psutil.TimeoutExpired:
            logger.error("Timeout esperando al runner")
            return -2
        except Exception as e:
            logger.error(f"Error esperando al runner: {e}")
            return -3
    
    def is_runner_registered(self) -> bool:
        """
        Verifica si el runner está registrado.
        
        Returns:
            True si el runner tiene configuración
        """
        try:
            # Verificar archivo de configuración
            config_file = os.path.join(self.runner_dir, ".runner")
            return os.path.exists(config_file)
        except Exception:
            return False
    
    def get_runner_info(self) -> Dict[str, Any]:
        """
        Obtiene información del runner configurado.
        
        Returns:
            Diccionario con información del runner
        """
        info = {
            "registered": self.is_runner_registered(),
            "runner_dir": self.runner_dir,
            "config_exists": os.path.exists(self.config_script),
            "run_exists": os.path.exists(self.run_script)
        }
        
        return info
