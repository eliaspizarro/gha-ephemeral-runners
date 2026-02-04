"""
Caso de uso para limpieza masiva de runners.

Rol: Orquestar la limpieza de múltiples runners inactivos.
Identifica candidatos, ejecuta limpieza en batch y reporta resultados.
Implementa la lógica de purga basada en workflows activos.

Depende de: OrchestrationService, GitHubService, ContainerManager.
"""

# CleanupRunners: Caso de uso que orquesta limpieza masiva
# Flujo: identificar candidatos → ejecutar batch cleanup → reportar
# Usa lógica de "purge all unused" simplificada
