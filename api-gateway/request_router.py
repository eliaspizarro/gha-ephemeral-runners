import os
import logging
import httpx
from typing import Dict, List, Optional, Any
from fastapi import HTTPException

logger = logging.getLogger(__name__)

class RequestRouter:
    def __init__(self, orchestrator_url: str, api_key: Optional[str] = None):
        self.orchestrator_url = orchestrator_url.rstrip('/')
        self.api_key = api_key
        self.timeout = 30.0
        
        # Configurar headers base
        self.headers = {
            "Content-Type": "application/json",
            "User-Agent": "gha-ephemeral-gateway/1.0.0"
        }
        
        if self.api_key:
            self.headers["X-API-Key"] = self.api_key
    
    async def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """
        Realiza una solicitud HTTP al orquestador.
        
        Args:
            method: Método HTTP
            endpoint: Endpoint del orquestador
            **kwargs: Argumentos adicionales para la solicitud
            
        Returns:
            Respuesta JSON del orquestador
            
        Raises:
            HTTPException: Si la solicitud falla
        """
        url = f"{self.orchestrator_url}{endpoint}"
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.request(
                    method=method,
                    url=url,
                    headers=self.headers,
                    **kwargs
                )
                
                logger.info(f"Solicitud {method} {url} - Status: {response.status_code}")
                
                if response.status_code >= 400:
                    error_detail = "Error del servidor"
                    try:
                        error_data = response.json()
                        error_detail = error_data.get("detail", error_detail)
                    except:
                        pass
                    
                    raise HTTPException(
                        status_code=response.status_code,
                        detail=error_detail
                    )
                
                return response.json()
                
        except httpx.TimeoutException:
            logger.error(f"Timeout en solicitud a {url}")
            raise HTTPException(status_code=504, detail="Timeout del orquestador")
        except httpx.ConnectError:
            logger.error(f"Error de conexión a {url}")
            raise HTTPException(status_code=503, detail="Orquestador no disponible")
        except Exception as e:
            logger.error(f"Error en solicitud a {url}: {e}")
            raise HTTPException(status_code=500, detail="Error interno del gateway")
    
    async def create_runners(self, runner_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Crea runners a través del orquestador.
        
        Args:
            runner_data: Datos para crear runners
            
        Returns:
            Lista de runners creados
        """
        return await self._make_request(
            "POST",
            "/runners/create",
            json=runner_data
        )
    
    async def get_runner_status(self, runner_id: str) -> Dict[str, Any]:
        """
        Obtiene el estado de un runner.
        
        Args:
            runner_id: ID del runner
            
        Returns:
            Estado del runner
        """
        return await self._make_request(
            "GET",
            f"/runners/{runner_id}/status"
        )
    
    async def destroy_runner(self, runner_id: str) -> Dict[str, Any]:
        """
        Destruye un runner.
        
        Args:
            runner_id: ID del runner
            
        Returns:
            Respuesta de destrucción
        """
        return await self._make_request(
            "DELETE",
            f"/runners/{runner_id}"
        )
    
    async def list_runners(self) -> List[Dict[str, Any]]:
        """
        Lista todos los runners activos.
        
        Returns:
            Lista de runners activos
        """
        return await self._make_request(
            "GET",
            "/runners"
        )
    
    async def cleanup_runners(self) -> Dict[str, Any]:
        """
        Limpia runners inactivos.
        
        Returns:
            Resultado de la limpieza
        """
        return await self._make_request(
            "POST",
            "/runners/cleanup"
        )
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Verifica la salud del orquestador.
        
        Returns:
            Estado del orquestador
        """
        return await self._make_request(
            "GET",
            "/health"
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
        required_fields = ["scope", "scope_name"]
        
        for field in required_fields:
            if field not in request_data:
                raise HTTPException(
                    status_code=400,
                    detail=f"Campo obligatorio faltante: {field}"
                )
        
        # Validar scope
        scope = request_data.get("scope")
        if scope not in ["repo", "org"]:
            raise HTTPException(
                status_code=400,
                detail="Scope debe ser 'repo' u 'org'"
            )
        
        # Validar scope_name para repo
        if scope == "repo":
            scope_name = request_data.get("scope_name", "")
            if "/" not in scope_name:
                raise HTTPException(
                    status_code=400,
                    detail="Para scope='repo', scope_name debe tener formato owner/repo"
                )
        
        # Validar count
        count = request_data.get("count", 1)
        if not isinstance(count, int) or count < 1 or count > 10:
            raise HTTPException(
                status_code=400,
                detail="Count debe ser un entero entre 1 y 10"
            )
        
        # Validar labels
        labels = request_data.get("labels")
        if labels is not None:
            if not isinstance(labels, list):
                raise HTTPException(
                    status_code=400,
                    detail="Labels debe ser una lista"
                )
            
            for label in labels:
                if not isinstance(label, str) or len(label.strip()) == 0:
                    raise HTTPException(
                        status_code=400,
                        detail="Cada label debe ser una cadena no vacía"
                    )
        
        return True
