package api

import (
	"encoding/base64"
	"errors"
	"strconv"
	"strings"
	"time"

	"example.com/orders/internal/store"
)

const (
	defaultLimit = 50
	maxLimit     = 200
)

var (
	errInvalidLimit  = errors.New("limit must be an integer from 1 to 200")
	errInvalidCursor = errors.New("cursor is not one issued by this API")
)

// parseLimit returns defaultLimit when the parameter is absent.
func parseLimit(text string, present bool) (int, error) {
	if !present {
		return defaultLimit, nil
	}
	limit, err := strconv.Atoi(text)
	if err != nil || limit < 1 || limit > maxLimit {
		return 0, errInvalidLimit
	}
	return limit, nil
}

// encodeCursor makes an opaque cursor of the form base64url("<created_at unix nanoseconds>|<order id>").
func encodeCursor(position store.Position) string {
	text := strconv.FormatInt(position.CreatedAt.UnixNano(), 10) + "|" + position.ID
	return base64.RawURLEncoding.EncodeToString([]byte(text))
}

func decodeCursor(cursor string) (store.Position, error) {
	raw, err := base64.RawURLEncoding.Strict().DecodeString(cursor)
	if err != nil {
		return store.Position{}, errInvalidCursor
	}
	nanos, id, found := strings.Cut(string(raw), "|")
	created, err := strconv.ParseInt(nanos, 10, 64)
	if !found || id == "" || err != nil {
		return store.Position{}, errInvalidCursor
	}
	position := store.Position{CreatedAt: time.Unix(0, created).UTC(), ID: id}
	if encodeCursor(position) != cursor {
		return store.Position{}, errInvalidCursor
	}
	return position, nil
}
