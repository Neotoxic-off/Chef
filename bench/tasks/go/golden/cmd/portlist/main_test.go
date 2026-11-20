package main

import (
	"bytes"
	"testing"
)

func TestRun(t *testing.T) {
	tests := []struct {
		name       string
		args       []string
		wantCode   int
		wantStdout string
		wantStderr bool
	}{
		{"valid list prints one port per line", []string{"80, 8-9"}, 0, "8\n9\n80\n", false},
		{"invalid list exits 1", []string{"0"}, 1, "", true},
		{"missing argument exits 1", nil, 1, "", true},
		{"extra argument exits 1", []string{"80", "81"}, 1, "", true},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			var stdout, stderr bytes.Buffer

			code := run(tt.args, &stdout, &stderr)

			if code != tt.wantCode {
				t.Errorf("exit code = %d, want %d", code, tt.wantCode)
			}
			if stdout.String() != tt.wantStdout {
				t.Errorf("stdout = %q, want %q", stdout.String(), tt.wantStdout)
			}
			if (stderr.Len() > 0) != tt.wantStderr {
				t.Errorf("stderr = %q, want output: %v", stderr.String(), tt.wantStderr)
			}
		})
	}
}
