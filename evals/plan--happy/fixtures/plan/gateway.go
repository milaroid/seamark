package main

import (
	"log"
	"net/http"
)

func main() {
	mux := http.NewServeMux()
	mux.HandleFunc("/api/orders", ordersHandler)
	mux.HandleFunc("/api/products", productsHandler)
	handler := WithAuth(WithLogging(mux))
	log.Fatal(http.ListenAndServe(":8080", handler))
}

func ordersHandler(w http.ResponseWriter, r *http.Request) {
	w.WriteHeader(http.StatusOK)
}

func productsHandler(w http.ResponseWriter, r *http.Request) {
	w.WriteHeader(http.StatusOK)
}
