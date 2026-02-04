"""
Servicio principal de orquestación de lógica de negocio.

Rol: Coordinar la lógica principal de orquestación sin dependencias técnicas.
Decide cuándo crear/destruir runners basándose en reglas de negocio.
Coordina con GitHub Service y mantiene estado global de runners activos.
"""

# OrchestrationService: Servicio principal que contiene la lógica de negocio
# Métodos: decide_runner_creation(), coordinate_lifecycle(), maintain_state()
# Sin dependencias de Docker o HTTP, solo lógica pura de dominio
