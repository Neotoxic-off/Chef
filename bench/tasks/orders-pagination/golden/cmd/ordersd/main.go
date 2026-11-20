// Command ordersd serves the orders API.
package main

import (
	"errors"
	"flag"
	"log/slog"
	"net/http"
	"os"
	"time"

	"example.com/orders/internal/api"
	"example.com/orders/internal/store"
)

const readHeaderTimeout = 5 * time.Second

func main() {
	address := flag.String("addr", ":8080", "listen address")
	flag.Parse()
	server := &http.Server{
		Addr:              *address,
		Handler:           api.NewServer(store.NewMemory(time.Now)),
		ReadHeaderTimeout: readHeaderTimeout,
	}
	slog.Info("listening", "addr", *address)
	if err := server.ListenAndServe(); err != nil && !errors.Is(err, http.ErrServerClosed) {
		slog.Error("server stopped", "error", err)
		os.Exit(1)
	}
}
