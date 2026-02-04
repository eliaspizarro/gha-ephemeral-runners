import logging
from typing import Optional

import requests

logger = logging.getLogger(__name__)


class TokenGenerator:
    def __init__(self, github_runner_token: str):
        self.github_runner_token = github_runner_token
        self.api_base = "https://api.github.com"
        self.timeout = 30.0  # Timeout de 30 segundos
        self.headers = {
            "Authorization": f"token {github_runner_token}",
            "Accept": "application/vnd.github.v3+json",
        }

    def generate_registration_token(self, scope: str, scope_name: str) -> str:
        """
        Genera un registration token para GitHub Actions runner.

        Args:
            scope: 'repo' u 'org'
            scope_name: Nombre del repositorio u organización

        Returns:
            Token de registro temporal

        Raises:
            ValueError: Si la API no devuelve un token válido
            requests.exceptions.RequestException: Si hay error en la llamada HTTP
        """
        try:
            if scope == "repo":
                url = f"{self.api_base}/repos/{scope_name}/actions/runners/registration-token"
            else:  # org
                url = f"{self.api_base}/orgs/{scope_name}/actions/runners/registration-token"

            logger.info(f"Generando token para scope: {scope}, name: {scope_name}")

            response = requests.post(url, headers=self.headers, timeout=self.timeout)
            response.raise_for_status()

            token = response.json().get("token")
            if not token:
                raise ValueError("La API no devolvió un token válido")

            logger.info("Token generado exitosamente")
            return token

        except requests.exceptions.Timeout:
            logger.error("Timeout generando token")
            raise requests.exceptions.RequestException("Timeout en la llamada a la API de GitHub")
        except requests.exceptions.RequestException as e:
            logger.error(f"Error generando token: {e}")
            raise
        except Exception as e:
            logger.error(f"Error inesperado: {e}")
