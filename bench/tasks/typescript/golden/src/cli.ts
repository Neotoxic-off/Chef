#!/usr/bin/env node
import { run } from "./run.js";

const { output, exitCode } = run(process.argv.slice(2));
(exitCode === 0 ? process.stdout : process.stderr).write(`${output}\n`);
process.exitCode = exitCode;
