# Lean: less code, fewer words

Read at the start of every task, by the lead and by every agent. Adapted from ponytail (MIT, see `LICENSE-ponytail`). Where this file and `SKILL.md` differ, `SKILL.md` wins: every change still ships with tests, types and lint.

## The smallest complete change

Before writing, list every place the change must reach: callers, tests, fixtures, config, exports. That is the scope; extra features are not. Then take the first option that fully works:

1. Does it need to exist? Skip features, options and flexibility nobody asked for, and name them in one line.
2. Already in the codebase (a helper, component, pattern)? Use it the way the surrounding code does.
3. Standard library or platform feature? Use it, unless the project has its own.
4. An installed dependency? Use it. Never add a dependency for a few lines.
5. One line a reader gets at a glance? One line.
6. Otherwise, the minimum code that works.

- No wrapper, option, config, abstraction, type conversion or "for later" code nobody asked for: keep values in the form the platform gives. Deletion beats addition. Keep the structure the codebase already has.
- Between options of equal size, take the one that is correct on edge cases.
- Tests: one parametrized test per behavior (`pytest.mark.parametrize`, `it.each`, table-driven), not one copy per case.
- Config files hold only what differs from the tool's defaults.
- Lazy about the solution, never about the change: finish every caller, test and fixture it breaks.
- Bug fix: grep every caller of the function first, fix the root cause once in the shared code.
- Code you move keeps its error handling and validation.
- A known limit gets a one-line comment: `shortcut: <the limit>, <when to upgrade>`.
- Never cut: validation at trust boundaries, error handling that prevents data loss, security, accessibility, anything the user asked for.

## Tool calls

- Read only what you need: grep, then the lines around the hit.
- After a fix, rerun only the check that failed; the full check runs once, before done.

## Replies

- Answer first, then what changed, then one or two lines: what was skipped or not verified, and the risk. About 10 lines; a table or code block only when it carries the answer.
- No greeting, recap of the question, "I will now", closing offer or filler. Do not narrate tool calls: one line before a multi-step run, one per phase.
- Shorten prose, never facts: keep every negation, number and unit; code, commands, paths and errors exact.
- Security warnings, irreversible actions and questions to the user get full sentences.
- Code shown in chat: the changed lines plus a line of context.

## Agent reports

- At most 20 lines, 30 for the council senior and the reviewer. Facts, `file:line`, evidence; no preamble, no restating the brief, no praise.
- Report only what the lead needs to decide or act on. Omit an empty section instead of writing "none", except Not done / Not reviewed: write "all verified" when nothing is left out.
- Round 2 of the council: only what changed since round 1.
