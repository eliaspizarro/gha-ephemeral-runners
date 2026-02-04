"""
Contratos/interfaces para dependencias externas del dominio.

Rol: Definir las interfaces que el dominio necesita del mundo exterior.
Permite que el dominio permanezca aislado de implementaciones técnicas.
Usa ABC para definir contratos que deben cumplir las implementaciones.

Implementado por: ContainerManager, TokenProvider en infrastructure.
"""

# ContainerManager: Contrato para gestión de contenedores
# TokenProvider: Contrato para gestión de tokens GitHub
# Ambos usan @abstractmethod para definir métodos requeridos
