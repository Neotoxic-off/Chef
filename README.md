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
    <img src="assets/bench/overview.svg" width="880" alt="Same 13 tasks, same model, a blind reviewer asks for fixes until it merges. Plain Claude: first answer accepted 59%, 46 review rounds per 100 tasks, $0.120 per task with fixes. Chef 1.2: 87%, 15 review rounds per 100 tasks, $0.194 per task with fixes.">
  </picture>
</p>

| | Without chef | With chef |
|---|---|---|
| The reviewer accepts the first answer | 59% | **87%** |
| Tasks sent back for fixes | 41% | **13%** |
| Review rounds, as a share of tasks | 46% | **15%** (−67%) |
| Agent time per task, first answer | 21 s | 42 s (+100%) |
| Agent time per task, fixes and new reviews | 29 s | **11 s** (−62%) |
| Cost per task, review fixes included | $0.120 | $0.194 (**+62%**) |

<sub>13 tasks in 11 stacks, 3 runs each, Sonnet 5.5. The reviewer is a blind Opus session that never knows chef exists; when it would not merge, its required changes go back to the same setup, up to 2 rounds. The code works either way: every first answer passes its hidden tests. <a href="bench/README.md">How it was measured</a>.</sub>

Chef's first answer costs 129% more than a plain one, because it already does what the reviewer would ask for: tests, strict types and linters, pinned versions, configs checked by their tools. Counting the fixes plain Claude needs afterwards, the gap falls to +62%, for 67% fewer review rounds. In agent time the two end level (73 s and 79 s per task until merged, +8%); the difference is on the reviewer's side: 69% fewer tasks come back for another review.

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/bench/time-dark.svg">
    <img src="assets/bench/time.svg" width="880" alt="Agent time per task until merged, mean of 39 tasks. Plain Claude: first answer 21 s, first review 23 s, fixes and new reviews 29 s, 41% sent back. Chef 1.1: 57 s, 25 s, 13 s, 15% sent back. Chef 1.2: 42 s, 26 s, 11 s, 13% sent back. Median time of the first answer by version on the Python, Docker and Prometheus tasks: 0.8.1 45 s, 0.9.0 55 s, 0.10.0 46 s, 1.0.0 45 s, 1.1.0 50 s, 1.2.0 41 s; plain Claude 15 s.">
  </picture>
</p>

Per token, chef is less cost-effective: $1 buys 8.2 accepted first answers without it and 5.3 with it. What it saves is the reviewer's rounds: 1.15 reviews per task instead of 1.46. Once a review round costs more than **$0.24** of the reviewer's time (about 15 seconds at $60/h), chef is the cheaper option; at $10 per round, $11.69 per task against $14.72 (−21%).

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/bench/break-even-dark.svg">
    <img src="assets/bench/break-even.svg" width="880" alt="Machine cost per task plus a human reviewer's cost per review round, from $0 to $20. Chef 1.2 costs less once a round costs more than $0.24; at $10 per round, plain Claude $14.72 and chef 1.2 $11.69 per task, 21% less.">
  </picture>
</p>

<sub>Reviews per task are the first review plus one after each fix. The model prices a round, not the lines in it: chef's code takes 2.3 times as many lines to read (median 231 against 98, lockfiles excluded).</sub>

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
    <img src="assets/bench/history.svg" width="880" alt="Chef by version on the Python, Docker and Prometheus tasks. Cost per task: 0.8.1 $0.167, 0.9.0 $0.184, 0.10.0 $0.180, 1.0.0 $0.155, 1.1.0 $0.145, 1.2.0 $0.156; plain Claude $0.059. Share a blind reviewer would merge as is: 50%, 44%, 67%, 78%, 78%, 89%; plain Claude 44%.">
  </picture>
</p>

<sub>The three tasks every version was run on (Python CLI, Dockerfile + compose, Prometheus), same blind reviewer for every version, 6 to 9 reviews each: read it as a trend.</sub>
