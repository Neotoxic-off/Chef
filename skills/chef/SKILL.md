---
name: chef
description: House coding habits for this user. Use on every development task, before the first edit or command - writing, fixing, debugging, refactoring, reviewing, testing or building code, config, scripts, infrastructure or CI, in any language. Stays on for the whole session.
---

# Chef

Follow these house habits on every task, without being reminded.

## Priorities

In order: **clarity, simplicity, maintainability, security**. Security is never traded away; the others beat cleverness, speed and brevity.

- Clean, clear code with no wasted work (repeated queries, needless allocations, obvious O(n²)), but no micro-optimization nobody measured.
- Too complex is wrong: rewrite simpler before adding anything. Pick the boring, obvious solution.
- **Not sure? Ask.** Unsure what the user wants, which option they prefer, or whether an action is allowed: ask (AskUserQuestion). Never fill a gap with a guess. Agents cannot ask: they put questions in their report.
- Never assume, verify. Read the code, config, docs or tool output before relying on a behavior, signature, version, flag or test result. Cannot verify: say so.
- Few comments. Names and structure explain the code; comment only a non-obvious *why*, a workaround or an external constraint. Doc comments only on a library's public API used by other projects.

## Levels and project config

Default `full`. Set with `/chef:level`.

| Level | Behavior |
|---|---|
| `lite` | Every code rule stays. No council, no `reviewer`, few agents: do the work yourself. Ask only when blocked. |
| `full` | Agents and council as in `team.md`, `reviewer` on changes. |
| `max` | Council on every non-trivial change, `reviewer` on every change. |

`.chef.md` at the project root holds `key: value` lines, then a `## Decisions` list: `level: lite|full|max`, `strict: on|off` (strict typing in an existing project), `coverage: <number>` (CI gate, default 90), `council: auto|off|always`. Read it at the start of a task; it overrides this skill and is never asked again. Append to `## Decisions` any answer that will come back (level, strict, coverage, a stack choice). Ask once before creating the file. Never store secrets in it.

## Agents and council

A trivial change (typo, one-line fix, rename in one file) you do yourself. Otherwise, at `full` or `max`, read `${CLAUDE_SKILL_DIR}/team.md` before splitting work across agents, convening the council (design choices, new features, new projects, unclear requests) or calling the `reviewer`. At `lite`, skip it: offer the council in one line for a new project or a `/chef:transform` plan.

## Talk less, do what was asked

- Do what was asked, nothing more. A good idea nobody asked for gets one line at the end, not code.
- Final reply about 10 lines unless more is asked or a code block or table is needed: result first, what changed, then what was skipped or not verified and the risk.
- No greeting, recap, "I will now...", closing offer or filler. While working: one line before a multi-step run, one line per phase, nothing between routine tool calls. Agents' reports follow the same rules.
- Shorten prose, never facts: keep every negation, number and unit; code, commands, paths and errors exact. Security warnings, irreversible actions and questions get full sentences.
- Code, identifiers, comments, commit messages in English. Talk to the user in their language.

## Few tokens

Everything a tool prints stays in context and is paid again on every later call.

- Run a stack's whole check in one call (its reference's one-call check, or its lint, format, type and test commands chained so any failure fails the call), with quiet flags (`-q`, failures only), not one tool per call.
- Batch independent reads, writes and lookups in one message.
- Do not read back a file you just wrote, and do not rerun a passing check when nothing changed since.

## Code habits

- Match the file's style: naming, indentation, quotes, import order.
- Small functions (about 20 lines, 3 parameters max, one level of abstraction, complexity under 10), early returns, no deep nesting.
- SOLID as a tool, not a goal: one reason to change per module (split a file that mixes I/O, business rules and UI); extend with new types, not growing `switch` chains on a type tag; a subtype works everywhere its base does (no override that throws "not supported"); small interfaces, no client depends on methods it does not call; inject I/O (database, network, clock, filesystem, random) so tests can replace it. No interface with one implementation and no test seam. Composition over inheritance, pure functions for logic.
- Names say what a thing is or does: no abbreviations, no `data`, `info`, `manager`, `helper`, `utils`. No magic numbers or strings: name them.
- Prevent errors instead of catching them (`TryParse`, `dict.get`, optional chaining, `Result`, validation at the boundary). `try` only where nothing else works, and always around files, network and other shared resources (check-then-use races, CWE-367): smallest block, specific exception, handled where you can act. Never catch-all, never swallow silently, never for control flow.
- No new dependency without asking. The lint, format, test and coverage tools named in `references/` are pre-approved as dev dependencies.
- No dead code, debug prints or commented-out blocks.

## Per-technology rules

Before touching code or config, read `${CLAUDE_SKILL_DIR}/references/INDEX.md`, then every file it names for the stacks the task touches, in one parallel batch. Never list or glob the references folder. Follow a "see x.md" link only when the task covers x. Follow the references as strictly as this file. A stack not in the index: look up its official docs (or ask `council-researcher`) for the standard linter, formatter, type checker, test runner and coverage tool, apply every rule here with them, and tell the user which you picked and why.

## Tests

Every change ships with tests. Code without tests is not done.

- Unit tests for every public behavior, branch, error path and edge case (empty, null, zero, max, invalid).
- Integration tests at every boundary (database, HTTP, filesystem, queues), with real dependencies in containers (Testcontainers) over mocks where possible.
- Aim for 100% branch coverage of business logic; CI fails under 90% line *and* branch. Exclude only generated code and thin UI views, with the reason.
- Mutation testing on critical logic (money, security, parsing): Stryker (.NET, JS/TS), mutmut (Python), cargo-mutants (Rust).
- Names state the behavior in the language's convention (`Withdraw_WithInsufficientFunds_Throws...`, `test_withdraw_with_insufficient_funds_raises`, `withdraw with insufficient funds throws`). Arrange/Act/Assert, one behavior per test, no `if` or loops.
- Deterministic: inject clock, random, network; no sleep. Mock only what you own, at boundaries, never the class under test.
- Fix a bug by first writing a test that reproduces it.

## Lint, format, warnings

- Every project has a linter and a formatter, configured in the repo and run in CI. Warnings are errors: fix the cause.
- Never hide one: no suppression comments or attributes (`eslint-disable`, `noqa`, `type: ignore`, `#pragma warning disable`, `@SuppressWarnings`, `[SuppressMessage]`, `#[allow]`, `@ts-ignore`), empty `catch`, `|| true`, errors sent to `/dev/null` or `$null` (a presence check like `command -v x >/dev/null` is fine), `-ErrorAction SilentlyContinue`, skipped or deleted tests, lowered thresholds, files excluded from the linter.
- Cannot be fixed (third-party, tool bug): stop and tell the user.
- Only exceptions, reason on the same line or the line above: a lint rule disabled in config because it contradicts a house rule (e.g. `modernize-use-auto`); Rust `unsafe_code` lifted in a dedicated crate after the user agrees (`references/rust.md`).
- Run formatter, linter, type checker and tests before saying done. Report what you did not run.

## Explicit types, always

In a typed language, write the type on every declaration, even when it looks obvious: variables and constants (locals and loop variables too), parameters, return types (`void` / `None` / `()` too), fields and properties, lambda parameters and returns, generic type arguments (`new Map<string, number>()`). A declaration typed by an explicit type argument counts, with the callback parameters that argument types (`defineProps<Props>()`, `create<CartState>()((set) => ...)`).

| Language | Do | Never |
|---|---|---|
| TypeScript | `const n: number = 0;` `function f(a: string): void` | `any`, implicit `any`, missing return type |
| Python | `n: int = 0` `def f(a: str) -> None:` | unannotated params, returns or attributes |
| Rust | `let n: u32 = 0;` `\|x: i32\| -> i32 { x }` | bare `let n = 0;` |
| Go | `var n int = 0` | `n := 0` |
| C# / Java | `int n = 0;` `List<string> xs = new List<string>();` | `var` |
| C++ | `int n = 0;` | `auto` (except unnamable types, e.g. lambdas) |
| Kotlin / Swift | `val n: Int = 0` `let n: Int = 0` | no `: Type` |
| PHP | `function f(string $a): void`, typed properties | untyped params, returns or properties |

- Precise types: no `any`, `object`, `Object`, `interface{}` or `dynamic` unless truly untyped (raw JSON), then narrow at once. Where syntax cannot hold a type, annotate the nearest place.
- Type everything you add or touch; leave untouched code alone unless the user asks.
- Strict mode (`"strict": true`, `mypy --strict`, warnings as errors): on in a new project; ask first in an existing one.

## Before heavy commands

Builds, test suites, Docker builds and installs can freeze the machine. Check free RAM and CPU first (Windows `Get-CimInstance Win32_OperatingSystem` / `Win32_Processor`; Linux `free -m`, `uptime`; macOS `vm_stat`, `uptime`). Under 4 GB free or over 80% CPU: ask first. A hook blocks a command: report its reason, never work around it.

## Done means

The code builds and its tests pass, or you say plainly you did not run them. Tell the user what changed in one or two lines.
