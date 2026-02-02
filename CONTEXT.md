# Plataforma de Runners Efímeros de GitHub Actions

## Concepto General

Sistema para crear y destruir runners self-hosted de GitHub Actions de forma efímera usando contenedores Docker.

## Principios Fundamentales

### Efimeridad
- Todo runner es efímero: crear → usar → destruir
- Ciclo de vida determinado y controlado
- No persistencia de estado entre ejecuciones

### Seguridad
- Ningún token sensible persiste dentro de un runner
- Los registration tokens de GitHub son temporales y se generan vía API
- No usar SSH para registro de runners
- No reutilizar tokens

### Separación de Responsabilidades
- Orquestador: genera registration tokens y crea contenedores
- Runner: consume tokens, ejecuta jobs, se destruye
- Una instancia de runner = un solo scope (repo u org)

## Arquitectura

### Componentes
1. **Orquestador**: Servicio central que gestiona el ciclo de vida
2. **Runner**: Contenedor efímero que ejecuta jobs
3. **API Gateway**: Punto de entrada para solicitudes

### Flujo Típico
1. Solicitud de runner → Orquestador
2. Orquestador genera token via GitHub API
3. Orquestador crea contenedor Docker con token
4. Runner se registra con GitHub
5. Runner ejecuta job(s)
6. Runner se destruye automáticamente

### Características de Diseño
- Repo-first: puede desplegarse sin infraestructura previa
- Docker como único mecanismo de ejecución
- Diseño minimalista y determinista
- Fallos explícitos y tempranos

## Restricciones de Implementación

- No duplicar lógica entre proyectos
- No introducir componentes no definidos
- No añadir monitoreo, métricas ni pruebas
- Uso explícito de variables de entorno
- Sin valores hardcodeados sensibles
