import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    coverage: {
      provider: "v8",
      include: ["src/**/*.ts"],
      // cli.ts only wires process.argv, stdout and the exit code to the tested run()
      exclude: ["src/cli.ts", "src/**/*.test.ts"],
      thresholds: { lines: 90, branches: 90, functions: 90, statements: 90 },
    },
  },
});
