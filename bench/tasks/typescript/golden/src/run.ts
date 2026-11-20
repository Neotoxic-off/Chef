import { parseDuration } from "./duration.js";

export interface RunResult {
  readonly output: string;
  readonly exitCode: number;
}

export function run(args: readonly string[]): RunResult {
  const [text, ...extra] = args;
  if (text === undefined || extra.length > 0) {
    return { output: "Usage: duration <text>, for example: duration 1h30m", exitCode: 1 };
  }
  try {
    return { output: String(parseDuration(text)), exitCode: 0 };
  } catch (error) {
    if (error instanceof Error) {
      return { output: error.message, exitCode: 1 };
    }
    throw error;
  }
}
