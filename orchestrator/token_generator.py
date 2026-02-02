import os
import requests
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class TokenGenerator:
    def __init__(self, github_token: str):
        self.github_token = github_token
        self.api_base = "https://api.github.com"
        self.headers = {
            "Authorization": f"token {github_token}",
            "Accept": "application/vnd.github.v3+json"
        }
    
    def generate_registration_token(self, scope: str, scope_name: str) -> str:
        """
        Genera un registration token para GitHub Actions runner.
        
        Args:
            scope: 'repo' o 'org'
            scope_name: nombre del repositorio (formato: owner/repo) u organización
            
        Returns:
            Registration token temporal
            
        Raises:
            ValueError: Si los parámetros son inválidos
            requests.RequestException: Si falla la llamada a la API
        """
        if scope not in ['repo', 'org']:
            raise ValueError(f"Scope inválido: {scope}. Debe ser 'repo' u 'org'")
        
        if not scope_name:
            raise ValueError("scope_name es obligatorio")
        
        if scope == 'repo' and '/' not in scope_name:
            raise ValueError("Para scope='repo', scope_name debe tener formato owner/repo")
        
        try:
            if scope == 'repo':
                url = f"{self.api_base}/repos/{scope_name}/actions/runners/registration-token"
            else:  # org
                url = f"{self.api_base}/orgs/{scope_name}/actions/runners/registration-token"
            
            logger.info(f"Generando token para scope: {scope}, name: {scope_name}")
            
            response = requests.post(url, headers=self.headers)
            response.raise_for_status()
            
            token = response.json().get('token')
            if not token:
                raise ValueError("La API no devolvió un token válido")
            
            logger.info("Token generado exitosamente")
            return token
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error generando token: {e}")
            raise
        except Exception as e:
            logger.error(f"Error inesperado: {e}")
            raise
