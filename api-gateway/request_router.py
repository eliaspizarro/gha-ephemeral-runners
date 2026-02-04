import logging
from typing import Any, Dict, List

import httpx
from fastapi import HTTPException

logger = logging.getLogger(__name__)


class RequestRouter:
    def __init__(self, orchestrator_url: str):
        self.orchestrator_url = orchestrator_url.rstrip("/")
        self.timeout = 30.0

        # Configurar headers base
        self.headers = {"Content-Type": "application/json", "User-Agent": "GHA-API-Gateway/1.0.0"}

    async def forward_request(self, method: str, path: str, **kwargs) -> Dict[str, Any]:
        """
        Reenvía una solicitud al orchestrator.

        Args:
            method: Método HTTP
            path: Path de la solicitud
            **kwargs: Argumentos adicionales

        Returns:
            Respuesta del orchestrator

        Raises:
            HTTPException: Si hay error en la solicitud
        """
        url = f"{self.orchestrator_url}{path}"

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.request(method, url, headers=self.headers, **kwargs)

                logger.info(f"Solicitud {method} {url} - Status: {response.status_code}")

                if response.status_code >= 400:
                    error_detail = "Error del servidor"
                    try:
                        error_data = response.json()
                        error_detail = error_data.get("detail", error_detail)
                    except (ValueError, KeyError):
                        pass

                    raise HTTPException(status_code=response.status_code, detail=error_detail)

                return response.json()

        except httpx.TimeoutException:
            logger.error("Timeout del orquestador")
            raise HTTPException(status_code=504, detail="Timeout del orquestador")
        except httpx.RequestError:
            logger.error("Orquestador no disponible")
            raise HTTPException(status_code=503, detail="Orquestador no disponible")
        except Exception as e:
            logger.error(f"Error interno del gateway: {e}")
            raise HTTPException(status_code=500, detail="Error interno del gateway")

    def validate_required_fields(self, request_data: Dict[str, Any]) -> None:
        """Valida campos obligatorios."""
        required_fields = ["scope", "scope_name"]

        for field in required_fields:
            if field not in request_data:
                raise HTTPException(status_code=400, detail=f"Campo obligatorio faltante: {field}")

    def validate_scope(self, scope: str) -> None:
        """Valida el scope."""
        if scope not in ["repo", "org"]:
            raise HTTPException(status_code=400, detail="Scope debe ser 'repo' u 'org'")

    def validate_repo_format(self, scope_name: str) -> None:
        """Valida formato de repositorio para scope 'repo'."""
        if "/" not in scope_name:
            raise HTTPException(
                status_code=400,
                detail="Para scope='repo', scope_name debe tener formato owner/repo",
            )

    def validate_count(self, count: Any) -> None:
        """Valida el campo count."""
        if not isinstance(count, int) or count < 1 or count > 10:
            raise HTTPException(status_code=400, detail="Count debe ser un entero entre 1 y 10")

    def validate_labels(self, labels: Any) -> None:
        """Valida el campo labels."""
        if labels is None:
            return

        if not isinstance(labels, list):
            raise HTTPException(status_code=400, detail="Labels debe ser una lista")

        for label in labels:
            if not isinstance(label, str) or len(label.strip()) == 0:
                raise HTTPException(
                    status_code=400, detail="Cada label debe ser una cadena no vacía"
                )

    def validate_runner_request(self, request_data: Dict[str, Any]) -> bool:
        """
        Valida los datos de una solicitud de creación de runner.

        Args:
            request_data: Datos a validar

        Returns:
            True si los datos son válidos

        Raises:
            HTTPException: Si los datos son inválidos
        """
        # Validar campos obligatorios
        self.validate_required_fields(request_data)

        # Validar scope
        scope = request_data.get("scope")
        self.validate_scope(scope)

        # Validar scope_name para repo
        if scope == "repo":
            scope_name = request_data.get("scope_name", "")
            self.validate_repo_format(scope_name)

        # Validar count
        count = request_data.get("count", 1)
        self.validate_count(count)

        # Validar labels
        labels = request_data.get("labels")
        self.validate_labels(labels)

        return True

    async def create_runner(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Crea un runner a través del orchestrator."""
        self.validate_runner_request(request_data)
        return await self.forward_request("POST", "/runners/create", json=request_data)

    async def get_runner_status(self, runner_id: str) -> Dict[str, Any]:
        """Obtiene el estado de un runner."""
        return await self.forward_request("GET", f"/runners/{runner_id}/status")

    async def destroy_runner(self, runner_id: str) -> Dict[str, Any]:
        """Destruye un runner."""
        return await self.forward_request("DELETE", f"/runners/{runner_id}")

    async def list_runners(self) -> Dict[str, Any]:
        """Lista todos los runners activos."""
        return await self.forward_request("GET", "/runners")

    async def cleanup_runners(self) -> Dict[str, Any]:
        """Limpia runners inactivos."""
        return await self.forward_request("POST", "/runners/cleanup")

    async def get_health(self) -> Dict[str, Any]:
        """Verifica salud del servicio."""
        return await self.forward_request("GET", "/health")

    async def get_health_docker(self) -> Dict[str, Any]:
        """Health check nativo para Docker."""
        return await self.forward_request("GET", "/healthz")
