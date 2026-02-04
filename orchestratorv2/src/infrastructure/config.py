"""
Configuración y validación centralizada de la aplicación.

Rol: Cargar variables de entorno, validar y proveer defaults.
Centraliza toda la configuración del sistema en un solo lugar.
Provee configuración tipada y validada para toda la aplicación.

Depende de: variables de entorno, pydantic para validación.
"""

# Config: Clase principal de configuración
# Métodos: load_from_env(), validate(), get_setting()
# Incluye timeouts, URLs de API, configuración Docker
