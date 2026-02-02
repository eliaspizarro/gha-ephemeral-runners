#!/usr/bin/env python3

import os
import sys
import logging
import signal
import time
from typing import Optional

from .registration_service import RegistrationService
from .job_executor import JobExecutor, SelfDestructMechanism

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class RunnerMain:
    def __init__(self):
        self.registration_service = RegistrationService()
        self.job_executor = JobExecutor(self.registration_service)
        self.self_destruct = SelfDestructMechanism(self.job_executor, self.registration_service)
        self.running = False
    
    def setup_signal_handlers(self):
        """Configura manejadores de señales."""
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Manejador de señales para shutdown graceful."""
        logger.info(f"Recibida señal {signum}, iniciando shutdown")
        self.shutdown()
    
    def validate_environment(self) -> bool:
        """
        Valida las variables de entorno obligatorias.
        
        Returns:
            True si el entorno es válido
        """
        required_vars = [
            "GITHUB_REGISTRATION_TOKEN",
            "SCOPE",
            "SCOPE_NAME"
        ]
        
        missing_vars = []
        for var in required_vars:
            if not os.getenv(var):
                missing_vars.append(var)
        
        if missing_vars:
            logger.error(f"Variables de entorno obligatorias faltantes: {missing_vars}")
            return False
        
        # Validar scope
        scope = os.getenv("SCOPE")
        if scope not in ["repo", "org"]:
            logger.error(f"SCOPE inválido: {scope}. Debe ser 'repo' u 'org'")
            return False
        
        # Validar scope_name para repo
        if scope == "repo":
            scope_name = os.getenv("SCOPE_NAME")
            if "/" not in scope_name:
                logger.error("Para SCOPE='repo', SCOPE_NAME debe tener formato owner/repo")
                return False
        
        return True
    
    def run(self) -> int:
        """
        Ejecuta el ciclo de vida completo del runner.
        
        Returns:
            Código de salida
        """
        try:
            logger.info("Iniciando runner efímero")
            
            # Validar entorno
            if not self.validate_environment():
                return 1
            
            # Obtener variables de entorno
            registration_token = os.getenv("GITHUB_REGISTRATION_TOKEN")
            scope = os.getenv("SCOPE")
            scope_name = os.getenv("SCOPE_NAME")
            runner_name = os.getenv("RUNNER_NAME", f"ephemeral-runner-{int(time.time())}-{os.uname().nodename}")
            runner_group = os.getenv("RUNNER_GROUP")
            labels = os.getenv("RUNNER_LABELS")
            idle_timeout = int(os.getenv("IDLE_TIMEOUT", "3600"))
            
            logger.info(f"Runner: {runner_name}")
            logger.info(f"Scope: {scope}/{scope_name}")
            logger.info(f"Timeout: {idle_timeout}s")
            
            # Configurar manejadores de señales
            self.setup_signal_handlers()
            
            # Registrar runner
            logger.info("Registrando runner con GitHub")
            if not self.registration_service.register_runner(
                registration_token=registration_token,
                scope=scope,
                scope_name=scope_name,
                runner_name=runner_name,
                runner_group=runner_group,
                labels=labels
            ):
                logger.error("Falló el registro del runner")
                return 1
            
            logger.info("Runner registrado exitosamente")
            
            # Activar mecanismo de autodestrucción
            self.self_destruct.activate(idle_timeout=idle_timeout)
            
            # Iniciar ejecución de jobs
            logger.info("Iniciando ejecución de jobs")
            if not self.job_executor.start_execution(idle_timeout=idle_timeout):
                logger.error("Falló el inicio de ejecución")
                self.shutdown()
                return 1
            
            self.running = True
            
            # Esperar a que el runner termine
            exit_code = self.job_executor.wait_for_completion()
            logger.info(f"Runner terminó con código: {exit_code}")
            
            # Shutdown
            self.shutdown()
            
            return exit_code
            
        except KeyboardInterrupt:
            logger.info("Interrupción por teclado")
            self.shutdown()
            return 130
        except Exception as e:
            logger.error(f"Error inesperado: {e}")
            self.shutdown()
            return 1
    
    def shutdown(self):
        """Realiza el shutdown graceful del runner."""
        if not self.running:
            return
        
        logger.info("Iniciando shutdown del runner")
        self.running = False
        
        try:
            # Desactivar autodestrucción
            self.self_destruct.deactivate()
            
            # Detener ejecutor
            self.job_executor.stop_execution()
            
            # Desregistrar runner
            registration_token = os.getenv("GITHUB_REGISTRATION_TOKEN")
            if registration_token:
                self.registration_service.unregister_runner(registration_token)
            
            logger.info("Shutdown completado")
            
        except Exception as e:
            logger.error(f"Error en shutdown: {e}")

def main():
    """Función principal."""
    try:
        runner = RunnerMain()
        exit_code = runner.run()
        sys.exit(exit_code)
    except Exception as e:
        logger.error(f"Error fatal: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
