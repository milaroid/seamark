package api

import (
	"database/sql"
	"encoding/json"
	"net/http"
)

// SearchHandler returns products in the category supplied by the caller.
func SearchHandler(db *sql.DB) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		category := r.URL.Query().Get("category")
		rows, err := db.Query("SELECT id, name, price FROM products WHERE category = ? ORDER BY name", category)
		if err != nil {
			http.Error(w, "query failed", http.StatusInternalServerError)
			return
		}
		defer rows.Close()
		var names []string
		for rows.Next() {
			var id int
			var name string
			var price float64
			if err := rows.Scan(&id, &name, &price); err != nil {
				http.Error(w, "scan failed", http.StatusInternalServerError)
				return
			}
			names = append(names, name)
		}
		json.NewEncoder(w).Encode(names)
	}
}
