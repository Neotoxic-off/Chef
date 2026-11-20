#!/usr/bin/env bats
# Hidden test of the bash task, run from the workspace root next to csvstats.sh.

bats_require_minimum_version 1.5.0

setup() {
  SCRIPT="$BATS_TEST_DIRNAME/csvstats.sh"
  cd "$BATS_TEST_TMPDIR" || exit 1
  printf 'region,amount,units\nnorth,10,1\nsouth,30.5,2\neast,-4.5,3\n' >sales.csv
}

csvstats() {
  run --separate-stderr bash "$SCRIPT" "$@"
}

@test "prints the statistics of a column of a file" {
  csvstats amount sales.csv
  [ "$status" -eq 0 ]
  [ "$output" = "count=3 sum=36.00 min=-4.50 max=30.50 mean=12.00" ]
  [ -z "$stderr" ]
}

@test "reads standard input without FILE or with -" {
  run --separate-stderr bash -c 'bash "$0" units <sales.csv' "$SCRIPT"
  [ "$status" -eq 0 ]
  [ "$output" = "count=3 sum=6.00 min=1.00 max=3.00 mean=2.00" ]

  run --separate-stderr bash -c 'bash "$0" units - <sales.csv' "$SCRIPT"
  [ "$status" -eq 0 ]
  [ "$output" = "count=3 sum=6.00 min=1.00 max=3.00 mean=2.00" ]
}

@test "the first column works too" {
  printf 'score,name\n7,a\n9,b\n' >first.csv
  csvstats score first.csv
  [ "$status" -eq 0 ]
  [ "$output" = "count=2 sum=16.00 min=7.00 max=9.00 mean=8.00" ]
}

@test "skips empty cells" {
  printf 'name,score,team\na,4,x\nb,,y\nc,8,z\n' >gaps.csv
  csvstats score gaps.csv
  [ "$status" -eq 0 ]
  [ "$output" = "count=2 sum=12.00 min=4.00 max=8.00 mean=6.00" ]
}

@test "reads Windows line endings like Unix ones" {
  printf 'region,amount\r\nnorth,2\r\nsouth,4\r\n' >crlf.csv
  csvstats amount crlf.csv
  [ "$status" -eq 0 ]
  [ "$output" = "count=2 sum=6.00 min=2.00 max=4.00 mean=3.00" ]
}

@test "counts a last line without a newline" {
  printf 'region,amount\nnorth,2\nsouth,4' >unterminated.csv
  csvstats amount unterminated.csv
  [ "$status" -eq 0 ]
  [ "$output" = "count=2 sum=6.00 min=2.00 max=4.00 mean=3.00" ]
}

@test "a wrong number of arguments prints the usage and exits 2" {
  csvstats
  [ "$status" -eq 2 ]
  [ -z "$output" ]
  [[ "$stderr" == *"usage: csvstats.sh COLUMN [FILE]"* ]]

  csvstats amount sales.csv extra
  [ "$status" -eq 2 ]
  [ -z "$output" ]
  [[ "$stderr" == *"usage: csvstats.sh COLUMN [FILE]"* ]]
}

@test "a file that cannot be read exits 1" {
  csvstats amount missing.csv
  [ "$status" -eq 1 ]
  [ -z "$output" ]
  [[ "$stderr" == "csvstats: "* ]]
}

@test "an unknown column exits 1" {
  csvstats price sales.csv
  [ "$status" -eq 1 ]
  [ -z "$output" ]
  [[ "$stderr" == "csvstats: "* ]]
}

@test "a value that is not a number exits 1 and names its line" {
  printf 'region,amount\nnorth,2\nsouth,lots\nwest,3\n' >bad.csv
  csvstats amount bad.csv
  [ "$status" -eq 1 ]
  [ -z "$output" ]
  [[ "$stderr" == "csvstats: "* ]]
  [[ "$stderr" == *"line 3"* ]]
}

@test "a column without any value exits 1" {
  printf 'region,amount\n' >header-only.csv
  csvstats amount header-only.csv
  [ "$status" -eq 1 ]
  [ -z "$output" ]
  [[ "$stderr" == "csvstats: "* ]]

  printf 'region,amount\nnorth,\n' >blank.csv
  csvstats amount blank.csv
  [ "$status" -eq 1 ]
  [ -z "$output" ]
}
