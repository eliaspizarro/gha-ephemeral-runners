"""
Caso de uso para destrucción de runners efímeros.

Rol: Orquestar el proceso completo de destrucción de un runner.
Valida existencia, coordina limpieza y maneja timeouts.
Es el punto de entrada para la lógica de negocio de destrucción.

Depende de: OrchestrationService, ContainerManager.
"""

# DestroyRunner: Caso de uso que orquesta la destrucción
# Flujo: validar existencia → coordinar cleanup → manejar timeouts
# Asegura limpieza completa de recursos
