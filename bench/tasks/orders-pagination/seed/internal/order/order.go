// Package order holds the order model and its business rules, free of storage and HTTP concerns.
package order

import (
	"errors"
	"fmt"
	"strings"
	"time"
)

// Status is where an order is in its life cycle.
type Status string

const (
	StatusPending   Status = "pending"
	StatusPaid      Status = "paid"
	StatusShipped   Status = "shipped"
	StatusCancelled Status = "cancelled"
)

const maxItems = 100

// ErrInvalid wraps every validation failure, so callers can map it to a client error.
var ErrInvalid = errors.New("invalid order")

// ErrTransition is returned when a status change is not allowed.
var ErrTransition = errors.New("status change not allowed")

var transitions = map[Status][]Status{
	StatusPending: {StatusPaid, StatusCancelled},
	StatusPaid:    {StatusShipped, StatusCancelled},
}

// Item is one line of an order.
type Item struct {
	SKU            string
	Quantity       int
	UnitPriceCents int64
}

// Order is an order as stored.
type Order struct {
	ID        string
	Customer  string
	Status    Status
	Items     []Item
	CreatedAt time.Time
	UpdatedAt time.Time
}

// New is what a client sends to place an order.
type New struct {
	Customer string
	Items    []Item
}

// ParseStatus accepts the lowercase status names used by the API.
func ParseStatus(text string) (Status, error) {
	switch status := Status(text); status {
	case StatusPending, StatusPaid, StatusShipped, StatusCancelled:
		return status, nil
	default:
		return "", fmt.Errorf("%w: unknown status %q", ErrInvalid, text)
	}
}

// Validate checks a new order before it is stored.
func (n New) Validate() error {
	if strings.TrimSpace(n.Customer) == "" {
		return fmt.Errorf("%w: customer is required", ErrInvalid)
	}
	if len(n.Items) == 0 {
		return fmt.Errorf("%w: at least one item is required", ErrInvalid)
	}
	if len(n.Items) > maxItems {
		return fmt.Errorf("%w: at most %d items", ErrInvalid, maxItems)
	}
	for i, item := range n.Items {
		if strings.TrimSpace(item.SKU) == "" {
			return fmt.Errorf("%w: item %d: sku is required", ErrInvalid, i)
		}
		if item.Quantity < 1 {
			return fmt.Errorf("%w: item %d: quantity must be at least 1", ErrInvalid, i)
		}
		if item.UnitPriceCents < 0 {
			return fmt.Errorf("%w: item %d: unit price must not be negative", ErrInvalid, i)
		}
	}
	return nil
}

// TotalCents is the sum of every line.
func (o Order) TotalCents() int64 {
	var total int64
	for _, item := range o.Items {
		total += int64(item.Quantity) * item.UnitPriceCents
	}
	return total
}

// CanMoveTo reports whether the order may go from its current status to next.
func (o Order) CanMoveTo(next Status) bool {
	for _, allowed := range transitions[o.Status] {
		if allowed == next {
			return true
		}
	}
	return false
}
