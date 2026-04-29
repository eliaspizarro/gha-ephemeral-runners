import logging
import requests
from typing import List, Dict
from src.services.tokens import TokenGenerator
from src.utils.helpers import format_log, setup_logger

logger = setup_logger(__name__)


class GitHubRunnerCleanup:
    """Maneja la limpieza de runners offline en GitHub API."""
    
    def __init__(self, github_runner_token: str):
        self.token_generator = TokenGenerator(github_runner_token)
    
    def get_all_runners_from_github(self, scope: str, scope_name: str) -> List[Dict]:
        """Obtiene todos los runners (online y offline) desde GitHub API."""
        try:
            if scope == "repo":
                url = f"{self.token_generator.api_base}/repos/{scope_name}/actions/runners"
            elif scope == "org":
                url = f"{self.token_generator.api_base}/orgs/{scope_name}/actions/runners"
            else:
                url = f"{self.token_generator.api_base}/user/actions/runners"
            
            response = requests.get(url, headers=self.token_generator.headers, timeout=30.0)
            
            if response.status_code == 200:
                data = response.json()
                return data.get("runners", [])
            else:
                logger.error(f"Error obteniendo runners de GitHub: {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"Error consultando GitHub API: {e}")
            return []
    
    def get_offline_runners(self, scope: str, scope_name: str) -> List[Dict]:
        """Filtra runners offline."""
        all_runners = self.get_all_runners_from_github(scope, scope_name)
        offline_runners = [runner for runner in all_runners if not runner.get("online", True)]
        
        logger.info(f"GitHub runners: {len(all_runners)} totales, {len(offline_runners)} offline")
        return offline_runners
    
    def unregister_runner_from_github(self, scope: str, scope_name: str, runner_id: int) -> bool:
        """Elimina un runner de GitHub API."""
        try:
            if scope == "repo":
                url = f"{self.token_generator.api_base}/repos/{scope_name}/actions/runners/{runner_id}"
            elif scope == "org":
                url = f"{self.token_generator.api_base}/orgs/{scope_name}/actions/runners/{runner_id}"
            else:
                url = f"{self.token_generator.api_base}/user/actions/runners/{runner_id}"
            
            response = requests.delete(url, headers=self.token_generator.headers, timeout=30.0)
            
            if response.status_code == 204:
                logger.info(f"Runner {runner_id} eliminado de GitHub")
                return True
            else:
                logger.error(f"Error eliminando runner {runner_id}: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Error eliminando runner {runner_id}: {e}")
            return False
    
    def cleanup_offline_runners(self, scope: str, scope_name: str, dry_run: bool = False) -> Dict[str, int]:
        """Elimina todos los runners offline de GitHub."""
        logger.info(format_log('CONFIG', f'Limpiando runners offline en GitHub: {scope}/{scope_name}'))
        
        offline_runners = self.get_offline_runners(scope, scope_name)
        
        if not offline_runners:
            logger.info("No hay runners offline para limpiar")
            return {"total": 0, "cleaned": 0, "failed": 0}
        
        if dry_run:
            logger.info(f"[DRY RUN] Se eliminarían {len(offline_runners)} runners offline:")
            for runner in offline_runners:
                logger.info(f"  - {runner['name']} (ID: {runner['id']}) - offline")
            return {"total": len(offline_runners), "cleaned": 0, "failed": 0}
        
        cleaned_count = 0
        failed_count = 0
        
        for runner in offline_runners:
            runner_id = runner["id"]
            runner_name = runner["name"]
            
            logger.info(f"Eliminando runner offline: {runner_name} (ID: {runner_id})")
            
            if self.unregister_runner_from_github(scope, scope_name, runner_id):
                cleaned_count += 1
            else:
                failed_count += 1
        
        logger.info(format_log('SUCCESS', f'Cleanup GitHub: {cleaned_count}/{len(offline_runners)} runners eliminados'))
        
        return {
            "total": len(offline_runners),
            "cleaned": cleaned_count,
            "failed": failed_count
        }
    
    def cleanup_all_offline_runners(self, dry_run: bool = False) -> Dict[str, Dict[str, int]]:
        """Limpia runners offline en todos los ámbitos (user, repos, orgs)."""
        results = {}
        
        # Limpiar runners de usuario
        user_result = self.cleanup_offline_runners("user", "", dry_run)
        if user_result["total"] > 0:
            results["user"] = user_result
        
        # TODO: Agregar limpieza por repositorio y organización si es necesario
        # Esto requeriría obtener la lista de repositorios y organizaciones
        
        return results
