<p align="center">
  <img src="assets/logo.png" width="180" alt="Chef logo">
</p>

<h1 align="center">Chef</h1>

<p align="center">
  <em>Your kitchen, your rules. Claude cooks the way you do.</em>
</p>

<p align="center">
  <img src="https://img.shields.io/github/stars/Neotoxic-off/chef?style=flat-square&color=D97757&label=stars" alt="Stars">
  <img src="https://img.shields.io/badge/Claude%20Code-plugin-D97757?style=flat-square" alt="Claude Code plugin">
  <img src="https://img.shields.io/badge/languages-34-D97757?style=flat-square" alt="34 languages">
  <img src="https://img.shields.io/badge/references-127-D97757?style=flat-square" alt="127 references">
</p>

**Chef makes Claude write code a reviewer accepts the first time.** It costs more tokens, and saves most of the review round-trips.

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/bench/overview-dark.svg">
    <img src="assets/bench/overview.svg" width="880" alt="Same 13 tasks, same model, a blind reviewer asks for fixes until it merges. Plain Claude: first answer accepted 59%, 0.46 review rounds per task, $0.120 per task with fixes. Chef 1.2: 87%, 0.15 review rounds, $0.194 per task with fixes.">
  </picture>
</p>

| | Without chef | With chef |
|---|---|---|
| The reviewer accepts the first answer | 59% | **87%** |
| Review rounds needed per task | 0.46 | **0.15** (67% fewer) |
| Cost per task, review fixes included | $0.120 | $0.194 (**1.62×**) |

<sub>13 tasks in 11 stacks, 3 runs each, Sonnet 5.5. The reviewer is a blind Opus session that never knows chef exists; when it would not merge, its required changes go back to the same setup, up to 2 rounds. The code works either way: every first answer passes its hidden tests. <a href="bench/README.md">How it was measured</a>.</sub>

Chef's first answer costs 2.3× a plain one, because it already does what the reviewer would ask for: tests, strict types and linters, pinned versions, configs checked by their tools. Counting the fixes plain Claude needs afterwards, the gap falls to 1.62×, for 67% fewer review rounds.

## Install

```
/plugin marketplace add Neotoxic-off/chef
```
```
/plugin install chef@chef
```

That's it: chef applies to every coding prompt from now on.

## What chef does

- **Asks before guessing**, and remembers your answers in `.chef.md`.
- **Tests every change**, and sets up a formatter, a linter and a strict type checker. Warnings get fixed, never hidden.
- **Types every signature**, pins dependencies, images and actions.
- **Knows your stack:** 127 references (34 languages, frameworks, infra, CI) with the right tools and configs.
- **Brings a council** of agents for design decisions, and a reviewer for changes.

## Commands

| Command | |
|---|---|
| `/chef:level lite \| full \| max` | How much process: `lite` keeps every code rule but skips the council and reviewer. |
| `/chef:status` | Current level, project settings and detected stacks. |
| `/chef:transform <goal>` | Upgrade or migrate a codebase in small, tested, committed batches. |

## Spend less

- `/chef:level lite` drops the council and the reviewer agent, the biggest cost on large tasks.
- Or skip the plugin: copy [`export/AGENTS.md`](export/AGENTS.md), chef's 12 core rules, into your project. It works with any agent (Codex, Cursor, Copilot) and gets part of the effect (in the 1.0 benchmark: 56% merged as is against 89% with chef, at $0.084 per task).

## Change a rule

Edit [`skills/chef/SKILL.md`](skills/chef/SKILL.md) or a stack file in [`skills/chef/references/`](skills/chef/references/), then run `bash scripts/check.sh`. Changes are listed in the [CHANGELOG](CHANGELOG.md).

## Across versions

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/bench/history-dark.svg">
    <img src="assets/bench/history.svg" width="880" alt="Chef by version on the Python, Docker and Prometheus tasks. Cost per task: 0.8.1 $0.167, 0.9.0 $0.184, 0.10.0 $0.180, 1.0.0 $0.155, 1.1.0 $0.145; plain Claude $0.059. Share a blind reviewer would merge as is: 50%, 44%, 67%, 78%, 78%; plain Claude 44%.">
  </picture>
</p>

<sub>The three tasks every version was run on (Python CLI, Dockerfile + compose, Prometheus), same blind reviewer for every version, 6 to 9 reviews each: read it as a trend.</sub>
