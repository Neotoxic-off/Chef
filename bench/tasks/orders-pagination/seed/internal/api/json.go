package api

import (
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"log/slog"
	"net/http"
	"time"

	"example.com/orders/internal/order"
)

const maxBodyBytes = 1 << 20

type itemJSON struct {
	SKU            string `json:"sku"`
	Quantity       int    `json:"quantity"`
	UnitPriceCents int64  `json:"unit_price_cents"`
}

type orderJSON struct {
	ID         string     `json:"id"`
	Customer   string     `json:"customer"`
	Status     string     `json:"status"`
	Items      []itemJSON `json:"items"`
	TotalCents int64      `json:"total_cents"`
	CreatedAt  string     `json:"created_at"`
	UpdatedAt  string     `json:"updated_at"`
}

type orderListJSON struct {
	Orders []orderJSON `json:"orders"`
}

type newOrderJSON struct {
	Customer string     `json:"customer"`
	Items    []itemJSON `json:"items"`
}

type statusChangeJSON struct {
	Status string `json:"status"`
}

type errorJSON struct {
	Error errorBodyJSON `json:"error"`
}

type errorBodyJSON struct {
	Code    string `json:"code"`
	Message string `json:"message"`
}

func toJSON(o order.Order) orderJSON {
	items := make([]itemJSON, 0, len(o.Items))
	for _, item := range o.Items {
		items = append(items, itemJSON{SKU: item.SKU, Quantity: item.Quantity, UnitPriceCents: item.UnitPriceCents})
	}
	return orderJSON{
		ID:         o.ID,
		Customer:   o.Customer,
		Status:     string(o.Status),
		Items:      items,
		TotalCents: o.TotalCents(),
		CreatedAt:  o.CreatedAt.Format(time.RFC3339Nano),
		UpdatedAt:  o.UpdatedAt.Format(time.RFC3339Nano),
	}
}

func (n newOrderJSON) toNew() order.New {
	items := make([]order.Item, 0, len(n.Items))
	for _, item := range n.Items {
		items = append(items, order.Item{SKU: item.SKU, Quantity: item.Quantity, UnitPriceCents: item.UnitPriceCents})
	}
	return order.New{Customer: n.Customer, Items: items}
}

// decodeBody reads one JSON object and rejects unknown fields and trailing data.
func decodeBody(w http.ResponseWriter, r *http.Request, into any) error {
	decoder := json.NewDecoder(http.MaxBytesReader(w, r.Body, maxBodyBytes))
	decoder.DisallowUnknownFields()
	if err := decoder.Decode(into); err != nil {
		return fmt.Errorf("invalid JSON body: %w", err)
	}
	if !errors.Is(decoder.Decode(&struct{}{}), io.EOF) {
		return errors.New("invalid JSON body: trailing data")
	}
	return nil
}

func writeJSON(w http.ResponseWriter, status int, body any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	if err := json.NewEncoder(w).Encode(body); err != nil {
		slog.Error("write response", "error", err)
	}
}

func writeError(w http.ResponseWriter, status int, code, message string) {
	writeJSON(w, status, errorJSON{Error: errorBodyJSON{Code: code, Message: message}})
}
