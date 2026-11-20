package main

import (
	"fmt"
	"io"
	"os"

	ports "example.com/ports"
)

func main() {
	os.Exit(run(os.Args[1:], os.Stdout, os.Stderr))
}

func run(args []string, stdout, stderr io.Writer) int {
	if len(args) != 1 {
		fmt.Fprintln(stderr, "usage: portlist <ports>, e.g. 80,443,8000-8010")
		return 1
	}
	list, err := ports.ParsePorts(args[0])
	if err != nil {
		fmt.Fprintln(stderr, err)
		return 1
	}
	for _, port := range list {
		fmt.Fprintln(stdout, port)
	}
	return 0
}
