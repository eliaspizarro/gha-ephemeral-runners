"""
Caso de uso para descubrimiento automático de repositorios.

Rol: Orquestar el descubrimiento automático de repositorios.
Busca repositorios, identifica necesidades y crea runners proactivamente.
Implementa la lógica de detección automática de jobs en cola.

Depende de: OrchestrationService, CreateRunner.
"""

import logging
from typing import List, Dict, Any

from ..shared.logging_utils import log_operation_start, log_operation_success, log_operation_error
from ..shared.domain_exceptions import OrchestrationError
from ..domain.orchestration_service import OrchestrationService
from .create_runner import CreateRunner

logger = logging.getLogger(__name__)


class AutoDiscovery:
    """Caso de uso para descubrimiento automático de repositorios."""
    
    def __init__(self, orchestration_service: OrchestrationService):
        """Inicializa caso de uso."""
        self.orchestration_service = orchestration_service
        self.create_runner = CreateRunner(orchestration_service)
        
        # Configuración
        self.max_runners_per_repo = 5
        self.auto_create_threshold = 1  # Crear si hay >= X jobs en cola
    
    def execute(self, dry_run: bool = False) -> Dict[str, Any]:
        """
        Ejecuta el descubrimiento automático de repositorios.
        
        Args:
            dry_run: Si es True, solo simula sin crear runners
        
        Returns:
            Resultado del descubrimiento
        """
        operation = "auto_discovery"
        log_operation_start(logger, operation, dry_run=dry_run)
        
        try:
            # Obtener repositorios que necesitan runners
            repositories = self.orchestration_service.get_repositories_needing_runners()
            
            if not repositories:
                result = {
                    "success": True,
                    "dry_run": dry_run,
                    "repositories_found": 0,
                    "runners_created": 0,
                    "message": "No se encontraron repositorios que necesiten runners"
                }
                
                log_operation_success(logger, operation, dry_run=dry_run, repositories_found=0)
                return result
            
            # Procesar cada repositorio
            total_created = 0
            processed_repos = []
            
            for repo in repositories:
                try:
                    repo_result = self._process_repository(repo, dry_run)
                    
                    if repo_result["success"]:
                        total_created += repo_result["runners_created"]
                        processed_repos.append(repo.full_name)
                    
                    # Si no es dry run, esperar un poco entre creaciones
                    if not dry_run and repo_result["runners_created"] > 0:
                        import time
                        time.sleep(2)  # Esperar entre creaciones
                
                except Exception as e:
                    logger.error(f"Error procesando repositorio {repo.full_name}: {e}")
                    continue
            
            result = {
                "success": True,
                "dry_run": dry_run,
                "repositories_found": len(repositories),
                "repositories_processed": len(processed_repos),
                "runners_created": total_created,
                "processed_repos": processed_repos,
                "message": f"Descubrimiento completado: {len(repositories)} repos, {total_created} runners creados"
            }
            
            log_operation_success(logger, operation, dry_run=dry_run, 
                                 repositories_found=len(repositories), 
                                 runners_created=total_created)
            return result
            
        except Exception as e:
            log_operation_error(logger, operation, e, dry_run=dry_run)
            raise OrchestrationError(f"Error en descubrimiento automático: {e}")
    
    def get_repository_needs(self) -> List[Dict[str, Any]]:
        """
        Obtiene repositorios que necesitan runners.
        
        Returns:
            Lista de repositorios con demanda
        """
        try:
            repositories = self.orchestration_service.get_repositories_needing_runners()
            
            repo_needs = []
            for repo in repositories:
                demand = self.orchestration_service.get_repository_runner_demand(repo.full_name)
                
                repo_needs.append({
                    "repository": repo.full_name,
                    "owner": repo.owner,
                    "active_workflows": repo.active_workflows,
                    "queued_jobs": repo.queued_jobs,
                    "runner_demand": demand,
                    "uses_self_hosted": repo.uses_self_hosted
                })
            
            # Ordenar por demanda (mayor primero)
            repo_needs.sort(key=lambda x: x["runner_demand"], reverse=True)
            
            return repo_needs
            
        except Exception as e:
            logger.error(f"Error obteniendo necesidades de repositorios: {e}")
            return []
    
    def _process_repository(self, repository, dry_run: bool = False) -> Dict[str, Any]:
        """
        Procesa un repositorio individual.
        
        Args:
            repository: Entidad Repository
            dry_run: Si es True, solo simula sin crear runners
        
        Returns:
            Resultado del procesamiento
        """
        try:
            # Calcular demanda
            demand = self.orchestration_service.get_repository_runner_demand(repository.full_name)
            current_runners = self.orchestration_service._count_runners_for_repo(repository.full_name)
            
            # Determinar cuántos runners crear
            runners_to_create = max(0, min(demand - current_runners, self.max_runners_per_repo))
            
            if runners_to_create == 0:
                return {
                    "success": True,
                    "repository": repository.full_name,
                    "runners_created": 0,
                    "message": f"No se necesitan runners (demanda: {demand}, actuales: {current_runners})"
                }
            
            if dry_run:
                return {
                    "success": True,
                    "repository": repository.full_name,
                    "runners_created": runners_to_create,
                    "dry_run": True,
                    "message": f"Se crearían {runners_to_create} runners (dry run)"
                }
            
            # Crear runners
            result = self.create_runner.execute(
                scope="repo",
                scope_name=repository.full_name,
                count=runners_to_create
            )
            
            successful = len([r for r in result if r["success"]])
            
            return {
                "success": True,
                "repository": repository.full_name,
                "runners_created": successful,
                "dry_run": False,
                "message": f"Creados {successful} runners para {repository.full_name}"
            }
            
        except Exception as e:
                logger.error(f"Error procesando repositorio {repository.full_name}: {e}")
                return {
                    "success": False,
                    "repository": repository.full_name,
                    "runners_created": 0,
                    "error": str(e),
                    "message": f"Error procesando {repository.full_name}: {e}"
                }
    
    def get_discovery_statistics(self) -> Dict[str, Any]:
        """
        Obtiene estadísticas de descubrimiento.
        
        Returns:
            Estadísticas del descubrimiento
        """
        try:
            repo_needs = self.get_repository_needs()
            
            total_demand = sum(repo["runner_demand"] for repo in repo_needs)
            
            return {
                "repositories_with_demand": len(repo_needs),
                "total_runner_demand": total_demand,
                "average_demand_per_repo": total_demand / len(repo_needs) if repo_needs else 0,
                "top_repositories": repo_needs[:5],
                "discovery_enabled": True
            }
            
        except Exception as e:
                logger.error(f"Error obteniendo estadísticas de descubrimiento: {e}")
                return {"error": str(e)}
