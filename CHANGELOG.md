# Changelog

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
