import { describe, expect, it } from "vitest";
import { parseDuration } from "./duration.js";

const DAY = 86_400_000;

describe("parseDuration", () => {
  it.each([
    ["1h30m", 5_400_000],
    ["1d", DAY],
    ["2h", 7_200_000],
    ["45s", 45_000],
    ["250ms", 250],
    ["5ms", 5],
    ["1m1ms", 60_001],
    ["1d2h3m4s5ms", DAY + 7_200_000 + 180_000 + 4_000 + 5],
    ["  1h30m \n", 5_400_000],
    ["0h30m", 1_800_000],
    ["001s", 1_000],
    ["30d", 30 * DAY],
    ["720h", 30 * DAY],
  ])("returns the total in milliseconds for %j", (text, expected) => {
    expect(parseDuration(text)).toBe(expected);
  });

  it.each(["", "   "])("throws that the input is empty for %j", (text) => {
    expect(() => parseDuration(text)).toThrow(new Error("Invalid duration: input is empty"));
  });

  it.each([
    "30m1h",
    "1h1h",
    "1h 30m",
    "1h,30m",
    "-1h",
    "+1h",
    "1.5h",
    "1x",
    "1w",
    "h",
    "10",
    "1H",
    "1h30",
    "1ms1s",
    "1s1m",
    "１h",
  ])("throws an invalid format error for %j", (text) => {
    expect(() => parseDuration(text)).toThrow(/^Invalid duration ".*": expected whole-number parts/);
  });

  it.each(["0s", "0d0h", "0ms"])("throws when the total is not greater than 0 for %j", (text) => {
    expect(() => parseDuration(text)).toThrow(`Invalid duration "${text}": total must be greater than 0`);
  });

  it.each(["30d1ms", "31d", "721h", "99999999999999999999999d"])(
    "throws when the total is over 30 days for %j",
    (text) => {
      expect(() => parseDuration(text)).toThrow(`Invalid duration "${text}": total must be at most 30 days`);
    },
  );
});
