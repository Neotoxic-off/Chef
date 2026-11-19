# Coding rules

These are the core rules of chef (https://github.com/Neotoxic-off/chef), for any coding agent that reads `AGENTS.md` or `CLAUDE.md`. Copy this file to your project root.

- Priorities, in order: clarity, simplicity, maintainability, security. Security is never traded away.
- Not sure what the user wants, which option they prefer, or whether an action is allowed: ask before acting. Never fill a gap with a guess.
- Verify before relying on a fact: read the code, config, docs or tool output. If you cannot verify it, say so.
- Do what was asked, nothing more, and never write outside the project folder. A good idea nobody asked for gets one line at the end, not code. The task's stated contract (exception types, exit codes, formats, behavior to keep) wins over every convention.
- Pick the boring, obvious solution; if it is hard to follow, rewrite it simpler first. Small focused functions, early returns, names that say what a thing is, no magic numbers or strings. Match the file's style. No dead code, debug prints or commented-out blocks.
- Comment only a non-obvious why, a workaround or an external constraint. Doc comments only on a library's public API used by other projects.
- Prevent errors instead of catching them (check first, `TryParse`, `dict.get`, `Result`). Catch only where no non-throwing API exists and around files, network and other shared resources, with the narrowest exception, handled where you can act. Never catch-all, never swallow an error, never use exceptions for control flow, never invent data to signal one. Error messages say what failed and where.
- Every change ships with tests: unit tests for each behavior, branch and error path, integration tests at each boundary (database, HTTP, filesystem). Deterministic: inject clock, random and network. Fix a bug by first writing a test that reproduces it.
- Every project has a formatter, a linter and a type checker (strict in a new project), configured in the repo and run in CI when the project has one. Declare every tool you configure as a dev dependency. Warnings are errors: fix the cause. Never hide one (no suppression comments, no `|| true`, no skipped tests, no lowered thresholds).
- Type every function signature and public field. Inside functions follow the language's idiom (`:=` in Go, `var` in C#/Java and `let` in Rust when the type is obvious on the right side). No `any` or untyped escape hatches.
- Pin what you depend on: lockfiles, image digests, action SHAs. No new dependency without asking; the lint, format, test and coverage tools are pre-approved.
- Before saying done, the code builds and the formatter, linter, type checker and tests pass, run in one call. Say plainly what you did not run.
