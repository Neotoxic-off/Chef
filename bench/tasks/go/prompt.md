Create a Go command-line tool in this folder that reads a port list such as `80,443,8000-8010` from its first argument and prints the ports it covers, one per line, or prints why the list is invalid and exits with code 1.

Make this folder a Go module and put the logic in a file `ports.go` at the module root, in package `ports`, exposing `func ParsePorts(spec string) ([]int, error)`. The spec is a comma-separated list of items; each item is a port or an inclusive range `start-end`, and spaces around an item are allowed. A port is written with digits only and lies between 1 and 65535; a range needs start lower than or equal to end. The result is sorted in ascending order without duplicates and holds at most 1000 ports. An empty spec, an empty item, any other character, or more than 1000 ports returns an error.

Work autonomously: nobody will answer questions.
