import os
import time
import logging
import threading
from typing import Dict, List, Optional
from docker.models.containers import Container
from token_generator import TokenGenerator
from container_manager import ContainerManager

logger = logging.getLogger(__name__)

class LifecycleManager:
    def __init__(self, github_token: str, runner_image: str = "ghcr.io/github-runner-images/ubuntu-latest:latest"):
        self.token_generator = TokenGenerator(github_token)
        self.container_manager = ContainerManager(runner_image)
        self.active_runners: Dict[str, Container] = {}
        self.monitoring = False
        self.monitor_thread: Optional[threading.Thread] = None
    
    def create_runner(self, 
                     scope: str,
                     scope_name: str,
                     runner_name: Optional[str] = None,
                     runner_group: Optional[str] = None,
                     labels: Optional[List[str]] = None) -> str:
        """
        Crea un nuevo runner efímero.
        
        Args:
            scope: 'repo' u 'org'
            scope_name: Nombre del repositorio u organización
            runner_name: Nombre único del runner
            runner_group: Grupo del runner
            labels: Labels para el runner
            
        Returns:
            ID del runner creado
            
        Raises:
            ValueError: Si los parámetros son inválidos
            Exception: Si falla la creación
        """
        try:
            logger.info(f"Creando runner para {scope}/{scope_name}")
            
            # Generar token de registro
            registration_token = self.token_generator.generate_registration_token(
                scope, scope_name
            )
            
            # Crear contenedor
            container = self.container_manager.create_runner_container(
                registration_token=registration_token,
                scope=scope,
                scope_name=scope_name,
                runner_name=runner_name,
                runner_group=runner_group,
                labels=labels
            )
            
            # Guardar referencia
            runner_id = container.labels.get("runner-name", container.id[:12])
            self.active_runners[runner_id] = container
            
            logger.info(f"Runner creado exitosamente: {runner_id}")
            return runner_id
            
        except Exception as e:
            logger.error(f"Error creando runner: {e}")
            raise
    
    def get_runner_status(self, runner_id: str) -> Dict:
        """
        Obtiene el estado de un runner.
        
        Args:
            runner_id: ID del runner
            
        Returns:
            Diccionario con estado del runner
        """
        container = self.active_runners.get(runner_id)
        if not container:
            container = self.container_manager.get_container_by_name(runner_id)
        
        if not container:
            return {"status": "not_found", "runner_id": runner_id}
        
        try:
            container.reload()
            status = container.status.lower()
            
            return {
                "status": status,
                "runner_id": runner_id,
                "container_id": container.id[:12],
                "image": container.image.tags[0] if container.image.tags else "unknown",
                "created": container.attrs['Created'],
                "labels": container.labels
            }
        except Exception as e:
            logger.error(f"Error obteniendo estado del runner {runner_id}: {e}")
            return {"status": "error", "runner_id": runner_id, "error": str(e)}
    
    def destroy_runner(self, runner_id: str, timeout: int = 30) -> bool:
        """
        Destruye un runner específico.
        
        Args:
            runner_id: ID del runner a destruir
            timeout: Timeout para detener el contenedor
            
        Returns:
            True si se destruyó exitosamente
        """
        container = self.active_runners.get(runner_id)
        if not container:
            container = self.container_manager.get_container_by_name(runner_id)
        
        if not container:
            logger.warning(f"Runner no encontrado: {runner_id}")
            return False
        
        try:
            success = self.container_manager.stop_container(container, timeout)
            if success:
                self.active_runners.pop(runner_id, None)
                logger.info(f"Runner destruido: {runner_id}")
            return success
        except Exception as e:
            logger.error(f"Error destruyendo runner {runner_id}: {e}")
            return False
    
    def list_active_runners(self) -> List[Dict]:
        """
        Lista todos los runners activos.
        
        Returns:
            Lista de estados de runners activos
        """
        containers = self.container_manager.get_runner_containers()
        runners = []
        
        for container in containers:
            runner_id = container.labels.get("runner-name", container.id[:12])
            status = self.get_runner_status(runner_id)
            runners.append(status)
        
        return runners
    
    def cleanup_inactive_runners(self, max_idle_time: int = 3600) -> int:
        """
        Limpia runners inactivos.
        
        Args:
            max_idle_time: Tiempo máximo de inactividad en segundos
            
        Returns:
            Número de runners limpiados
        """
        cleaned = 0
        containers = self.container_manager.get_runner_containers()
        
        for container in containers:
            try:
                # Verificar si el contenedor está inactivo
                container.reload()
                if container.status == "exited":
                    runner_id = container.labels.get("runner-name", container.id[:12])
                    if self.destroy_runner(runner_id):
                        cleaned += 1
            except Exception as e:
                logger.error(f"Error en limpieza de contenedor: {e}")
        
        if cleaned > 0:
            logger.info(f"Limpiados {cleaned} runners inactivos")
        
        return cleaned
    
    def start_monitoring(self, cleanup_interval: int = 300):
        """
        Inicia el monitoreo automático de runners.
        
        Args:
            cleanup_interval: Intervalo de limpieza en segundos
        """
        if self.monitoring:
            logger.warning("Monitoreo ya está activo")
            return
        
        self.monitoring = True
        self.monitor_thread = threading.Thread(
            target=self._monitor_loop,
            args=(cleanup_interval,),
            daemon=True
        )
        self.monitor_thread.start()
        logger.info("Monitoreo iniciado")
    
    def stop_monitoring(self):
        """Detiene el monitoreo automático."""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        logger.info("Monitoreo detenido")
    
    def _monitor_loop(self, cleanup_interval: int):
        """Bucle de monitoreo en segundo plano."""
        while self.monitoring:
            try:
                self.cleanup_inactive_runners()
                time.sleep(cleanup_interval)
            except Exception as e:
                logger.error(f"Error en bucle de monitoreo: {e}")
                time.sleep(60)  # Esperar antes de reintentar
