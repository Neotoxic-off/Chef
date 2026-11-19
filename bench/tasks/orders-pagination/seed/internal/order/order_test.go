package order

import (
	"errors"
	"testing"
)

func TestParseStatus(t *testing.T) {
	for _, text := range []string{"pending", "paid", "shipped", "cancelled"} {
		if got, err := ParseStatus(text); err != nil || string(got) != text {
			t.Fatalf("ParseStatus(%q) = %q, %v", text, got, err)
		}
	}
	for _, text := range []string{"", "Paid", "lost"} {
		if _, err := ParseStatus(text); !errors.Is(err, ErrInvalid) {
			t.Fatalf("ParseStatus(%q) err = %v", text, err)
		}
	}
}

func TestValidate(t *testing.T) {
	valid := Item{SKU: "A", Quantity: 1, UnitPriceCents: 0}
	cases := map[string]New{
		"no customer":    {Customer: " ", Items: []Item{valid}},
		"no items":       {Customer: "ada"},
		"no sku":         {Customer: "ada", Items: []Item{{Quantity: 1}}},
		"zero quantity":  {Customer: "ada", Items: []Item{{SKU: "A"}}},
		"negative price": {Customer: "ada", Items: []Item{{SKU: "A", Quantity: 1, UnitPriceCents: -1}}},
		"too many items": {Customer: "ada", Items: make([]Item, maxItems+1)},
	}
	for name, n := range cases {
		if err := n.Validate(); !errors.Is(err, ErrInvalid) {
			t.Errorf("%s: err = %v", name, err)
		}
	}
	if err := (New{Customer: "ada", Items: []Item{valid}}).Validate(); err != nil {
		t.Fatalf("valid order: %v", err)
	}
}

func TestTotalCents(t *testing.T) {
	o := Order{Items: []Item{{SKU: "A", Quantity: 3, UnitPriceCents: 250}, {SKU: "B", Quantity: 1, UnitPriceCents: 99}}}
	if got := o.TotalCents(); got != 849 {
		t.Fatalf("total = %d", got)
	}
}

func TestCanMoveTo(t *testing.T) {
	pending := Order{Status: StatusPending}
	if !pending.CanMoveTo(StatusPaid) || !pending.CanMoveTo(StatusCancelled) || pending.CanMoveTo(StatusShipped) {
		t.Fatal("pending transitions")
	}
	if (Order{Status: StatusShipped}).CanMoveTo(StatusCancelled) {
		t.Fatal("shipped is final")
	}
}
