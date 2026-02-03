/*
 * This script should be run after a period of time (180s), because the server may need some time to prepare.
 */
package main

import (
	"fmt"
	"log"
	"net/http"
	"os"
	"time"
)

func main() {
	// Configuración
	port := os.Getenv("PORT")
	if port == "" {
		port = "8080"
	}
	
	// Esperar a que el servicio esté listo
	time.Sleep(5 * time.Second)
	
	// Realizar health check
	url := fmt.Sprintf("http://localhost:%s/healthz", port)
	
	client := &http.Client{
		Timeout: 10 * time.Second,
	}
	
	resp, err := client.Get(url)
	if err != nil {
		log.Fatalf("Health check failed: %v", err)
	}
	defer resp.Body.Close()
	
	if resp.StatusCode != http.StatusOK {
		log.Fatalf("Health check failed with status: %d", resp.StatusCode)
	}
	
	log.Printf("Health Check OK [Res Code: %d]\n", resp.StatusCode)
	os.Exit(0)
}
