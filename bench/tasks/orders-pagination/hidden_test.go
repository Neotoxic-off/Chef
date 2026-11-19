package api_test

import (
	"encoding/json"
	"fmt"
	"net/http"
	"net/http/httptest"
	"net/url"
	"slices"
	"strings"
	"testing"
	"time"

	"example.com/orders/internal/api"
	"example.com/orders/internal/store"
)

type benchService struct {
	t       *testing.T
	now     time.Time
	handler http.Handler
}

type benchPage struct {
	status int
	ids    []string
	cursor string
	code   string
}

func benchNewService(t *testing.T) *benchService {
	t.Helper()
	s := &benchService{t: t, now: time.Date(2026, 11, 20, 9, 0, 0, 0, time.UTC)}
	s.handler = api.NewServer(store.NewMemory(func() time.Time { return s.now }))
	return s
}

func (s *benchService) send(method, target, body string) *httptest.ResponseRecorder {
	s.t.Helper()
	recorder := httptest.NewRecorder()
	s.handler.ServeHTTP(recorder, httptest.NewRequest(method, target, strings.NewReader(body)))
	return recorder
}

// placeAt creates an order for customer stamped at the current clock, and returns its ID.
func (s *benchService) placeAt(customer string) string {
	s.t.Helper()
	response := s.send(http.MethodPost, "/orders", `{"customer":"`+customer+`","items":[{"sku":"A","quantity":1,"unit_price_cents":100}]}`)
	if response.Code != http.StatusCreated {
		s.t.Fatalf("create: %d %s", response.Code, response.Body)
	}
	var created struct {
		ID string `json:"id"`
	}
	if err := json.Unmarshal(response.Body.Bytes(), &created); err != nil {
		s.t.Fatal(err)
	}
	return created.ID
}

func (s *benchService) placeEachSecond(customer string, count int) []string {
	ids := make([]string, 0, count)
	for range count {
		s.now = s.now.Add(time.Second)
		ids = append(ids, s.placeAt(customer))
	}
	return ids
}

func (s *benchService) page(query url.Values) benchPage {
	s.t.Helper()
	response := s.send(http.MethodGet, "/orders?"+query.Encode(), "")
	var body struct {
		Orders []struct {
			ID string `json:"id"`
		} `json:"orders"`
		NextCursor *string `json:"next_cursor"`
		Error      struct {
			Code string `json:"code"`
		} `json:"error"`
	}
	if err := json.Unmarshal(response.Body.Bytes(), &body); err != nil {
		s.t.Fatalf("decode %q: %v", response.Body, err)
	}
	result := benchPage{status: response.Code, code: body.Error.Code}
	for _, o := range body.Orders {
		result.ids = append(result.ids, o.ID)
	}
	if body.NextCursor != nil {
		result.cursor = *body.NextCursor
	}
	return result
}

// all follows next_cursor from the first page to the last and returns every page's IDs.
func (s *benchService) all(query url.Values) [][]string {
	s.t.Helper()
	var pages [][]string
	for range 100 {
		p := s.page(query)
		if p.status != http.StatusOK {
			s.t.Fatalf("page %d: status %d code %q", len(pages)+1, p.status, p.code)
		}
		pages = append(pages, p.ids)
		if p.cursor == "" {
			return pages
		}
		query.Set("cursor", p.cursor)
	}
	s.t.Fatal("pagination never ends")
	return nil
}

func benchReversed(ids []string) []string {
	reversed := slices.Clone(ids)
	slices.Reverse(reversed)
	return reversed
}

func benchSizes(pages [][]string) []int {
	sizes := make([]int, 0, len(pages))
	for _, p := range pages {
		sizes = append(sizes, len(p))
	}
	return sizes
}

func TestBenchHiddenDefaultLimitIs50(t *testing.T) {
	s := benchNewService(t)
	ids := s.placeEachSecond("ada", 120)
	pages := s.all(url.Values{})
	if got := benchSizes(pages); !slices.Equal(got, []int{50, 50, 20}) {
		t.Fatalf("page sizes = %v", got)
	}
	if got := slices.Concat(pages...); !slices.Equal(got, benchReversed(ids)) {
		t.Fatalf("orders across pages = %v", got)
	}
}

func TestBenchHiddenSmallListHasNoCursor(t *testing.T) {
	s := benchNewService(t)
	s.placeEachSecond("ada", 3)
	p := s.page(url.Values{})
	if len(p.ids) != 3 || p.cursor != "" {
		t.Fatalf("got %d orders, cursor %q", len(p.ids), p.cursor)
	}
}

func TestBenchHiddenLastFullPageHasNoCursor(t *testing.T) {
	s := benchNewService(t)
	s.placeEachSecond("ada", 4)
	pages := s.all(url.Values{"limit": {"2"}})
	if got := benchSizes(pages); !slices.Equal(got, []int{2, 2}) {
		t.Fatalf("page sizes = %v", got)
	}
}

func TestBenchHiddenEmptyListStillAnArray(t *testing.T) {
	response := benchNewService(t).send(http.MethodGet, "/orders?limit=10", "")
	if !strings.Contains(response.Body.String(), `"orders":[]`) || strings.Contains(response.Body.String(), `"next_cursor":"`) {
		t.Fatalf("body = %s", response.Body)
	}
}

func TestBenchHiddenSameInstantOrdersComeHighestIDFirst(t *testing.T) {
	s := benchNewService(t)
	ids := make([]string, 0, 5)
	for range 5 {
		ids = append(ids, s.placeAt("ada"))
	}
	pages := s.all(url.Values{"limit": {"2"}})
	if got := benchSizes(pages); !slices.Equal(got, []int{2, 2, 1}) {
		t.Fatalf("page sizes = %v", got)
	}
	if got := slices.Concat(pages...); !slices.Equal(got, benchReversed(ids)) {
		t.Fatalf("orders = %v, want %v", got, benchReversed(ids))
	}
}

func TestBenchHiddenTiesAcrossAPageBoundary(t *testing.T) {
	s := benchNewService(t)
	var ids []string
	ids = append(ids, s.placeEachSecond("ada", 2)...)
	s.now = s.now.Add(time.Second)
	for range 4 {
		ids = append(ids, s.placeAt("ada"))
	}
	ids = append(ids, s.placeEachSecond("ada", 2)...)
	pages := s.all(url.Values{"limit": {"3"}})
	if got := slices.Concat(pages...); !slices.Equal(got, benchReversed(ids)) {
		t.Fatalf("orders = %v, want %v", got, benchReversed(ids))
	}
}

func TestBenchHiddenNewOrdersWhilePagingAreNotShownTwice(t *testing.T) {
	s := benchNewService(t)
	ids := s.placeEachSecond("ada", 6)
	first := s.page(url.Values{"customer": {"ada"}, "limit": {"2"}})
	s.placeEachSecond("ada", 3)
	rest := s.all(url.Values{"customer": {"ada"}, "limit": {"2"}, "cursor": {first.cursor}})
	if got := slices.Concat(append([][]string{first.ids}, rest...)...); !slices.Equal(got, benchReversed(ids)) {
		t.Fatalf("orders = %v, want %v", got, benchReversed(ids))
	}
}

func TestBenchHiddenNewOrdersAtTheSameInstantWhilePaging(t *testing.T) {
	s := benchNewService(t)
	ids := make([]string, 0, 4)
	for range 4 {
		ids = append(ids, s.placeAt("ada"))
	}
	first := s.page(url.Values{"limit": {"2"}})
	s.placeAt("ada")
	rest := s.all(url.Values{"limit": {"2"}, "cursor": {first.cursor}})
	if got := slices.Concat(append([][]string{first.ids}, rest...)...); !slices.Equal(got, benchReversed(ids)) {
		t.Fatalf("orders = %v, want %v", got, benchReversed(ids))
	}
}

func TestBenchHiddenFiltersCombineWithPagination(t *testing.T) {
	s := benchNewService(t)
	var adaPending []string
	for i := range 10 {
		s.now = s.now.Add(time.Second)
		customer := "ada"
		if i%3 == 0 {
			customer = "bob"
		}
		id := s.placeAt(customer)
		if customer == "ada" && i%2 == 0 {
			if response := s.send(http.MethodPost, "/orders/"+id+"/status", `{"status":"paid"}`); response.Code != http.StatusOK {
				t.Fatalf("pay %s: %d", id, response.Code)
			}
			continue
		}
		if customer == "ada" {
			adaPending = append(adaPending, id)
		}
	}
	pages := s.all(url.Values{"customer": {"ada"}, "status": {"pending"}, "limit": {"2"}})
	if got := slices.Concat(pages...); !slices.Equal(got, benchReversed(adaPending)) {
		t.Fatalf("orders = %v, want %v", got, benchReversed(adaPending))
	}
}

func TestBenchHiddenLimitCanChangeBetweenPages(t *testing.T) {
	s := benchNewService(t)
	ids := s.placeEachSecond("ada", 7)
	first := s.page(url.Values{"limit": {"2"}})
	second := s.page(url.Values{"limit": {"4"}, "cursor": {first.cursor}})
	if got := append(slices.Clone(first.ids), second.ids...); !slices.Equal(got, benchReversed(ids)[:6]) {
		t.Fatalf("orders = %v", got)
	}
}

func TestBenchHiddenLimitBounds(t *testing.T) {
	s := benchNewService(t)
	s.placeEachSecond("ada", 205)
	for _, limit := range []string{"1", "200"} {
		if p := s.page(url.Values{"limit": {limit}}); p.status != http.StatusOK || fmt.Sprint(len(p.ids)) != limit || p.cursor == "" {
			t.Fatalf("limit=%s: status %d, %d orders, cursor %q", limit, p.status, len(p.ids), p.cursor)
		}
	}
	for _, limit := range []string{"0", "-1", "201", "abc", "1.5", ""} {
		query := url.Values{"limit": {limit}}
		if limit == "" {
			query = url.Values{"limit": {""}, "status": {"pending"}}
		}
		p := s.page(query)
		if limit == "" {
			if p.status != http.StatusOK && (p.status != http.StatusBadRequest || p.code != "invalid_limit") {
				t.Fatalf("empty limit: status %d code %q", p.status, p.code)
			}
			continue
		}
		if p.status != http.StatusBadRequest || p.code != "invalid_limit" {
			t.Fatalf("limit=%q: status %d code %q", limit, p.status, p.code)
		}
	}
}

func TestBenchHiddenRejectsCursorsTheAPIDidNotIssue(t *testing.T) {
	s := benchNewService(t)
	s.placeEachSecond("ada", 5)
	if s.page(url.Values{"limit": {"2"}}).cursor == "" {
		t.Fatal("no cursor issued for a first page of 2 out of 5")
	}
	for _, cursor := range []string{"garbage", "%%%", "bm90LWEtY3Vyc29y", "{}"} {
		p := s.page(url.Values{"cursor": {cursor}})
		if p.status != http.StatusBadRequest || p.code != "invalid_cursor" {
			t.Fatalf("cursor %q: status %d code %q", cursor, p.status, p.code)
		}
	}
}

func TestBenchHiddenStatusFilterStillValidated(t *testing.T) {
	p := benchNewService(t).page(url.Values{"status": {"lost"}, "limit": {"10"}})
	if p.status != http.StatusBadRequest || p.code != "invalid_status" {
		t.Fatalf("status %d code %q", p.status, p.code)
	}
}
