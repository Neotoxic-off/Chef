<p align="center">
  <img src="assets/logo.png" width="180" alt="Chef logo">
</p>

<h1 align="center">Chef</h1>

<p align="center">
  <em>Your AI-powered coding chef crafting clean, secure, and maintainable code with precision</em>
</p>

<p align="center">
  <img src="https://img.shields.io/github/v/tag/Neotoxic-off/chef?sort=semver&style=flat-square&color=D97757&label=release" alt="Latest release">
  <img src="https://img.shields.io/github/stars/Neotoxic-off/chef?style=flat-square&color=D97757&label=stars" alt="Stars">
  <img src="https://img.shields.io/badge/Claude%20Code-plugin-D97757?style=flat-square" alt="Claude Code plugin">
  <img src="https://img.shields.io/badge/languages-34-D97757?style=flat-square" alt="34 languages">
  <img src="https://img.shields.io/badge/references-127-D97757?style=flat-square" alt="127 references">
</p>

## Install

```
/plugin marketplace add Neotoxic-off/chef
```
```
/plugin install chef@chef
```

Chef then applies to every coding prompt.

## What chef does

- **Tests every change** and sets up a formatter, a linter and a strict type checker. Warnings get fixed, never hidden.
- **Types and pins:** every signature typed; dependencies, images and actions pinned.
- **Knows your stack:** 127 references (34 languages, frameworks, infra, CI).
- **Asks before guessing**, and remembers your answers in `.chef.md`. Your explicit instruction wins, never over security.
- **Brings a council** of agents for design decisions, and a reviewer for changes spanning several modules.
- **Talks less:** short replies, the smallest complete change ([`lean.md`](skills/chef/lean.md), adapted from [ponytail](https://github.com/DietrichGebert/ponytail), MIT).

## Results

A blind reviewer that never knows chef exists asks for fixes until it would merge. Same tasks, same model (Sonnet 5.5). [How it was measured](bench/README.md).

The model's behavior drifts from day to day: on 2026-11-25, plain Claude pinned to the same Claude Code 2.1.330 thought up to 100 times more than on 2026-11-22 and cost 1.5 to 3.3 times as much. Costs are only compared between arms run on the same day.

### Chef 1.5, same day as chef 1.4 and plain Claude (2026-11-25)

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/bench/overview-dark.svg">
    <img src="assets/bench/overview.svg" width="880" alt="Same day, 13 tasks, one run each, a blind reviewer asks for fixes until it merges. Plain Claude: first answer accepted 92%, 15 review rounds per 100 tasks, $0.145 per task with fixes. Chef 1.4: 100%, no review round, $0.375. Chef 1.5: 100%, no review round, $0.270.">
  </picture>
</p>

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/bench/overview-152-dark.svg">
    <img src="assets/bench/overview-152.svg" width="880" alt="Same day, 11 tasks of the 1.5 bench. Plain Claude, 11 runs: first answer accepted 82%, 18 review rounds per 100 tasks, $0.208 per task with fixes. Chef 1.4, 11 runs: 100%, no review round, $0.510. Chef 1.5, 22 runs: 100%, no review round, $0.348.">
  </picture>
</p>

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/bench/devops-152-dark.svg">
    <img src="assets/bench/devops-152.svg" width="880" alt="Same day, 7 DevOps and CI tasks, 14 runs per arm. Plain Claude, chef 1.4 and chef 1.5: first answer accepted 100%, no review round; $0.123, $0.331 and $0.260 per task with fixes.">
  </picture>
</p>

Chef 1.5 costs 28% less than 1.4 on the 13 older tasks, 32% less on the 11 tasks of the 1.5 bench (cheaper on 10 of them) and 22% less on the DevOps and CI tasks; on the 11 tasks its first answer comes in 155 s instead of 210 s. Every first answer of both versions was accepted that day, against 92% and 82% for plain Claude, so these benches no longer separate 1.4 from 1.5 on quality.

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/bench/time-dark.svg">
    <img src="assets/bench/time.svg" width="880" alt="Agent time per task until merged, mean of 13 runs on the 13 tasks, same day. Plain Claude: first answer 65 s, first review 20 s, fixes and new reviews 4 s, 8% sent back. Chef 1.4: 148 s, 24 s, 0 s, none sent back. Chef 1.5: 114 s, 24 s, 0 s, none sent back. Median time of the first answer by version on the Python, Docker and Prometheus tasks: 0.8 45 s, 0.9 55 s, 0.10 46 s, 1.0 45 s, 1.1 50 s, 1.2 41 s, 1.3 41 s, 1.4 47 s, 1.5 93 s; plain Claude 46 s on 2026-11-25.">
  </picture>
</p>

Chef 1.5 is the cheaper option once a human review round costs more than $0.83.

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/bench/break-even-dark.svg">
    <img src="assets/bench/break-even.svg" width="880" alt="Machine cost per task plus a human reviewer's cost per review round, from $0 to $20, on the 13 tasks, same day. Chef 1.5 costs less once a round costs more than $0.83; at $10 per round, plain Claude $11.65 and chef 1.5 $10.27 per task (12% less).">
  </picture>
</p>

Chef against caveman and ponytail, same day. Chef here is the 1.5 skill before its reviewer fix (`ad13bf7`), so its cost is an upper bound. With 2 runs per task, these are trends, not proof.

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/bench/styles-dark.svg">
    <img src="assets/bench/styles.svg" width="880" alt="Same day, 4 tasks, 2 runs each. Plain Claude: first answer accepted 88%, $0.233 per task, 270 lines to review. Chef 1.5: 100%, $0.389, 419 lines. Chef without lean.md: 100%, $0.374, 510 lines. Caveman 4.1: 100%, $0.165, 251 lines. Ponytail 5.3: 88%, $0.208, 229 lines.">
  </picture>
</p>

Caveman and ponytail shorten replies and code, so they cost less than plain Claude; chef's extra cost buys the tests, linter and type checker it sets up and runs. `lean.md` cuts the code to review by about a fifth, at the same cost.

### The 1.5 bench, first 1.5 release (2026-11-22)

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/bench/overview-15-dark.svg">
    <img src="assets/bench/overview-15.svg" width="880" alt="Chef 1.5 bench, 11 tasks, 3 of them held out, 95 runs per arm. Plain Claude: first answer accepted 58%, 53 review rounds per 100 tasks, $0.145 per task with fixes. Chef 1.4: 75%, 33 review rounds per 100 tasks, $0.278. Chef 1.5: 87%, 15 review rounds per 100 tasks, $0.293.">
  </picture>
</p>

| | Without chef | Chef 1.4 | Chef 1.5 |
|---|---|---|---|
| First answer accepted | 58% | 75% | **87%** |
| Review rounds per task | 0.53 | 0.33 | **0.15** |
| Cost per task, fixes included | $0.145 | $0.278 | $0.294 |
| Median time, first answer | 21 s | 65 s | 94 s |

Chef 1.5 against 1.4: +13 points (p = 0.04), with half the review rounds. Its first answer is slower: it now runs every check, from a container when a tool is missing.

Code quality per language: one task for each of the 32 most-used references, the mean of a blind reviewer's scores for quality, clarity, maintainability and functionality.

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/bench/quality-dark.svg">
    <img src="assets/bench/quality.svg" width="880" alt="Code quality per language, 0 to 10, by a blind reviewer, without chef and with chef 1.5. All 32: 7.1 and 7.9. The biggest gains: GitHub Actions 4.8 and 7.5, Bash 6.8 and 8.2, Ruby 5.8 and 7.2.">
  </picture>
</p>

### Across versions

Each version ran on its own day, so the costs are not comparable from one point to the next. The 1.5 point is its latest patch; it and plain Claude ran on 2026-11-25, a day the model thought far more than before (see above): plain Claude cost $0.137 per task that day, against $0.059 when the earlier versions ran.

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/bench/history-cost-dark.svg">
    <img src="assets/bench/history-cost.svg" width="880" alt="Chef across versions, median cost per task: 0.8 $0.167, 0.9 $0.184, 0.10 $0.180, 1.0 $0.155, 1.1 $0.145, 1.2 $0.156, 1.3 $0.169, 1.4 $0.173, 1.5 $0.272; plain Claude $0.137 on 2026-11-25, the day of the 1.5 point.">
  </picture>
</p>

## Commands

| Command | |
|---|---|
| `/chef:level lite \| full \| max` | How much process: `lite` keeps every code rule, skips the council and reviewer. |
| `/chef:status` | Current level, project settings and detected stacks. |
| `/chef:transform <goal>` | Upgrade or migrate a codebase in small, tested batches. |

## Spend less

- `/chef:level lite` drops the council and the reviewer.
- Turn chef off in one project: `claude plugin disable chef@chef --scope local`.
- No plugin: copy [`export/AGENTS.md`](export/AGENTS.md), chef's core rules, into any agent's project.

## Change a rule

Edit [`skills/chef/SKILL.md`](skills/chef/SKILL.md) or a file in [`skills/chef/references/`](skills/chef/references/), then run `bash scripts/check.sh`. See the [CHANGELOG](CHANGELOG.md).
