package store

import (
	"errors"
	"sync"
	"testing"
	"time"

	"example.com/orders/internal/order"
)

var start = time.Date(2026, 11, 20, 9, 0, 0, 0, time.UTC)

func newOrder(customer string) order.New {
	return order.New{Customer: customer, Items: []order.Item{{SKU: "MUG-01", Quantity: 1, UnitPriceCents: 1200}}}
}

func TestCreateAssignsSequentialIDsAndPendingStatus(t *testing.T) {
	m := NewMemory(func() time.Time { return start })
	first, _ := m.Create(newOrder("ada"))
	second, _ := m.Create(newOrder("bob"))
	if first.ID != "ord_000001" || second.ID != "ord_000002" {
		t.Fatalf("ids %s %s", first.ID, second.ID)
	}
	if first.Status != order.StatusPending || !first.CreatedAt.Equal(start) {
		t.Fatalf("unexpected %+v", first)
	}
}

func TestCreateRejectsInvalidOrders(t *testing.T) {
	m := NewMemory(time.Now)
	if _, err := m.Create(order.New{Customer: "ada"}); !errors.Is(err, order.ErrInvalid) {
		t.Fatalf("err = %v", err)
	}
	if len(m.List(Filter{})) != 0 {
		t.Fatal("invalid order was stored")
	}
}

func TestCreateCopiesItems(t *testing.T) {
	m := NewMemory(time.Now)
	n := newOrder("ada")
	created, _ := m.Create(n)
	n.Items[0].Quantity = 99
	stored, _ := m.Get(created.ID)
	if stored.Items[0].Quantity != 1 {
		t.Fatal("store shares the caller's items slice")
	}
}

func TestGetUnknownOrder(t *testing.T) {
	if _, err := NewMemory(time.Now).Get("ord_000042"); !errors.Is(err, ErrNotFound) {
		t.Fatalf("err = %v", err)
	}
}

func TestListFiltersAndSortsNewestFirst(t *testing.T) {
	now := start
	m := NewMemory(func() time.Time { now = now.Add(time.Second); return now })
	_, _ = m.Create(newOrder("ada"))
	_, _ = m.Create(newOrder("bob"))
	_, _ = m.Create(newOrder("ada"))
	listed := m.List(Filter{Customer: "ada"})
	if len(listed) != 2 || listed[0].ID != "ord_000003" || listed[1].ID != "ord_000001" {
		t.Fatalf("listed %+v", listed)
	}
}

func TestUpdateStatus(t *testing.T) {
	m := NewMemory(func() time.Time { return start })
	created, _ := m.Create(newOrder("ada"))
	if _, err := m.UpdateStatus(created.ID, order.StatusShipped); !errors.Is(err, order.ErrTransition) {
		t.Fatalf("pending to shipped: %v", err)
	}
	paid, err := m.UpdateStatus(created.ID, order.StatusPaid)
	if err != nil || paid.Status != order.StatusPaid {
		t.Fatalf("pending to paid: %+v %v", paid, err)
	}
	if _, err := m.UpdateStatus("ord_000404", order.StatusPaid); !errors.Is(err, ErrNotFound) {
		t.Fatalf("unknown: %v", err)
	}
}

func TestConcurrentCreatesGetDistinctIDs(t *testing.T) {
	m := NewMemory(time.Now)
	var wg sync.WaitGroup
	for range 50 {
		wg.Go(func() { _, _ = m.Create(newOrder("ada")) })
	}
	wg.Wait()
	if got := len(m.List(Filter{})); got != 50 {
		t.Fatalf("stored %d orders", got)
	}
}
