package api_test

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"time"

	"example.com/orders/internal/api"
	"example.com/orders/internal/store"
)

type fixture struct {
	t       *testing.T
	now     time.Time
	handler http.Handler
}

func newFixture(t *testing.T) *fixture {
	t.Helper()
	f := &fixture{t: t, now: time.Date(2026, 11, 20, 9, 0, 0, 0, time.UTC)}
	f.handler = api.NewServer(store.NewMemory(func() time.Time { return f.now }))
	return f
}

func (f *fixture) do(method, target, body string) *httptest.ResponseRecorder {
	f.t.Helper()
	request := httptest.NewRequest(method, target, strings.NewReader(body))
	recorder := httptest.NewRecorder()
	f.handler.ServeHTTP(recorder, request)
	return recorder
}

// place creates an order one minute after the previous one.
func (f *fixture) place(customer string) map[string]any {
	f.t.Helper()
	f.now = f.now.Add(time.Minute)
	response := f.do(http.MethodPost, "/orders", `{"customer":"`+customer+`","items":[{"sku":"MUG-01","quantity":2,"unit_price_cents":1200}]}`)
	if response.Code != http.StatusCreated {
		f.t.Fatalf("create order: status %d: %s", response.Code, response.Body)
	}
	return decode(f.t, response)
}

func decode(t *testing.T, response *httptest.ResponseRecorder) map[string]any {
	t.Helper()
	var body map[string]any
	if err := json.Unmarshal(response.Body.Bytes(), &body); err != nil {
		t.Fatalf("decode %q: %v", response.Body, err)
	}
	return body
}

func listedIDs(t *testing.T, response *httptest.ResponseRecorder) []string {
	t.Helper()
	orders, ok := decode(t, response)["orders"].([]any)
	if !ok {
		t.Fatalf("no orders array in %s", response.Body)
	}
	ids := make([]string, 0, len(orders))
	for _, o := range orders {
		ids = append(ids, o.(map[string]any)["id"].(string))
	}
	return ids
}

func errorCode(t *testing.T, response *httptest.ResponseRecorder) string {
	t.Helper()
	body, ok := decode(t, response)["error"].(map[string]any)
	if !ok {
		t.Fatalf("no error object in %s", response.Body)
	}
	return body["code"].(string)
}

func TestCreateOrderReturnsTheStoredOrder(t *testing.T) {
	f := newFixture(t)
	created := f.place("ada")
	if created["id"] != "ord_000001" || created["status"] != "pending" || created["total_cents"] != 2400.0 {
		t.Fatalf("unexpected order %v", created)
	}
	if created["created_at"] != "2026-11-20T09:01:00Z" {
		t.Fatalf("created_at = %v", created["created_at"])
	}
}

func TestCreateOrderSetsLocation(t *testing.T) {
	f := newFixture(t)
	response := f.do(http.MethodPost, "/orders", `{"customer":"ada","items":[{"sku":"A","quantity":1,"unit_price_cents":5}]}`)
	if got := response.Header().Get("Location"); got != "/orders/ord_000001" {
		t.Fatalf("Location = %q", got)
	}
}

func TestCreateOrderRejectsBadInput(t *testing.T) {
	cases := map[string]struct {
		body   string
		status int
		code   string
	}{
		"not json":      {`{`, http.StatusBadRequest, "invalid_body"},
		"unknown field": {`{"customer":"ada","items":[],"coupon":"X"}`, http.StatusBadRequest, "invalid_body"},
		"trailing data": {`{"customer":"ada","items":[]} {}`, http.StatusBadRequest, "invalid_body"},
		"no items":      {`{"customer":"ada","items":[]}`, http.StatusUnprocessableEntity, "invalid_order"},
		"no customer":   {`{"customer":" ","items":[{"sku":"A","quantity":1,"unit_price_cents":5}]}`, http.StatusUnprocessableEntity, "invalid_order"},
		"zero quantity": {`{"customer":"ada","items":[{"sku":"A","quantity":0,"unit_price_cents":5}]}`, http.StatusUnprocessableEntity, "invalid_order"},
	}
	for name, c := range cases {
		t.Run(name, func(t *testing.T) {
			response := newFixture(t).do(http.MethodPost, "/orders", c.body)
			if response.Code != c.status || errorCode(t, response) != c.code {
				t.Fatalf("got %d %s", response.Code, response.Body)
			}
		})
	}
}

func TestListOrdersNewestFirst(t *testing.T) {
	f := newFixture(t)
	f.place("ada")
	f.place("bob")
	f.place("ada")
	response := f.do(http.MethodGet, "/orders", "")
	if response.Code != http.StatusOK {
		t.Fatalf("status %d", response.Code)
	}
	got := strings.Join(listedIDs(t, response), ",")
	if got != "ord_000003,ord_000002,ord_000001" {
		t.Fatalf("ids = %s", got)
	}
}

func TestListOrdersEmptyIsAnEmptyArray(t *testing.T) {
	response := newFixture(t).do(http.MethodGet, "/orders", "")
	if strings.TrimSpace(response.Body.String()) != `{"orders":[]}` {
		t.Fatalf("body = %s", response.Body)
	}
}

func TestListOrdersFiltersByCustomerAndStatus(t *testing.T) {
	f := newFixture(t)
	f.place("ada")
	f.place("bob")
	f.place("ada")
	f.do(http.MethodPost, "/orders/ord_000003/status", `{"status":"paid"}`)
	if got := strings.Join(listedIDs(t, f.do(http.MethodGet, "/orders?customer=ada", "")), ","); got != "ord_000003,ord_000001" {
		t.Fatalf("customer filter: %s", got)
	}
	if got := strings.Join(listedIDs(t, f.do(http.MethodGet, "/orders?customer=ada&status=pending", "")), ","); got != "ord_000001" {
		t.Fatalf("customer and status filter: %s", got)
	}
}

func TestListOrdersRejectsUnknownStatus(t *testing.T) {
	response := newFixture(t).do(http.MethodGet, "/orders?status=lost", "")
	if response.Code != http.StatusBadRequest || errorCode(t, response) != "invalid_status" {
		t.Fatalf("got %d %s", response.Code, response.Body)
	}
}

func nextCursor(t *testing.T, response *httptest.ResponseRecorder) (string, bool) {
	t.Helper()
	cursor, ok := decode(t, response)["next_cursor"].(string)
	return cursor, ok
}

func TestListOrdersPagesWithoutRepeatsOrGapsWhileOrdersArrive(t *testing.T) {
	f := newFixture(t)
	for range 5 {
		f.place("ada")
	}
	first := f.do(http.MethodGet, "/orders?limit=2", "")
	cursor, ok := nextCursor(t, first)
	if got := strings.Join(listedIDs(t, first), ","); got != "ord_000005,ord_000004" || !ok {
		t.Fatalf("first page %s cursor=%v", got, ok)
	}
	f.place("ada")
	second := f.do(http.MethodGet, "/orders?limit=2&cursor="+cursor, "")
	cursor, ok = nextCursor(t, second)
	if got := strings.Join(listedIDs(t, second), ","); got != "ord_000003,ord_000002" || !ok {
		t.Fatalf("second page %s cursor=%v", got, ok)
	}
	last := f.do(http.MethodGet, "/orders?limit=2&cursor="+cursor, "")
	_, ok = nextCursor(t, last)
	if got := strings.Join(listedIDs(t, last), ","); got != "ord_000001" || ok {
		t.Fatalf("last page %s cursor=%v", got, ok)
	}
}

func TestListOrdersPagesCombineWithFilters(t *testing.T) {
	f := newFixture(t)
	f.place("ada")
	f.place("bob")
	f.place("ada")
	f.place("ada")
	first := f.do(http.MethodGet, "/orders?customer=ada&limit=2", "")
	cursor, _ := nextCursor(t, first)
	second := f.do(http.MethodGet, "/orders?customer=ada&limit=2&cursor="+cursor, "")
	if got := strings.Join(listedIDs(t, second), ","); got != "ord_000001" {
		t.Fatalf("second page %s", got)
	}
}

func TestListOrdersDefaultLimitIs50(t *testing.T) {
	f := newFixture(t)
	for range 51 {
		f.place("ada")
	}
	response := f.do(http.MethodGet, "/orders", "")
	if _, ok := nextCursor(t, response); len(listedIDs(t, response)) != 50 || !ok {
		t.Fatal("expected 50 orders and a next_cursor")
	}
}

func TestListOrdersRejectsBadLimit(t *testing.T) {
	for _, limit := range []string{"0", "201", "-1", "abc", "", "1.5"} {
		t.Run("limit="+limit, func(t *testing.T) {
			response := newFixture(t).do(http.MethodGet, "/orders?limit="+limit, "")
			if response.Code != http.StatusBadRequest || errorCode(t, response) != "invalid_limit" {
				t.Fatalf("got %d %s", response.Code, response.Body)
			}
		})
	}
}

func TestListOrdersAcceptsLimitBounds(t *testing.T) {
	for _, limit := range []string{"1", "200"} {
		if response := newFixture(t).do(http.MethodGet, "/orders?limit="+limit, ""); response.Code != http.StatusOK {
			t.Fatalf("limit %s: status %d", limit, response.Code)
		}
	}
}

func TestListOrdersRejectsForeignCursors(t *testing.T) {
	cursors := map[string]string{
		"empty":         "",
		"not base64":    "!!!",
		"no separator":  "MTIz",
		"bad timestamp": "eHl6fG9yZF8wMDAwMDE",
		"no id":         "MTIzfA",
		"not canonical": "MTIzfG9yZF8wMDAwMDE=",
		"padded zeros":  "MDAxfG9yZF8wMDAwMDE",
	}
	for name, cursor := range cursors {
		t.Run(name, func(t *testing.T) {
			response := newFixture(t).do(http.MethodGet, "/orders?cursor="+cursor, "")
			if response.Code != http.StatusBadRequest || errorCode(t, response) != "invalid_cursor" {
				t.Fatalf("got %d %s", response.Code, response.Body)
			}
		})
	}
}

func TestGetOrder(t *testing.T) {
	f := newFixture(t)
	f.place("ada")
	if response := f.do(http.MethodGet, "/orders/ord_000001", ""); response.Code != http.StatusOK || decode(t, response)["customer"] != "ada" {
		t.Fatalf("got %d %s", response.Code, response.Body)
	}
	if response := f.do(http.MethodGet, "/orders/ord_999999", ""); response.Code != http.StatusNotFound || errorCode(t, response) != "not_found" {
		t.Fatalf("got %d %s", response.Code, response.Body)
	}
}

func TestChangeStatusFollowsTheLifeCycle(t *testing.T) {
	f := newFixture(t)
	f.place("ada")
	if response := f.do(http.MethodPost, "/orders/ord_000001/status", `{"status":"shipped"}`); response.Code != http.StatusConflict {
		t.Fatalf("pending to shipped: %d", response.Code)
	}
	if response := f.do(http.MethodPost, "/orders/ord_000001/status", `{"status":"paid"}`); response.Code != http.StatusOK || decode(t, response)["status"] != "paid" {
		t.Fatalf("pending to paid: %d %s", response.Code, response.Body)
	}
	if response := f.do(http.MethodPost, "/orders/ord_000001/status", `{"status":"lost"}`); response.Code != http.StatusBadRequest {
		t.Fatalf("unknown status: %d", response.Code)
	}
	if response := f.do(http.MethodPost, "/orders/ord_000404/status", `{"status":"paid"}`); response.Code != http.StatusNotFound {
		t.Fatalf("unknown order: %d", response.Code)
	}
}

func TestHealthz(t *testing.T) {
	if response := newFixture(t).do(http.MethodGet, "/healthz", ""); response.Code != http.StatusOK {
		t.Fatalf("status %d", response.Code)
	}
}
