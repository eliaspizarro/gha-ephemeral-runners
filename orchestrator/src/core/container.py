import logging
import os
import re
import time
import uuid
from typing import Any, Dict, List, Optional

import docker
from src.services.docker import DockerError, DockerUtils
from src.services.environment import EnvironmentManager
from src.utils.helpers import ErrorHandler, format_container_id, validate_runner_name

logger = logging.getLogger(__name__)

# Patrones comunes de timestamp
TIMESTAMP_PATTERNS = [
    r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+Z\s*',      # ISO 8601 nano
    r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z\s*',           # ISO 8601 simple
    r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\s*',             # YYYY-MM-DD HH:MM:SS
    r'\[\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\]\s*',         # [timestamp]
    r'\[\d+\]\s*',                                          # [unix]
]


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

        logger.info(f"🐳 Creando contenedor {container_name} con imagen {self.runner_image}")
        
        container = self.client.containers.run(
            self.runner_image,
            name=container_name,
            environment=environment,
            detach=True,
            labels=container_labels,
        )

        logger.info(f"✅ Contenedor creado: {DockerUtils.format_container_id(container.id)}")
        
        # Esperar a que el contenedor esté completamente iniciado
        if DockerUtils.wait_for_container(container, timeout=30):
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
        """Obtiene logs de un contenedor usando safe_container_operation."""
        try:
            return DockerUtils.safe_container_operation(
                "obtener logs", container, lambda c: c.logs(tail=tail)
            )
        except DockerError:
            return "Error obteniendo logs"
        except Exception as e:
            return f"Error inesperado: {str(e)}"

    def log_container_output(self, container: Any, runner_name: str) -> None:
        """Muestra logs del contenedor con detección simple de timestamps."""
        try:
            print(f"📋 Salida del Runner: {runner_name}")
            print("")
            
            logs = self.get_container_logs(container, tail=50)
            if logs and logs != "Error obteniendo logs":
                # Detectar patrón dominante en primeras 10 líneas
                dominant_pattern = self._detect_timestamp_pattern(logs)
                
                for line in logs.split("\n"):
                    if line.strip():
                        clean_line = self._clean_timestamp(line.strip(), dominant_pattern)
                        print(f"  {runner_name} | {clean_line}")
            
            print("")
            
        except Exception as e:
            print(f"❌ Error obteniendo logs del contenedor {runner_name}: {e}")

    def _detect_timestamp_pattern(self, logs: str) -> Optional[str]:
        """Detecta el patrón de timestamp más común."""
        pattern_counts = {}
        
        # Analizar primeras 10 líneas
        for line in logs.split('\n')[:10]:
            for i, pattern in enumerate(TIMESTAMP_PATTERNS):
                if re.match(pattern, line.strip()):
                    pattern_counts[i] = pattern_counts.get(i, 0) + 1
        
        # Retornar patrón más frecuente (si aparece 3+ veces)
        if pattern_counts:
            dominant = max(pattern_counts.items(), key=lambda x: x[1])
            if dominant[1] >= 3:  # Umbral simple
                return TIMESTAMP_PATTERNS[dominant[0]]
        
        return None

    def _clean_timestamp(self, line: str, pattern: Optional[str]) -> str:
        """Elimina timestamp si el patrón coincide."""
        if pattern and re.match(pattern, line):
            return re.sub(pattern, '', line)
        return line

    def get_container_info(self, container: Any) -> Dict[str, Any]:
        """Obtiene información completa de un contenedor usando DockerUtils."""
        return DockerUtils.get_container_info(container)

    def is_container_running(self, container: Any) -> bool:
        """Verifica si un contenedor está en ejecución usando DockerUtils."""
        return DockerUtils.is_container_running(container)

    def get_container_by_name(self, name: str) -> Any:
        """Obtiene un contenedor por su nombre."""
        try:
            containers = self.client.containers.list(
                all=True, filters={"name": name}
            )
            return containers[0] if containers else None
        except:
            return None
