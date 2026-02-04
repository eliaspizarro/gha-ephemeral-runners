"""
API Gateway - Configuration Settings
Contains environment variables, service configuration, and application constants.
"""

import os
from typing import Optional
from version import __version__

# Environment Variables
API_GATEWAY_PORT: int = int(os.getenv("API_GATEWAY_PORT", "8080"))
ORCHESTRATOR_PORT: str = os.getenv("ORCHESTRATOR_PORT", "8000")
ORCHESTRATOR_URL: str = f"http://orchestrator:{ORCHESTRATOR_PORT}"
CORS_ORIGINS: str = os.getenv("CORS_ORIGINS", "*")

# Service Configuration
USER_AGENT: str = f"GHA-API-Gateway/{__version__}"

# Logging Configuration
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

# Application Constants
APP_TITLE: str = "GitHub Actions Ephemeral Runners API Gateway"
APP_DESCRIPTION: str = "Gateway para la plataforma de runners efímeros de GitHub Actions"
APP_VERSION: str = __version__
API_PREFIX: str = "/api/v1"

# Health Check Configuration
HEALTH_CHECK_INTERVAL: str = "30s"
HEALTH_CHECK_TIMEOUT: str = "10s"
HEALTH_CHECK_START_PERIOD: str = "5s"
HEALTH_CHECK_RETRIES: int = 3

# Docker Configuration
DOCKER_EXPOSED_PORT: int = 8080
DOCKER_HOST: str = "0.0.0.0"

# Logging Configuration
LOG_LEVEL: str = "INFO"
LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# Headers Configuration
DEFAULT_HEADERS = {
    "Content-Type": "application/json",
    "User-Agent": USER_AGENT,
}

# CORS Configuration
CORS_ALLOW_CREDENTIALS: bool = True
CORS_ALLOW_METHODS: list[str] = ["GET", "POST", "PUT", "DELETE"]
CORS_ALLOW_HEADERS: list[str] = ["*"]
