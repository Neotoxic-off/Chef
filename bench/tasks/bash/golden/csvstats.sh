#!/usr/bin/env bash
# Print count, sum, min, max and mean of one numeric column of a CSV file whose first line is the header.
# Usage: csvstats.sh COLUMN [FILE]   (standard input when FILE is missing or -)
set -euo pipefail

readonly PROGRAM="csvstats"

if [[ $# -lt 1 || $# -gt 2 ]]; then
  echo "usage: csvstats.sh COLUMN [FILE]" >&2
  exit 2
fi

column=$1
file=${2:--}
if [[ ${file} != - && ! (-f ${file} && -r ${file}) ]]; then
  echo "${PROGRAM}: cannot read ${file}" >&2
  exit 1
fi

# awk reads a last line without a newline, which a `while read` loop would drop.
awk -F, -v column="${column}" -v program="${PROGRAM}" '
  function fail(message) {
    printf "%s: %s\n", program, message > "/dev/stderr"
    failed = 1
    exit 1
  }
  { sub(/\r$/, "") }
  NR == 1 {
    for (field = 1; field <= NF; field++) {
      if ($field == column) {
        position = field
      }
    }
    if (!position) {
      fail("no column named " column)
    }
    next
  }
  {
    value = $position
    if (value == "") {
      next
    }
    if (value !~ /^-?[0-9]+(\.[0-9]+)?$/) {
      fail("line " NR ": not a number: " value)
    }
    value += 0
    if (count == 0 || value < min) {
      min = value
    }
    if (count == 0 || value > max) {
      max = value
    }
    sum += value
    count++
  }
  END {
    if (failed) {
      exit 1
    }
    if (NR == 0) {
      fail("no header line")
    }
    if (count == 0) {
      fail("no value in column " column)
    }
    printf "count=%d sum=%.2f min=%.2f max=%.2f mean=%.2f\n", count, sum, min, max, sum / count
  }
' "${file}"
