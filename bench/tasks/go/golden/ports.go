package ports

import (
	"errors"
	"fmt"
	"slices"
	"strconv"
	"strings"
)

const (
	minPort  = 1
	maxPort  = 65535
	maxCount = 1000
)

// ParsePorts expands a spec such as "80,443,8000-8010" into a sorted list of
// unique ports.
func ParsePorts(spec string) ([]int, error) {
	if strings.TrimSpace(spec) == "" {
		return nil, errors.New("port list is empty")
	}

	seen := make(map[int]struct{})
	for _, item := range strings.Split(spec, ",") {
		start, end, err := parseItem(strings.Trim(item, " "))
		if err != nil {
			return nil, err
		}
		// Checked before the loop so a huge range never allocates.
		if end-start+1 > maxCount {
			return nil, tooManyPorts()
		}
		for port := start; port <= end; port++ {
			seen[port] = struct{}{}
		}
		if len(seen) > maxCount {
			return nil, tooManyPorts()
		}
	}

	result := make([]int, 0, len(seen))
	for port := range seen {
		result = append(result, port)
	}
	slices.Sort(result)
	return result, nil
}

func tooManyPorts() error {
	return fmt.Errorf("port list covers more than %d ports", maxCount)
}

// parseItem returns the inclusive bounds of a single port or range item.
func parseItem(item string) (int, int, error) {
	if item == "" {
		return 0, 0, errors.New("empty item in port list")
	}
	bounds := strings.Split(item, "-")
	switch len(bounds) {
	case 1:
		port, err := parsePort(bounds[0])
		return port, port, err
	case 2:
		return parseRange(item, bounds[0], bounds[1])
	default:
		return 0, 0, fmt.Errorf("invalid item %q: too many '-'", item)
	}
}

func parseRange(item, first, last string) (int, int, error) {
	start, err := parsePort(first)
	if err != nil {
		return 0, 0, err
	}
	end, err := parsePort(last)
	if err != nil {
		return 0, 0, err
	}
	if start > end {
		return 0, 0, fmt.Errorf("invalid range %q: start is greater than end", item)
	}
	return start, end, nil
}

func parsePort(text string) (int, error) {
	if text == "" || strings.Trim(text, "0123456789") != "" {
		return 0, fmt.Errorf("invalid port %q: digits only", text)
	}
	port, err := strconv.Atoi(text)
	if err != nil || port < minPort || port > maxPort {
		return 0, fmt.Errorf("invalid port %q: must be between %d and %d", text, minPort, maxPort)
	}
	return port, nil
}
