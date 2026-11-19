// Package store keeps orders. Memory is the only implementation until the Postgres migration lands.
package store

import (
	"errors"
	"fmt"
	"sort"
	"sync"
	"time"

	"example.com/orders/internal/order"
)

// ErrNotFound is returned when no order has the requested ID.
var ErrNotFound = errors.New("order not found")

// Clock returns the current time; tests pass a fixed one.
type Clock func() time.Time

// Filter narrows a listing. Zero fields match everything.
type Filter struct {
	Status   order.Status
	Customer string
}

func (f Filter) matches(o order.Order) bool {
	return (f.Status == "" || o.Status == f.Status) && (f.Customer == "" || o.Customer == f.Customer)
}

// Memory is a concurrency-safe in-memory order store.
type Memory struct {
	mu     sync.RWMutex
	clock  Clock
	nextID int
	orders map[string]order.Order
}

// NewMemory returns an empty store that stamps orders with clock.
func NewMemory(clock Clock) *Memory {
	return &Memory{clock: clock, orders: make(map[string]order.Order)}
}

// Create validates and stores a new pending order.
func (m *Memory) Create(n order.New) (order.Order, error) {
	if err := n.Validate(); err != nil {
		return order.Order{}, err
	}
	m.mu.Lock()
	defer m.mu.Unlock()
	m.nextID++
	now := m.clock().UTC()
	created := order.Order{
		ID:        fmt.Sprintf("ord_%06d", m.nextID),
		Customer:  n.Customer,
		Status:    order.StatusPending,
		Items:     append([]order.Item(nil), n.Items...),
		CreatedAt: now,
		UpdatedAt: now,
	}
	m.orders[created.ID] = created
	return created, nil
}

// Get returns the order with the given ID.
func (m *Memory) Get(id string) (order.Order, error) {
	m.mu.RLock()
	defer m.mu.RUnlock()
	found, ok := m.orders[id]
	if !ok {
		return order.Order{}, fmt.Errorf("%w: %s", ErrNotFound, id)
	}
	return found, nil
}

// List returns the orders matching filter, newest first.
func (m *Memory) List(filter Filter) []order.Order {
	m.mu.RLock()
	defer m.mu.RUnlock()
	matching := make([]order.Order, 0, len(m.orders))
	for _, o := range m.orders {
		if filter.matches(o) {
			matching = append(matching, o)
		}
	}
	sort.Slice(matching, func(i, j int) bool {
		return matching[i].CreatedAt.After(matching[j].CreatedAt)
	})
	return matching
}

// UpdateStatus moves an order to a new status when its life cycle allows it.
func (m *Memory) UpdateStatus(id string, next order.Status) (order.Order, error) {
	m.mu.Lock()
	defer m.mu.Unlock()
	found, ok := m.orders[id]
	if !ok {
		return order.Order{}, fmt.Errorf("%w: %s", ErrNotFound, id)
	}
	if !found.CanMoveTo(next) {
		return order.Order{}, fmt.Errorf("%w: %s to %s", order.ErrTransition, found.Status, next)
	}
	found.Status = next
	found.UpdatedAt = m.clock().UTC()
	m.orders[id] = found
	return found, nil
}
