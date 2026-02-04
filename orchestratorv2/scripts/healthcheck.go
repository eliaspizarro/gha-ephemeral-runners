/*
 * Health Check nativo para OrchestratorV2
 * 
 * Este script debe ejecutarse después de un período de tiempo (5s),
 * porque el servidor puede necesitar tiempo para prepararse.
 * 
 * Similar al healthcheck.go del orchestrator original pero adaptado
 * para la nueva arquitectura con FastAPI y endpoints actualizados.
 * 
 * Uso: ./healthcheck.go (se compila y ejecuta en el contenedor)
 * Variables de entorno:
 *   - ORCHESTRATOR_HOST: Host del servicio (default: localhost)
 *   - ORCHESTRATOR_PORT: Puerto del servicio (default: 8000)
 *   - HEALTH_CHECK_TIMEOUT: Timeout en segundos (default: 10)
 *   - HEALTH_CHECK_WAIT_TIME: Tiempo de espera inicial (default: 5)
 */

package main

import (
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"os"
	"strconv"
	"time"
)

// HealthResponse representa la respuesta del endpoint de health
type HealthResponse struct {
	Status       string                 `json:"status"`
	Message      string                 `json:"message"`
	Uptime       int                    `json:"uptime_seconds"`
	Version      string                 `json:"version"`
	Environment  string                 `json:"environment"`
	Monitoring   *bool                  `json:"monitoring_active,omitempty"`
	Stats        map[string]interface{} `json:"stats,omitempty"`
	Config       map[string]interface{} `json:"config,omitempty"`
}

func main() {
	// Configuración desde variables de entorno
	host := getEnv("ORCHESTRATOR_HOST", "localhost")
	port := getEnv("ORCHESTRATOR_PORT", "8000")
	timeout := getEnvInt("HEALTH_CHECK_TIMEOUT", 10)
	waitTime := getEnvInt("HEALTH_CHECK_WAIT_TIME", 5)

	// Esperar a que el servicio esté listo
	log.Printf("Esperando %d segundos para que el servicio esté listo...", waitTime)
	time.Sleep(time.Duration(waitTime) * time.Second)

	// Construir URL del health check
	url := fmt.Sprintf("http://%s:%s/api/system/health", host, port)
	log.Printf("Verificando salud en: %s", url)

	// Configurar cliente HTTP con timeout
	client := &http.Client{
		Timeout: time.Duration(timeout) * time.Second,
	}

	// Realizar petición con parámetros para verificación detallada
	req, err := http.NewRequest("GET", url, nil)
	if err != nil {
		log.Fatalf("Error creando request: %v", err)
	}

	// Agregar parámetros para verificación completa
	q := req.URL.Query()
	q.Add("detailed", "true")
	q.Add("include_stats", "true")
	q.Add("include_config", "true")
	req.URL.RawQuery = q.Encode()

	// Ejecutar request
	startTime := time.Now()
	resp, err := client.Do(req)
	if err != nil {
		log.Fatalf("Health check failed: %v", err)
	}
	defer resp.Body.Close()

	responseTime := time.Since(startTime)

	// Verificar status code
	if resp.StatusCode != http.StatusOK {
		log.Fatalf("Health check failed con status: %d", resp.StatusCode)
	}

	// Parsear respuesta JSON
	var healthResp HealthResponse
	if err := json.NewDecoder(resp.Body).Decode(&healthResp); err != nil {
		log.Fatalf("Error parseando respuesta JSON: %v", err)
	}

	// Verificaciones específicas del servicio
	checks := map[string]bool{
		"status_healthy":    healthResp.Status == "healthy",
		"uptime_sufficient": healthResp.Uptime >= 5,
	}

	// Verificar monitoreo si está disponible
	if healthResp.Monitoring != nil {
		checks["monitoring_configured"] = *healthResp.Monitoring
	}

	// Verificar estadísticas si están disponibles
	if healthResp.Stats != nil {
		checks["stats_available"] = true
	}

	// Verificar configuración si está disponible
	if healthResp.Config != nil {
		checks["config_available"] = true
	}

	// Evaluar todas las verificaciones
	allPassed := true
	for name, passed := range checks {
		if !passed {
			log.Printf("❌ Verificación fallida: %s", name)
			allPassed = false
		} else {
			log.Printf("✅ Verificación exitosa: %s", name)
		}
	}

	if allPassed {
		log.Printf("✅ Health Check OK [Status: %d, Response: %v, Uptime: %ds, Version: %s]", 
			resp.StatusCode, responseTime.Round(time.Millisecond), healthResp.Uptime, healthResp.Version)
		log.Printf("🎉 Todas las verificaciones pasaron: %v", checks)
	} else {
		log.Printf("⚠️ Health Check parcial [Status: %d, Response: %v]", resp.StatusCode, responseTime.Round(time.Millisecond))
		log.Printf("Verificaciones: %v", checks)
		// No fallar el health check si algunas verificaciones no críticas fallan
		// Solo fallar si el status no es healthy
		if healthResp.Status != "healthy" {
			log.Fatalf("❌ Status del servicio no es healthy: %s", healthResp.Status)
		}
	}

	log.Printf("🚀 OrchestratorV2 está listo para recibir tráfico")
	os.Exit(0)
}

// Funciones helper para manejo de variables de entorno

func getEnv(key, defaultValue string) string {
	if value := os.Getenv(key); value != "" {
		return value
	}
	return defaultValue
}

func getEnvInt(key string, defaultValue int) int {
	if value := os.Getenv(key); value != "" {
		if intValue, err := strconv.Atoi(value); err == nil {
			return intValue
		}
		log.Printf("Valor inválido para %s: %s, usando default: %d", key, value, defaultValue)
	}
	return defaultValue
}
