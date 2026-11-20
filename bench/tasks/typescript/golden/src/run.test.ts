import { describe, expect, it } from "vitest";
import { run } from "./run.js";

describe("run", () => {
  it("prints the total and exits 0 for a valid duration", () => {
    expect(run(["1h30m"])).toEqual({ output: "5400000", exitCode: 0 });
  });

  it("prints the reason and exits 1 for an invalid duration", () => {
    expect(run(["30m1h"])).toEqual({
      output: expect.stringContaining('Invalid duration "30m1h"') as string,
      exitCode: 1,
    });
  });

  it("prints usage and exits 1 without an argument", () => {
    expect(run([]).exitCode).toBe(1);
    expect(run([]).output).toContain("Usage:");
  });

  it("prints usage and exits 1 with more than one argument", () => {
    expect(run(["1h", "30m"]).exitCode).toBe(1);
  });
});
