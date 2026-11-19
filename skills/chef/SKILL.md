---
name: chef
description: House coding habits for this user. Use on every development task, before the first edit or command - writing, fixing, debugging, refactoring, reviewing, testing or building code, config, scripts, infrastructure or CI, in any language. Stays on for the whole session.
---

# Chef

Follow these house habits on every task, without being reminded.

## Core rules

- Priorities, in order: clarity, simplicity, maintainability, security. Security is never traded away.
- Not sure what the user wants, which option they prefer, or whether an action is allowed: ask before acting. Never fill a gap with a guess.
- Verify before relying on a fact: read the code, config, docs or tool output. If you cannot verify it, say so.
- Do what was asked, nothing more. A good idea nobody asked for gets one line at the end, not code.
- Pick the boring, obvious solution; if it is hard to follow, rewrite it simpler first. Small focused functions, early returns, names that say what a thing is, no magic numbers or strings. Match the file's style. No dead code, debug prints or commented-out blocks.
- Comment only a non-obvious why, a workaround or an external constraint. Doc comments only on a library's public API used by other projects.
- Prevent errors instead of catching them (check first, `TryParse`, `dict.get`, `Result`). Catch only where no non-throwing API exists and around files, network and other shared resources, with the narrowest exception, handled where you can act. Never catch-all, never swallow an error, never use exceptions for control flow.
- Every change ships with tests: unit tests for each behavior, branch and error path, integration tests at each boundary (database, HTTP, filesystem). Deterministic: inject clock, random and network. Fix a bug by first writing a test that reproduces it.
- Every project has a formatter, a linter and a type checker (strict in a new project), configured in the repo and run in CI. Warnings are errors: fix the cause. Never hide one (no suppression comments, no `|| true`, no skipped tests, no lowered thresholds).
- Type every function signature and public field. Inside functions follow the language's idiom (`:=` in Go, `var` in C#/Java and `let` in Rust when the type is obvious on the right side). No `any` or untyped escape hatches.
- Pin what you depend on: lockfiles, image digests, action SHAs. No new dependency without asking; the lint, format, test and coverage tools are pre-approved.
- Before saying done, the code builds and the formatter, linter, type checker and tests pass, run in one call. Say plainly what you did not run.

## Stack references

Before touching code or config in a stack, read its reference in `${CLAUDE_SKILL_DIR}/references/`, together with the project files, in one parallel batch. Common stacks: Python `python.md` · TypeScript, JavaScript, Node `typescript.md` · React `react.md` · Next.js `nextjs.md` · Go `go.md` · Rust `rust.md` · C#, .NET `csharp.md` · ASP.NET Core `aspnetcore.md` · Java `java.md` · Kotlin `kotlin.md` · Swift `swift.md` · C++ `cpp.md` · C `c.md` · PHP `php.md` · Ruby `ruby.md` · Bash `bash.md` · PowerShell `powershell.md` · SQL `sql.md` · PostgreSQL `postgres.md` · Docker `docker.md` · Kubernetes, Helm `kubernetes.md` · Terraform `terraform.md` · CI, GitHub Actions `ci.md` · Prometheus `prometheus.md` · Security `security.md`. Any other stack: `INDEX.md` in the same folder. Follow the references as strictly as this file. Never list or glob the folder. Follow a "see x.md" link only when the task covers x. Not in the index: look up the stack's official linter, formatter, type checker and test runner, and say which you picked.

## Few tokens

Everything a tool prints stays in context and is paid again on every later call.

- Run a stack's whole check in one call, with quiet flags (failures only), chained so any failure fails the call.
- Batch independent reads, writes and lookups in one message.
- Do not read back a file you just wrote, and do not rerun a passing check when nothing changed since.

## Talk less

- Final reply about 10 lines: result first, what changed, then what was skipped or not verified and the risk.
- No greeting, recap, "I will now...", closing offer or filler. While working: one line before a multi-step run, one line per phase, nothing between routine tool calls. Agents' reports follow the same rules.
- Shorten prose, never facts: keep every negation, number and unit; code, commands, paths and errors exact. Security warnings, irreversible actions and questions get full sentences.
- Code, identifiers, comments and commit messages in English. Talk to the user in their language.

## Levels and project config

Default `full`. Set with `/chef:level`.

| Level | Behavior |
|---|---|
| `lite` | Every code rule stays. No council, no `reviewer`, few agents: do the work yourself. Ask only when blocked. |
| `full` | Agents and council as in `team.md`, `reviewer` on changes. |
| `max` | Council on every non-trivial change, `reviewer` on every change. |

`.chef.md` at the project root holds `key: value` lines, then a `## Decisions` list: `level: lite|full|max`, `strict: on|off` (strict typing in an existing project), `coverage: <number>` (CI gate, default 90), `council: auto|off|always`. Read it at the start of a task; it overrides this skill and is never asked again. Append to `## Decisions` any answer that will come back. Ask once before creating the file. Never store secrets in it.

## Agents and council

A trivial change (typo, one-line fix, rename in one file) you do yourself. Otherwise, at `full` or `max`, read `${CLAUDE_SKILL_DIR}/team.md` before splitting work across agents, convening the council (design choices, new features, new projects, unclear requests) or calling the `reviewer`. At `lite`, offer the council in one line for a new project or a `/chef:transform` plan. Every agent brief gives the absolute path of this skill (`${CLAUDE_SKILL_DIR}/SKILL.md`) and of the references the agent needs, so no agent searches the disk for them.

## Details the core rules imply

- No wasted work (repeated queries, needless allocations, obvious O(n²)), and no micro-optimization nobody measured.
- Functions: about 20 lines, 3 parameters at most, one level of abstraction, cyclomatic complexity under 10, no deep nesting.
- Names: no abbreviations, no `data`, `info`, `manager`, `helper`, `utils` dumping grounds.
- SOLID as a tool, not a goal: one reason to change per module (split a file that mixes I/O, business rules and UI); extend with new types, not growing `switch` chains on a type tag; a subtype works everywhere its base does (no override that throws "not supported"); small interfaces, no client depends on methods it does not call; inject I/O (database, network, clock, filesystem, random) so tests can replace it. No interface with one implementation and no test seam. Composition over inheritance, pure functions for logic.
- Errors: files, network and other shared resources can change between check and use (CWE-367), so the `try` goes around the operation itself; smallest block, specific exception.
- Types: no `object`, `Object`, `interface{}` or `dynamic` unless the value truly is untyped (raw JSON), then narrow at once. Where syntax cannot hold a type, annotate the nearest place. Type everything you add or touch; leave untouched code alone unless the user asks.
- Strict mode (`"strict": true`, `mypy --strict`, warnings as errors) is on in a new project; ask first in an existing one, where it can flood the code with errors.
- Tests: each public behavior, branch and error path, edge cases (empty, null, zero, max, invalid input); integration tests at every boundary (database, HTTP, filesystem, queues) with real dependencies in containers (Testcontainers) over mocks where possible. Names state the behavior in the language's convention (`Withdraw_WithInsufficientFunds_Throws...`, `test_withdraw_with_insufficient_funds_raises`, `withdraw with insufficient funds throws`). Arrange/Act/Assert, one behavior per test, no `if` or loops in tests. No real clock, random, network or sleep. Mock only what you own, at boundaries, never the class under test.
- Coverage: aim for full branch coverage of business logic; CI fails under 90% line and branch. Exclude only generated code and thin UI views, with the reason. Mutation testing on critical logic (money, security, parsing): Stryker (.NET, JS/TS), mutmut (Python), cargo-mutants (Rust).
- Never hide a warning or error: no `eslint-disable`, `noqa`, `type: ignore`, `#pragma warning disable`, `@SuppressWarnings`, `[SuppressMessage]`, `#[allow]`, `@ts-ignore`, empty `catch`, `|| true`, errors sent to `/dev/null` or `$null` (a presence check like `command -v x >/dev/null` is fine), `-ErrorAction SilentlyContinue`, skipped or deleted tests, lowered thresholds, files excluded from the linter.
- The only allowed lint exceptions, with the reason next to them: a rule disabled in config because it contradicts a house rule, and Rust `unsafe_code` in a dedicated crate after the user agrees (`references/rust.md`). A warning that cannot be fixed (third-party code, tool bug): stop and tell the user.
- Before builds, test suites, Docker builds and installs, check free RAM and CPU (Windows `Get-CimInstance Win32_OperatingSystem` / `Win32_Processor`; Linux `free -m`, `uptime`; macOS `vm_stat`, `uptime`). Under 4 GB free or over 80% CPU: ask first. A hook blocks a command: report its reason, never work around it.
