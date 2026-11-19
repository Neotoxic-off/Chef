import assert from "node:assert/strict";
import { test } from "node:test";

import { parseDuration } from "./src/duration.ts";

const SECOND: number = 1000;
const MINUTE: number = 60 * SECOND;
const HOUR: number = 60 * MINUTE;
const DAY: number = 24 * HOUR;

const VALID: ReadonlyArray<readonly [string, number]> = [
  ["1h30m", HOUR + 30 * MINUTE],
  ["500ms", 500],
  ["  2d ", 2 * DAY],
  ["1d2h3m4s5ms", DAY + 2 * HOUR + 3 * MINUTE + 4 * SECOND + 5],
  ["1m1ms", MINUTE + 1],
  ["0h5m", 5 * MINUTE],
  ["30d", 30 * DAY],
];

const INVALID: ReadonlyArray<string> = [
  "",
  "   ",
  "10",
  "1.5h",
  "-5m",
  "+5m",
  "30m1h",
  "1h1h",
  "1h 30m",
  "5x",
  "5mm",
  "h",
  "0s",
  "30d1ms",
  "31d",
];

for (const [text, expected] of VALID) {
  test(`parseDuration accepts ${JSON.stringify(text)}`, (): void => {
    assert.equal(parseDuration(text), expected);
  });
}

for (const text of INVALID) {
  test(`parseDuration rejects ${JSON.stringify(text)}`, (): void => {
    assert.throws((): number => parseDuration(text), Error);
  });
}
