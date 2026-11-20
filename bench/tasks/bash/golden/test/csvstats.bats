#!/usr/bin/env bats

bats_require_minimum_version 1.5.0

setup() {
  SCRIPT="$BATS_TEST_DIRNAME/../csvstats.sh"
  cd "$BATS_TEST_TMPDIR" || exit 1
}

@test "statistics of a column, CRLF and a missing last newline included" {
  printf 'item,price\r\na,1.5\r\nb,\r\nc,2.5' >prices.csv
  run --separate-stderr bash "$SCRIPT" price prices.csv
  [ "$status" -eq 0 ]
  [ "$output" = "count=2 sum=4.00 min=1.50 max=2.50 mean=2.00" ]
}

@test "standard input" {
  run --separate-stderr bash -c 'printf "n\n-1\n3\n" | bash "$0" n' "$SCRIPT"
  [ "$status" -eq 0 ]
  [ "$output" = "count=2 sum=2.00 min=-1.00 max=3.00 mean=1.00" ]
}

@test "usage error exits 2" {
  run --separate-stderr bash "$SCRIPT"
  [ "$status" -eq 2 ]
  [[ "$stderr" == "usage: "* ]]
}

@test "a value that is not a number exits 1 with its line" {
  printf 'n\n1\n1e3\n' >bad.csv
  run --separate-stderr bash "$SCRIPT" n bad.csv
  [ "$status" -eq 1 ]
  [ -z "$output" ]
  [ "$stderr" = "csvstats: line 3: not a number: 1e3" ]
}
