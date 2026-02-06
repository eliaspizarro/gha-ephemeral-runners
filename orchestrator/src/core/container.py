import logging
import os
import time
import uuid
from typing import Any, Dict, List, Optional

import docker
from src.services.docker import DockerError, DockerUtils
from src.services.environment import EnvironmentManager
from src.utils.helpers import ErrorHandler, setup_logger, validate_runner_name

logger = setup_logger(__name__)


class ContainerManager:
    def __init__(self, runner_image: str):
        self.client = docker.from_env()
        self.runner_image = runner_image
        self.environment_manager = EnvironmentManager(runner_image)

    def create_runner_container(
        self,
        registration_token: str,
        scope: str,
        scope_name: str,
        runner_name: Optional[str] = None,
        runner_group: Optional[str] = None,
        labels: Optional[List[str]] = None,
        enable_dind: bool = False,
    ) -> Any:
        """Crea un contenedor Docker para un runner efímero."""
        if not runner_name:
            runner_name = f"ephemeral-runner-{uuid.uuid4().hex[:8]}"
        runner_name = validate_runner_name(runner_name)

        environment = self.environment_manager.process_environment_variables(
            scope_name=scope_name,
            runner_name=runner_name,
            registration_token=registration_token,
        )
        
        if runner_group:
            environment["RUNNER_GROUP"] = runner_group
        if labels:
            environment["RUNNER_LABELS"] = ",".join(labels)

        # Validar y formatear nombre de contenedor
        validated_name = DockerUtils.validate_container_name(runner_name)
        container_name = DockerUtils.format_container_name("gha-runner", validated_name)
        container_labels = DockerUtils.create_container_labels(
            runner_name=runner_name, scope=scope, scope_name=scope_name
        )

        # Configurar Docker-in-Docker si es necesario
        volumes = {}
        security_opt = []
        
        if enable_dind:
            volumes['/var/run/docker.sock'] = {'bind': '/var/run/docker.sock', 'mode': 'rw'}
            security_opt.append('label:disable')
            logger.info(f"🐳 Habilitando Docker-in-Docker para {runner_name}")

        # Configurar comando inyectado si está especificado
        injected_command = os.getenv("RUNNER_COMMAND")
        if injected_command:
            command = injected_command
            logger.info(f"🔍 Aplicando comando: {injected_command}")
        else:
            command = None

        logger.info(f"🐳 Creando contenedor {container_name} con imagen {self.runner_image}")
        
        container = self.client.containers.run(
            self.runner_image,
            command=command,
            name=container_name,
            environment=environment,
            detach=True,
            labels=container_labels,
            volumes=volumes if volumes else None,
            security_opt=security_opt if security_opt else None,
        )

        logger.info(f"✅ Contenedor creado: {DockerUtils.format_container_id(container.id)}")
        
        # Esperar a que el contenedor esté completamente iniciado
        if DockerUtils.wait_for_container(container, timeout=30):
            # Esperar 10 segundos para que el runner genere más logs de configuración
            time.sleep(10)
            self.log_container_output(container, runner_name)
        else:
            logger.error(f"❌ Runner {runner_name} falló al iniciar correctamente")
        
        return container

    def get_runner_container(self, runner_name: str) -> Any:
        """Obtiene un contenedor específico por nombre de runner."""
        try:
            containers = self.client.containers.list(
                all=False, filters={"label": f"runner-name={runner_name}"}
            )
            return containers[0] if containers else None
        except Exception as e:
            logger.error(f"Error obteniendo contenedor {runner_name}: {e}")
            return None

    def get_runner_containers(self) -> List[Any]:
        """Obtiene todos los contenedores de runners efímeros activos."""
        try:
            containers = self.client.containers.list(
                all=False, filters={"label": "gha-ephemeral=true"}
            )
            return containers
        except Exception as e:
            logger.error(f"Error obteniendo contenedores: {e}")
            return []

    def stop_container(self, container: Any, timeout: int = 30) -> bool:
        """Detiene y elimina un contenedor."""
        try:
            container.stop(timeout=timeout)
            container.remove(force=True)
            return True
        except Exception as e:
            logger.error(f"Error deteniendo contenedor: {e}")
            return False

    def get_container_logs(self, container: Any, tail: int = 50) -> str:
        """Obtiene logs de un contenedor directamente."""
        try:
            logs = container.logs(tail=tail)
            if isinstance(logs, bytes):
                return logs.decode("utf-8", errors="replace")
            else:
                return str(logs)
        except Exception as e:
            logger.error(f"Error obteniendo logs del contenedor: {e}")
            return f"Error obteniendo logs: {str(e)}"

    def log_container_output(self, container: Any, runner_name: str) -> None:
        """Muestra logs del contenedor sin filtrar (salida raw)."""
        try:
            print(f"📋 Salida del Runner: {runner_name}")
            print("")
            
            logs = self.get_container_logs(container, tail=200)
            if logs and logs != "Error obteniendo logs":
                for line in logs.split("\n"):
                    if line.strip():
                        print(f"  {runner_name} | {line.strip()}")
            
            print("")
            
        except Exception as e:
            print(f"❌ Error obteniendo logs del contenedor {runner_name}: {e}")

    
    def get_container_by_name(self, name: str) -> Any:
        """Obtiene un contenedor por su nombre."""
        try:
            containers = self.client.containers.list(
                all=True, filters={"name": name}
            )
            return containers[0] if containers else None
        except:
            return None
