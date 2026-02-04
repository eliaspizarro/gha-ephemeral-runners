"""
Utilitarios de validación reutilizables.

Rol: Proveer funciones de validación comunes para toda la aplicación.
Validar nombres, scopes, configuración y otros datos.
Funciones puras sin dependencias externas.

Depende de: expresiones regulares, tipos de datos.
"""

import re
from typing import Optional, Tuple

from .constants import (
    MAX_RUNNER_NAME_LENGTH,
    REPO_NAME_PATTERN,
    RUNNER_NAME_PATTERN,
    ScopeType,
)


def validate_runner_name(runner_name: str) -> str:
    """
    Valida y normaliza nombre de runner.

    Args:
        runner_name: Nombre a validar

    Returns:
        Nombre validado

    Raises:
        ValueError: Si el nombre es inválido
    """
    if not runner_name:
        raise ValueError("runner_name no puede estar vacío")

    if len(runner_name) > MAX_RUNNER_NAME_LENGTH:
        raise ValueError(f"runner_name no puede exceder {MAX_RUNNER_NAME_LENGTH} caracteres")

    if not re.match(RUNNER_NAME_PATTERN, runner_name):
        raise ValueError("runner_name contiene caracteres inválidos")

    return runner_name


def validate_scope(scope: str) -> str:
    """
    Valida el tipo de scope.

    Args:
        scope: Tipo de scope a validar

    Returns:
        Scope validado

    Raises:
        ValueError: Si el scope es inválido
    """
    valid_scopes = [s.value for s in ScopeType]
    
    if scope not in valid_scopes:
        raise ValueError(f"scope debe ser uno de: {', '.join(valid_scopes)}")
    
    return scope


def validate_repository(repo_name: str) -> str:
    """
    Valida formato de nombre de repositorio.

    Args:
        repo_name: Nombre del repositorio en formato owner/repo

    Returns:
        Nombre validado

    Raises:
        ValueError: Si el formato es inválido
    """
    if not repo_name:
        raise ValueError("repo_name no puede estar vacío")

    if not re.match(REPO_NAME_PATTERN, repo_name):
        raise ValueError("repo_name debe tener formato owner/repo")

    return repo_name


def validate_runner_group(runner_group: Optional[str]) -> Optional[str]:
    """
    Valida grupo de runner (opcional).

    Args:
        runner_group: Grupo a validar

    Returns:
        Grupo validado o None
    """
    if not runner_group:
        return None

    if len(runner_group) > MAX_RUNNER_NAME_LENGTH:
        raise ValueError(f"runner_group no puede exceder {MAX_RUNNER_NAME_LENGTH} caracteres")

    if not re.match(RUNNER_NAME_PATTERN, runner_group):
        raise ValueError("runner_group contiene caracteres inválidos")

    return runner_group


def validate_labels(labels: Optional[list]) -> Optional[list]:
    """
    Valida lista de labels.

    Args:
        labels: Lista de labels a validar

    Returns:
        Labels validados o None
    """
    if not labels:
        return None

    if not isinstance(labels, list):
        raise ValueError("labels debe ser una lista")

    if len(labels) > 10:
        raise ValueError("máximo 10 labels permitidos")

    validated_labels = []
    for label in labels:
        if not isinstance(label, str):
            raise ValueError("todos los labels deben ser strings")
        
        label = label.strip()
        if not label:
            continue
            
        if len(label) > 50:
            raise ValueError("label no puede exceder 50 caracteres")
            
        validated_labels.append(label)

    return validated_labels if validated_labels else None


def validate_timeout(timeout: Optional[int]) -> int:
    """
    Valida timeout.

    Args:
        timeout: Timeout en segundos

    Returns:
        Timeout validado
    """
    if timeout is None:
        from .constants import DEFAULT_TIMEOUT
        return int(DEFAULT_TIMEOUT)

    if not isinstance(timeout, (int, float)):
        raise ValueError("timeout debe ser un número")

    if timeout < 1 or timeout > 3600:  # 1 segundo a 1 hora
        raise ValueError("timeout debe estar entre 1 y 3600 segundos")

    return int(timeout)


def validate_count(count: Optional[int]) -> int:
    """
    Valida cantidad de runners a crear.

    Args:
        count: Cantidad de runners

    Returns:
        Cantidad validada
    """
    if count is None:
        return 1

    if not isinstance(count, int):
        raise ValueError("count debe ser un entero")

    if count < 1 or count > 10:
        raise ValueError("count debe estar entre 1 y 10")

    return count


def parse_repository_parts(repo_name: str) -> Tuple[str, str]:
    """
    Parsea nombre de repositorio en owner y repo.

    Args:
        repo_name: Nombre en formato owner/repo

    Returns:
        Tupla (owner, repo)
    """
    validate_repository(repo_name)
    
    parts = repo_name.split("/", 1)
    if len(parts) != 2:
        raise ValueError("repo_name debe tener formato owner/repo")
    
    owner, repo = parts
    return owner.strip(), repo.strip()
