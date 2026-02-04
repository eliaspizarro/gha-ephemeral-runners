"""
Servicio de lógica de negocio relacionada con GitHub.

Rol: Contener la lógica de negocio pura para interactuar con GitHub.
Interpreta estados de workflows y decide acciones basadas en GitHub.
No contiene código HTTP, solo lógica de interpretación y decisión.

Depende de: TokenProvider (interface) para obtener tokens.
"""

# GitHubService: Lógica pura de interpretación de GitHub API
# Métodos: analyze_workflow_state(), should_create_runner(), get_active_workflows()
# Transforma datos de GitHub en decisiones de negocio
