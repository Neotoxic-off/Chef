package ports

import (
	"slices"
	"testing"
)

func TestBenchHiddenParsePortsAcceptsValidSpecs(t *testing.T) {
	var cases map[string][]int = map[string][]int{
		"443, 80 ,8000-8002,80": {80, 443, 8000, 8001, 8002},
		"22":                    {22},
		"65535":                 {65535},
		"5-5":                   {5},
		" 1-3 , 2-4 ":           {1, 2, 3, 4},
	}
	for spec, expected := range cases {
		var actual []int
		var err error
		actual, err = ParsePorts(spec)
		if err != nil || !slices.Equal(actual, expected) {
			t.Errorf("ParsePorts(%q) = %v, %v; want %v, nil", spec, actual, err, expected)
		}
	}
}

func TestBenchHiddenParsePortsAcceptsThousandPorts(t *testing.T) {
	var actual []int
	var err error
	actual, err = ParsePorts("1-1000,500")
	if err != nil || len(actual) != 1000 {
		t.Errorf("ParsePorts(\"1-1000,500\") = %d ports, %v; want 1000 ports, nil", len(actual), err)
	}
}

func TestBenchHiddenParsePortsRejectsInvalidSpecs(t *testing.T) {
	var invalid []string = []string{
		"",
		" ",
		"0",
		"65536",
		"80,,443",
		"80,",
		",80",
		"10-5",
		"8o",
		"+80",
		"-80",
		"80-",
		"1-2-3",
		"80 443",
		"1-1001",
		"99999999999999999999",
	}
	for _, spec := range invalid {
		var err error
		_, err = ParsePorts(spec)
		if err == nil {
			t.Errorf("ParsePorts(%q) returned no error", spec)
		}
	}
}
