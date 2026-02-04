"""
Caso de uso para descubrimiento automático de repositorios.

Rol: Orquestar el descubrimiento automático de repositorios needing runners.
Busca repositorios, identifica necesidades y crea runners proactivamente.
Implementa la lógica de detección automática de jobs en cola.

Depende de: GitHubService, CreateRunner use case.
"""

# AutoDiscovery: Caso de uso que encuentra y crea runners automáticamente
# Flujo: buscar repos → identificar jobs → crear runners proactivamente
# Habilita el modo automático de creación de runners
