"""
Excepciones específicas del dominio de negocio.

Rol: Definir excepciones para errores de lógica de negocio.
RunnerNotFound, InvalidRunnerState, WorkflowError.
Excepciones que representan violaciones de reglas de negocio.

Depende de: excepciones base de Python.
"""

# Excepciones base del dominio
class DomainError(Exception):
    """Error base del dominio de negocio."""
    pass


class RunnerNotFound(DomainError):
    """Runner no encontrado en el sistema."""
    pass


class InvalidRunnerState(DomainError):
    """Estado de runner inválido para la operación solicitada."""
    pass


class WorkflowError(DomainError):
    """Error en el estado o procesamiento de workflows."""
    pass


class RepositoryError(DomainError):
    """Error relacionado con configuración de repositorio."""
    pass


class OrchestrationError(DomainError):
    """Error en la lógica de orquestación principal."""
    pass


class ValidationError(DomainError):
    """Error en validación de datos de entrada."""
    pass
