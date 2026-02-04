"""
Cliente HTTP para GitHub API.

Rol: Cliente técnico para interactuar con GitHub API.
Maneja autenticación, requests HTTP y errores de red.
Implementa el contrato TokenProvider del dominio.

Depende de: requests library, configuración de tokens.
"""

# GitHubClient: Implementación HTTP del contrato TokenProvider
# Métodos: get_token(), fetch_workflows(), get_repository_info()
# Maneja rate limits, timeouts y reintentos automáticos
