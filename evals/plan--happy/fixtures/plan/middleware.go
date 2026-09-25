package main

import (
	"log"
	"net/http"
	"time"
)

// WithAuth rejects requests whose X-API-Key header is absent; it does not verify the key against any store.
func WithAuth(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		key := r.Header.Get("X-API-Key")
		if key == "" {
			http.Error(w, "missing API key", http.StatusUnauthorized)
			return
		}
		next.ServeHTTP(w, r)
	})
}

// WithLogging records method, path, and latency for every request.
func WithLogging(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		start := time.Now()
		next.ServeHTTP(w, r)
		log.Printf("%s %s %s", r.Method, r.URL.Path, time.Since(start))
	})
}
