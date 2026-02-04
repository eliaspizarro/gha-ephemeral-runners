"""
Caso de uso para creación de runners efímeros.

Rol: Orquestar el proceso completo de creación de un runner.
Valida parámetros, coordina servicios y maneja errores de creación.
Es el punto de entrada para la lógica de negocio de creación.

Depende de: OrchestrationService, ContainerManager, TokenProvider.
"""

# CreateRunner: Caso de uso que orquesta la creación
# Flujo: validar → coordinar servicios → retornar resultado
# Maneja excepciones de dominio y de infraestructura
