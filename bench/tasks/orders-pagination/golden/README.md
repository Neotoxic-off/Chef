# orders

The orders service: places orders, tracks their status, lists them for the back office and the mobile app.

```
go run ./cmd/ordersd -addr :8080
```

| Route | |
|---|---|
| `GET /orders?status=&customer=&limit=&cursor=` | orders, newest first (ties: highest ID first); `limit` 1-200, default 50; pass `next_cursor` back as `cursor` for the next page, absent on the last page |
| `POST /orders` | place an order |
| `GET /orders/{id}` | one order |
| `POST /orders/{id}/status` | move an order to `paid`, `shipped` or `cancelled` |

Errors are always `{"error": {"code": "...", "message": "..."}}` with a stable, snake_case `code`.

Layout: `internal/order` holds the model and its rules, `internal/store` the storage, `internal/api`
the HTTP layer. The store takes a clock so tests control time.

## Development

```
gofmt -l . && go vet ./... && go test ./...
```
