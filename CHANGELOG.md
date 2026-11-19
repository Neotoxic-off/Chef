# Changelog

## 0.9.0 (2026-11-19)

- Fewer tokens per session: `SKILL.md` cut from 20.3 KB to 9.5 KB. The team and council procedure moved to `skills/chef/team.md`, read only when agents, a council or the `reviewer` are used. The CommunityToolkit rules moved to `references/csharp.md`. `INDEX.md` tables became lists. No rule removed.
- Benchmark harness in `bench/`: `run.sh` runs each task in a fresh git folder per arm, `score.py` checks the output with pytest, coverage, mypy, ruff, hadolint, promtool and a container health check.
- Benchmark rerun: without chef, chef 0.8.1 and chef 0.9.0, on a Python CLI, a Dockerfile with compose, and a Prometheus setup.

## 0.8.1 (2026-11-19)

- `pin-gate.sh` checks only the workflows Claude edited in the session (recorded by a `PostToolUse` hook on Edit/Write), and blocks once instead of every turn.
- `/chef:status` reads the current session's transcript by session id, not the newest one in the project.

## 0.8.0 (2026-11-19)

- Levels `lite | full | max`, set with `/chef:level`. `full` stays the default. `lite` keeps every code rule but drops the council and the reviewer; `max` runs both on every non-trivial change.
- Per-project `.chef.md`: level, strict mode, coverage target, council, and a `## Decisions` list so an answered question is not asked again.
- `/chef:status`: active level, overrides, detected stacks, and the session's tokens, subagents and elapsed time.
- Stop hook `pin-gate.sh`: blocks once when a changed GitHub workflow uses an action not pinned by a full commit SHA.
- Transform stop gate: once a batch is `[x]`, `TRANSFORM.md` needs `Target:` and `## Council`, and every ticked batch needs its own commit.
- "Talk less" tightened: about 10 lines per reply, result first, closing line on what was skipped and the risk.
- Benchmark rerun with real checks: hidden tests, coverage, `mypy --strict`, `tsc --strict`, hadolint.

## 0.7.0 (2026-11-19)

- `/chef:transform <goal>`: upgrades and migrations in the AWS Transform style. Baseline, plan in a committed `TRANSFORM.md`, council review, user approval, then batches that are validated, reviewed and committed one by one, with resume and a before/after report.
- Migration mode: the diff holds only what the migration needs; chef's style rules apply to new and changed lines only.
- Stop hook scoped to the transform skill: blocks the end of a turn once while a batch is marked `[~]`. Not active outside a transform.
- 5 recipes: `dotnet-upgrade.md`, `ts-strict.md`, `test-coverage.md`, `java-upgrade.md`, `python-upgrade.md`.
- A new project goes through the council before its first file.
- CI: `scripts/check.sh` checks every skill's frontmatter; bats tests for the stop hook.

## 0.6.0 (2026-11-19)

- Council grows to nine members: `council-security`, `council-ops`, `council-user` and `council-maintainer` join.
- Core (senior, skeptic, novice) sits on every council; the lead adds two or three specialists that fit the problem.
- Rust `unsafe_code` in a dedicated crate, with the user's agreement, is an explicit lint exception in `SKILL.md`.

## 0.5.0 (2026-11-19)

- `UserPromptSubmit` hook: every development prompt goes through the chef skill.
- `reviewer` agent shipped with the plugin.
- Stack routing moved from `SKILL.md` to `references/INDEX.md`: about a quarter fewer tokens per skill load.
- The 63 references without a verified date were checked against current docs and gained a "Verified against" line; `rust.md` covers supply-chain checks, MSRV and `unsafe`.
- Docker digests and GitHub Action SHAs: commands to look up the real value, never invent one.
- TypeScript: a diff check for untyped `const`/`let` before saying done.
- "Before heavy commands" rule restored, with Linux and macOS commands.
- Council members keep their own report format.
- CI: `scripts/check.sh` checks the index, agents, README badge and JSON manifests, with bats tests and ShellCheck.
- Removed the leftover `.gitignore` from the old benchmark harness.

## 0.4.1 (2026-11-18)

- CommunityToolkit pre-approved for MAUI and Avalonia; Qt owning-memory rule off.

## 0.4.0 (2026-11-18)

- 71 more references: languages, mobile, desktop, games, web, cloud, cross-cutting, data and AI. README coverage table.

## 0.3.0 (2026-11-18)

- 26 framework, observability and data references; lint-clash fixes; "talk less" rule.

## 0.2.0 (2026-11-18)

- Council agents: senior, researcher, outsider, novice, skeptic, with cross-examination.
- Always ask the user when not sure.

## 0.1.0 (2026-11-18)

- Chef skill with house coding rules and per-stack references.
