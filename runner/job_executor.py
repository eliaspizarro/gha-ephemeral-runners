import os
import signal
import logging
import threading
import time
from typing import Optional
from .registration_service import RegistrationService

logger = logging.getLogger(__name__)

class JobExecutor:
    def __init__(self, registration_service: RegistrationService):
        self.registration_service = registration_service
        self.runner_pid: Optional[int] = None
        self.running = False
        self.shutdown_event = threading.Event()
    
    def start_execution(self, idle_timeout: int = 3600) -> bool:
        """
        Inicia la ejecución de jobs.
        
        Args:
            idle_timeout: Timeout de inactividad en segundos
            
        Returns:
            True si se inició exitosamente
        """
        try:
            if not self.registration_service.is_runner_registered():
                logger.error("Runner no está registrado")
                return False
            
            logger.info("Iniciando ejecutor de jobs")
            self.running = True
            
            # Iniciar el runner
            self.runner_pid = self.registration_service.start_runner(idle_timeout)
            
            if self.runner_pid == 0:
                logger.error("No se pudo iniciar el runner")
                return False
            
            # Iniciar monitoreo en segundo plano
            monitor_thread = threading.Thread(
                target=self._monitor_runner,
                daemon=True
            )
            monitor_thread.start()
            
            logger.info(f"Ejecutor iniciado con PID: {self.runner_pid}")
            return True
            
        except Exception as e:
            logger.error(f"Error iniciando ejecutor: {e}")
            return False
    
    def stop_execution(self, timeout: int = 30) -> bool:
        """
        Detiene la ejecución de jobs.
        
        Args:
            timeout: Timeout para detener
            
        Returns:
            True si se detuvo exitosamente
        """
        try:
            logger.info("Deteniendo ejecutor de jobs")
            self.running = False
            self.shutdown_event.set()
            
            if self.runner_pid:
                # Enviar SIGTERM al proceso del runner
                try:
                    os.kill(self.runner_pid, signal.SIGTERM)
                    logger.info(f"Enviada señal SIGTERM al PID {self.runner_pid}")
                    
                    # Esperar a que termine
                    for i in range(timeout):
                        try:
                            os.kill(self.runner_pid, 0)  # Verificar si existe
                            time.sleep(1)
                        except ProcessLookupError:
                            logger.info("Proceso del runner terminado")
                            return True
                    
                    # Si no terminó, enviar SIGKILL
                    logger.warning("Enviando SIGKILL al runner")
                    os.kill(self.runner_pid, signal.SIGKILL)
                    
                except ProcessLookupError:
                    logger.info("Proceso del runner ya no existe")
                    return True
                except Exception as e:
                    logger.error(f"Error deteniendo runner: {e}")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error en stop_execution: {e}")
            return False
    
    def wait_for_completion(self, timeout: int = 86400) -> int:
        """
        Espera a que el runner complete su ejecución.
        
        Args:
            timeout: Timeout máximo en segundos
            
        Returns:
            Código de salida del runner
        """
        if not self.runner_pid:
            logger.error("No hay runner en ejecución")
            return -1
        
        try:
            exit_code = self.registration_service.wait_for_runner(self.runner_pid)
            self.running = False
            return exit_code
        except Exception as e:
            logger.error(f"Error esperando completion: {e}")
            return -1
    
    def is_running(self) -> bool:
        """
        Verifica si el ejecutor está activo.
        
        Returns:
            True si está en ejecución
        """
        if not self.running or not self.runner_pid:
            return False
        
        try:
            # Verificar si el proceso existe
            os.kill(self.runner_pid, 0)
            return True
        except ProcessLookupError:
            self.running = False
            return False
        except Exception:
            return False
    
    def get_status(self) -> dict:
        """
        Obtiene el estado actual del ejecutor.
        
        Returns:
            Diccionario con estado
        """
        return {
            "running": self.is_running(),
            "pid": self.runner_pid,
            "registered": self.registration_service.is_runner_registered()
        }
    
    def _monitor_runner(self):
        """
        Monitorea el proceso del runner en segundo plano.
        """
        while self.running and not self.shutdown_event.is_set():
            try:
                if self.runner_pid:
                    # Verificar si el proceso sigue activo
                    try:
                        os.kill(self.runner_pid, 0)
                    except ProcessLookupError:
                        logger.info("Proceso del runner terminó")
                        self.running = False
                        break
                
                # Esperar antes de próxima verificación
                self.shutdown_event.wait(30)
                
            except Exception as e:
                logger.error(f"Error en monitoreo: {e}")
                break
        
        logger.info("Monitoreo del runner terminado")

class SelfDestructMechanism:
    def __init__(self, job_executor: JobExecutor, registration_service: RegistrationService):
        self.job_executor = job_executor
        self.registration_service = registration_service
        self.active = False
        self.monitor_thread: Optional[threading.Thread] = None
    
    def activate(self, idle_timeout: int = 3600, check_interval: int = 60):
        """
        Activa el mecanismo de autodestrucción.
        
        Args:
            idle_timeout: Timeout de inactividad en segundos
            check_interval: Intervalo de verificación en segundos
        """
        if self.active:
            logger.warning("Mecanismo de autodestrucción ya está activo")
            return
        
        self.active = True
        self.monitor_thread = threading.Thread(
            target=self._self_destruct_loop,
            args=(idle_timeout, check_interval),
            daemon=True
        )
        self.monitor_thread.start()
        logger.info("Mecanismo de autodestrucción activado")
    
    def deactivate(self):
        """Desactiva el mecanismo de autodestrucción."""
        self.active = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        logger.info("Mecanismo de autodestrucción desactivado")
    
    def _self_destruct_loop(self, idle_timeout: int, check_interval: int):
        """
        Bucle de autodestrucción.
        
        Args:
            idle_timeout: Timeout de inactividad
            check_interval: Intervalo de verificación
        """
        last_activity = time.time()
        
        while self.active:
            try:
                # Verificar si el runner está activo
                if not self.job_executor.is_running():
                    # Runner no está activo, verificar cuánto tiempo ha pasado
                    inactive_time = time.time() - last_activity
                    
                    if inactive_time >= idle_timeout:
                        logger.info(f"Runner inactivo por {inactive_time}s, iniciando autodestrucción")
                        self._self_destruct()
                        break
                else:
                    # Runner activo, actualizar timestamp
                    last_activity = time.time()
                
                # Esperar próxima verificación
                time.sleep(check_interval)
                
            except Exception as e:
                logger.error(f"Error en bucle de autodestrucción: {e}")
                time.sleep(check_interval)
    
    def _self_destruct(self):
        """Ejecuta la autodestrucción."""
        try:
            logger.info("Iniciando autodestrucción")
            
            # Detener ejecutor
            self.job_executor.stop_execution()
            
            # Desregistrar runner
            registration_token = os.getenv("GITHUB_REGISTRATION_TOKEN")
            if registration_token:
                self.registration_service.unregister_runner(registration_token)
            
            # Salir del proceso principal
            logger.info("Autodestrucción completada")
            os._exit(0)
            
        except Exception as e:
            logger.error(f"Error en autodestrucción: {e}")
            os._exit(1)
