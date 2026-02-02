import os
import logging
import hashlib
import hmac
from typing import Optional
from fastapi import HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

logger = logging.getLogger(__name__)

class AuthenticationLayer:
    def __init__(self, api_key: Optional[str] = None, enable_auth: bool = False):
        self.api_key = api_key
        self.enable_auth = enable_auth
        self.security = HTTPBearer(auto_error=False)
        
        if enable_auth and not api_key:
            logger.warning("Autenticación habilitada pero no se proporcionó API_KEY")
    
    async def verify_api_key(self, request: Request) -> bool:
        """
        Verifica la API key en la solicitud.
        
        Args:
            request: Solicitud HTTP
            
        Returns:
            True si la autenticación es exitosa
            
        Raises:
            HTTPException: Si la autenticación falla
        """
        if not self.enable_auth:
            return True
        
        # Obtener API key de diferentes fuentes
        api_key = None
        
        # 1. Header Authorization (Bearer token)
        try:
            credentials: HTTPAuthorizationCredentials = await self.security(request)
            if credentials:
                api_key = credentials.credentials
        except:
            pass
        
        # 2. Header X-API-Key
        if not api_key:
            api_key = request.headers.get("X-API-Key")
        
        # 3. Query parameter api_key
        if not api_key:
            api_key = request.query_params.get("api_key")
        
        if not api_key:
            logger.warning("Solicitud sin API key")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="API key requerida",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Verificar API key
        if not self._verify_key(api_key):
            logger.warning(f"API key inválida: {api_key[:8]}...")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="API key inválida",
            )
        
        logger.debug("API key verificada exitosamente")
        return True
    
    def _verify_key(self, provided_key: str) -> bool:
        """
        Verifica si la API key proporcionada es válida.
        
        Args:
            provided_key: API key a verificar
            
        Returns:
            True si es válida
        """
        if not self.api_key or not provided_key:
            return False
        
        # Comparación segura para evitar timing attacks
        return hmac.compare_digest(provided_key, self.api_key)
    
    def generate_secure_hash(self, data: str) -> str:
        """
        Genera un hash seguro para datos.
        
        Args:
            data: Datos a hashear
            
        Returns:
            Hash SHA-256
        """
        return hashlib.sha256(data.encode()).hexdigest()
    
    def get_client_info(self, request: Request) -> dict:
        """
        Obtiene información del cliente para logging.
        
        Args:
            request: Solicitud HTTP
            
        Returns:
            Información del cliente
        """
        client_info = {
            "ip": request.client.host if request.client else "unknown",
            "user_agent": request.headers.get("User-Agent", "unknown"),
            "method": request.method,
            "url": str(request.url)
        }
        
        # Agregar información de autenticación si está disponible
        if self.enable_auth:
            client_info["authenticated"] = True
        else:
            client_info["authenticated"] = False
        
        return client_info

class RateLimiter:
    def __init__(self, max_requests: int = 100, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = {}  # Simple in-memory rate limiting
    
    async def check_rate_limit(self, client_ip: str) -> bool:
        """
        Verifica si el cliente ha excedido el límite de solicitudes.
        
        Args:
            client_ip: IP del cliente
            
        Returns:
            True si está dentro del límite
            
        Raises:
            HTTPException: Si excede el límite
        """
        import time
        
        current_time = time.time()
        
        # Limpiar solicitudes antiguas
        if client_ip not in self.requests:
            self.requests[client_ip] = []
        
        # Filtrar solicitudes dentro de la ventana
        self.requests[client_ip] = [
            req_time for req_time in self.requests[client_ip]
            if current_time - req_time < self.window_seconds
        ]
        
        # Verificar límite
        if len(self.requests[client_ip]) >= self.max_requests:
            logger.warning(f"Rate limit excedido para IP: {client_ip}")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit excedido. Máximo {self.max_requests} solicitudes por {self.window_seconds} segundos",
            )
        
        # Agregar solicitud actual
        self.requests[client_ip].append(current_time)
        
        return True
    
    def cleanup_old_entries(self):
        """Limpia entradas antiguas del rate limiter."""
        import time
        
        current_time = time.time()
        expired_ips = []
        
        for ip, requests in self.requests.items():
            # Mantener solo IPs con solicitudes recientes
            recent_requests = [
                req_time for req_time in requests
                if current_time - req_time < self.window_seconds * 2
            ]
            
            if not recent_requests:
                expired_ips.append(ip)
            else:
                self.requests[ip] = recent_requests
        
        # Limpiar IPs expiradas
        for ip in expired_ips:
            del self.requests[ip]
