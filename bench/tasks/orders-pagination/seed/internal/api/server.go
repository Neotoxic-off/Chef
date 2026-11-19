// Package api serves the orders HTTP API.
package api

import (
	"errors"
	"net/http"

	"example.com/orders/internal/order"
	"example.com/orders/internal/store"
)

// Store is what the API needs from the order store.
type Store interface {
	Create(n order.New) (order.Order, error)
	Get(id string) (order.Order, error)
	List(filter store.Filter) []order.Order
	UpdateStatus(id string, next order.Status) (order.Order, error)
}

type server struct {
	store Store
}

// NewServer returns the HTTP handler of the orders API.
func NewServer(s Store) http.Handler {
	srv := &server{store: s}
	mux := http.NewServeMux()
	mux.HandleFunc("GET /orders", srv.listOrders)
	mux.HandleFunc("POST /orders", srv.createOrder)
	mux.HandleFunc("GET /orders/{id}", srv.getOrder)
	mux.HandleFunc("POST /orders/{id}/status", srv.changeStatus)
	mux.HandleFunc("GET /healthz", func(w http.ResponseWriter, _ *http.Request) {
		writeJSON(w, http.StatusOK, map[string]string{"status": "ok"})
	})
	return mux
}

func (s *server) listOrders(w http.ResponseWriter, r *http.Request) {
	query := r.URL.Query()
	filter := store.Filter{Customer: query.Get("customer")}
	if text := query.Get("status"); text != "" {
		status, err := order.ParseStatus(text)
		if err != nil {
			writeError(w, http.StatusBadRequest, "invalid_status", err.Error())
			return
		}
		filter.Status = status
	}
	orders := s.store.List(filter)
	body := orderListJSON{Orders: make([]orderJSON, 0, len(orders))}
	for _, o := range orders {
		body.Orders = append(body.Orders, toJSON(o))
	}
	writeJSON(w, http.StatusOK, body)
}

func (s *server) createOrder(w http.ResponseWriter, r *http.Request) {
	var payload newOrderJSON
	if err := decodeBody(w, r, &payload); err != nil {
		writeError(w, http.StatusBadRequest, "invalid_body", err.Error())
		return
	}
	created, err := s.store.Create(payload.toNew())
	if errors.Is(err, order.ErrInvalid) {
		writeError(w, http.StatusUnprocessableEntity, "invalid_order", err.Error())
		return
	}
	if err != nil {
		writeError(w, http.StatusInternalServerError, "internal", "could not create the order")
		return
	}
	w.Header().Set("Location", "/orders/"+created.ID)
	writeJSON(w, http.StatusCreated, toJSON(created))
}

func (s *server) getOrder(w http.ResponseWriter, r *http.Request) {
	found, err := s.store.Get(r.PathValue("id"))
	if errors.Is(err, store.ErrNotFound) {
		writeError(w, http.StatusNotFound, "not_found", err.Error())
		return
	}
	if err != nil {
		writeError(w, http.StatusInternalServerError, "internal", "could not read the order")
		return
	}
	writeJSON(w, http.StatusOK, toJSON(found))
}

func (s *server) changeStatus(w http.ResponseWriter, r *http.Request) {
	var payload statusChangeJSON
	if err := decodeBody(w, r, &payload); err != nil {
		writeError(w, http.StatusBadRequest, "invalid_body", err.Error())
		return
	}
	next, err := order.ParseStatus(payload.Status)
	if err != nil {
		writeError(w, http.StatusBadRequest, "invalid_status", err.Error())
		return
	}
	updated, err := s.store.UpdateStatus(r.PathValue("id"), next)
	switch {
	case errors.Is(err, store.ErrNotFound):
		writeError(w, http.StatusNotFound, "not_found", err.Error())
	case errors.Is(err, order.ErrTransition):
		writeError(w, http.StatusConflict, "invalid_transition", err.Error())
	case err != nil:
		writeError(w, http.StatusInternalServerError, "internal", "could not update the order")
	default:
		writeJSON(w, http.StatusOK, toJSON(updated))
	}
}
