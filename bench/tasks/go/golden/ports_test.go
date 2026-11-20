package ports

import (
	"slices"
	"strconv"
	"strings"
	"testing"
)

func TestParsePortsValid(t *testing.T) {
	tests := []struct {
		name string
		spec string
		want []int
	}{
		{"single port", "80", []int{80}},
		{"list and range", "80,443,8000-8003", []int{80, 443, 8000, 8001, 8002, 8003}},
		{"unsorted input is sorted", "443,80", []int{80, 443}},
		{"duplicates removed", "80,80,79-81", []int{79, 80, 81}},
		{"spaces around items", " 80 , 8-9 ", []int{8, 9, 80}},
		{"range of one", "5-5", []int{5}},
		{"lowest and highest ports", "1,65535", []int{1, 65535}},
		{"leading zeros", "0080", []int{80}},
		{"exactly 1000 ports", "1-1000", rangeOf(1, 1000)},
		{"overlapping ranges within limit", "1-1000,500-600", rangeOf(1, 1000)},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got, err := ParsePorts(tt.spec)

			if err != nil {
				t.Fatalf("ParsePorts(%q) error: %v", tt.spec, err)
			}
			if !slices.Equal(got, tt.want) {
				t.Errorf("ParsePorts(%q) = %v, want %v", tt.spec, got, tt.want)
			}
		})
	}
}

func TestParsePortsInvalid(t *testing.T) {
	tests := []struct {
		name string
		spec string
	}{
		{"empty spec", ""},
		{"blank spec", "   "},
		{"empty item", "80,,443"},
		{"trailing comma", "80,"},
		{"letters", "http"},
		{"plus sign", "+80"},
		{"negative", "-80"},
		{"tab", "80,\t443"},
		{"space inside range", "80 - 90"},
		{"space inside number", "8 0"},
		{"zero", "0"},
		{"above max", "65536"},
		{"overflowing digits", "99999999999999999999"},
		{"reversed range", "90-80"},
		{"range with missing end", "80-"},
		{"range with three parts", "1-2-3"},
		{"range end above max", "65530-65536"},
		{"more than 1000 ports", "1-1001"},
		{"more than 1000 across items", "1-600,601-1001"},
		{"huge range", "1-65535"},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got, err := ParsePorts(tt.spec)

			if err == nil {
				t.Errorf("ParsePorts(%q) = %v, want error", tt.spec, got)
			}
		})
	}
}

func TestParsePortsErrorMessages(t *testing.T) {
	tests := []struct {
		spec string
		want string
	}{
		{"", "port list is empty"},
		{"80,,1", "empty item in port list"},
		{"abc", `invalid port "abc": digits only`},
		{"70000", `invalid port "70000": must be between 1 and 65535`},
		{"9-8", `invalid range "9-8": start is greater than end`},
		{"1-2-3", `invalid item "1-2-3": too many '-'`},
		{"1-1001", "port list covers more than 1000 ports"},
	}
	for _, tt := range tests {
		t.Run(tt.spec, func(t *testing.T) {
			_, err := ParsePorts(tt.spec)

			if err == nil || err.Error() != tt.want {
				t.Errorf("ParsePorts(%q) error = %v, want %q", tt.spec, err, tt.want)
			}
		})
	}
}

func rangeOf(start, end int) []int {
	result := make([]int, 0, end-start+1)
	for port := start; port <= end; port++ {
		result = append(result, port)
	}
	return result
}

func FuzzParsePorts(f *testing.F) {
	f.Add("80,443,8000-8010")
	f.Fuzz(func(t *testing.T, spec string) {
		got, err := ParsePorts(spec)
		if err != nil {
			return
		}
		if len(got) == 0 || len(got) > maxCount || !slices.IsSorted(got) {
			t.Fatalf("ParsePorts(%q) = %v violates the contract", spec, got)
		}
		if strings.ContainsAny(spec, "abcdefghijklmnopqrstuvwxyz") {
			t.Fatalf("ParsePorts(%q) accepted letters: %s", spec, strconv.Itoa(len(got)))
		}
	})
}
