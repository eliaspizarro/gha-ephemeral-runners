import logging
from typing import Optional

import requests

logger = logging.getLogger(__name__)


class TokenGenerator:
    def __init__(self, github_runner_token: str):
        self.github_runner_token = github_runner_token
        self.api_base = "https://api.github.com"
        self.timeout = 30.0
        self.headers = {
            "Authorization": f"token {github_runner_token}",
            "Accept": "application/vnd.github.v3+json",
        }

    def generate_registration_token(self, scope: str, scope_name: str) -> str:
        """Genera un registration token para GitHub Actions runner."""
        endpoint = f"{self._get_endpoint(scope, scope_name)}/actions/runners/registration-token"
        url = f"{self.api_base}/{endpoint}"
        response = requests.post(url, headers=self.headers, timeout=self.timeout)
        return response.json().get("token", "")

    def _get_endpoint(self, scope: str, scope_name: str) -> str:
        """Obtiene endpoint según scope."""
        return f"repos/{scope_name}" if scope == "repo" else f"orgs/{scope_name}"
