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
	if stored, _ := m.List(Filter{}, Page{}); len(stored) != 0 {
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
	listed, more := m.List(Filter{Customer: "ada"}, Page{})
	if len(listed) != 2 || listed[0].ID != "ord_000003" || listed[1].ID != "ord_000001" || more {
		t.Fatalf("listed %+v", listed)
	}
}

func TestListSameInstantHighestIDFirstAcrossPages(t *testing.T) {
	m := NewMemory(func() time.Time { return start })
	for range 5 {
		_, _ = m.Create(newOrder("ada"))
	}
	first, more := m.List(Filter{}, Page{Limit: 2})
	if !more || first[0].ID != "ord_000005" || first[1].ID != "ord_000004" {
		t.Fatalf("first page %+v more=%v", first, more)
	}
	_, _ = m.Create(newOrder("ada")) // same instant, sorts before the cursor
	after := PositionOf(first[1])
	second, more := m.List(Filter{}, Page{After: &after, Limit: 3})
	if more || len(second) != 3 || second[0].ID != "ord_000003" || second[2].ID != "ord_000001" {
		t.Fatalf("second page %+v more=%v", second, more)
	}
}

func TestListLimitEqualToRemainingHasNoMore(t *testing.T) {
	m := NewMemory(func() time.Time { return start })
	_, _ = m.Create(newOrder("ada"))
	_, _ = m.Create(newOrder("ada"))
	listed, more := m.List(Filter{}, Page{Limit: 2})
	if len(listed) != 2 || more {
		t.Fatalf("listed %d more=%v", len(listed), more)
	}
}

func TestListOrdersLongerIDsAsHigher(t *testing.T) {
	older := Position{CreatedAt: start, ID: "ord_999999"}
	newer := Position{CreatedAt: start, ID: "ord_1000000"}
	if !listedBefore(newer, older) || listedBefore(older, newer) {
		t.Fatal("ord_1000000 must be listed before ord_999999")
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
	if stored, _ := m.List(Filter{}, Page{}); len(stored) != 50 {
		t.Fatalf("stored %d orders", len(stored))
	}
}
