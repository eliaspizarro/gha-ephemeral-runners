import os
import docker
import logging
import uuid
from typing import Dict, List, Optional
from docker.models.containers import Container

logger = logging.getLogger(__name__)

class ContainerManager:
    def __init__(self, runner_image: str):
        self.client = docker.from_env()
        self.runner_image = runner_image
    
    def create_runner_container(self, 
                              registration_token: str,
                              scope: str,
                              scope_name: str,
                              runner_name: Optional[str] = None,
                              runner_group: Optional[str] = None,
                              labels: Optional[List[str]] = None) -> Container:
        """
        Crea un contenedor Docker para un runner efímero.
        
        Args:
            registration_token: Token de registro temporal
            scope: 'repo' u 'org'
            scope_name: Nombre del repositorio u organización
            runner_name: Nombre único del runner (opcional)
            runner_group: Grupo del runner (opcional)
            labels: Labels para el runner (opcional)
            
        Returns:
            Contenedor Docker creado
            
        Raises:
            docker.errors.DockerException: Si falla la creación del contenedor
        """
        if not runner_name:
            runner_name = f"ephemeral-runner-{uuid.uuid4().hex[:8]}"
        
        environment = {
            "REPO_URL": f"https://github.com/{scope_name}",
            "RUNNER_TOKEN": registration_token,
            "RUNNER_NAME": runner_name,
            "RUNNER_WORKDIR": f"/tmp/github-runner-{scope_name}",
            "LABELS": "self-hosted,ephemeral"
        }
        
        if runner_group:
            environment["RUNNER_GROUP"] = runner_group
        
        if labels:
            environment["RUNNER_LABELS"] = ",".join(labels)
        
        container_name = f"gha-runner-{runner_name}"
        
        try:
            logger.info(f"Creando contenedor: {container_name}")
            
            container = self.client.containers.run(
                self.runner_image,
                name=container_name,
                environment=environment,
                detach=True,
                remove=True,  # Auto-remove cuando se detiene
                labels={
                    "gha-ephemeral": "true",
                    "runner-name": runner_name,
                    "scope": scope,
                    "scope_name": scope_name,  # Consistente con guion bajo
                    "repo": scope_name,         # Para compatibilidad con get_active_runners_for_repo
                    "scope-name": scope_name    # Para compatibilidad con código existente
                }
            )
            
            logger.info(f"Contenedor creado: {container.id[:12]}")
            return container
            
        except docker.errors.DockerException as e:
            logger.error(f"Error creando contenedor: {e}")
            raise
    
    def get_runner_containers(self) -> List[Container]:
        """
        Obtiene todos los contenedores de runners efímeros activos.
        
        Returns:
            Lista de contenedores activos
        """
        try:
            containers = self.client.containers.list(
                filters={"label": "gha-ephemeral=true"}
            )
            return containers
        except docker.errors.DockerException as e:
            logger.error(f"Error listando contenedores: {e}")
            raise
    
    def get_container_by_name(self, runner_name: str) -> Optional[Container]:
        """
        Busca un contenedor por el nombre del runner.
        
        Args:
            runner_name: Nombre del runner
            
        Returns:
            Contenedor encontrado o None
        """
        try:
            containers = self.client.containers.list(
                all=True,
                filters={"label": f"runner-name={runner_name}"}
            )
            return containers[0] if containers else None
        except docker.errors.DockerException as e:
            logger.error(f"Error buscando contenedor: {e}")
            return None
    
    def stop_container(self, container: Container, timeout: int = 30) -> bool:
        """
        Detiene un contenedor de runner.
        
        Args:
            container: Contenedor a detener
            timeout: Timeout para detener
            
        Returns:
            True si se detuvo exitosamente
        """
        try:
            logger.info(f"Deteniendo contenedor: {container.id[:12]}")
            container.stop(timeout=timeout)
            return True
        except docker.errors.DockerException as e:
            logger.error(f"Error deteniendo contenedor: {e}")
            return False
