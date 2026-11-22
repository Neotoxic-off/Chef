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
- **Brings a council** of agents for design decisions, and a reviewer for changes.
- **Talks less:** short replies, the smallest complete change ([`lean.md`](skills/chef/lean.md), adapted from [ponytail](https://github.com/DietrichGebert/ponytail), MIT).

## Results

A blind reviewer that never knows chef exists asks for fixes until it would merge. Same tasks, same model (Sonnet 5.5). [How it was measured](bench/README.md).

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

Code quality on the 32 most-used references, one task each, scored 0 to 10 by a blind reviewer:

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/bench/quality-dark.svg">
    <img src="assets/bench/quality.svg" width="880" alt="Blind reviewer scores from 0 to 10 over 32 most-used references. Quality: plain Claude 7.1, chef 1.3 7.8, chef 1.4 7.6, chef 1.5 7.6. Clarity: 8.2, 8.7, 8.6, 8.7. Maintainability: 5.5, 7.4, 7.5, 7.5. Functionality: 7.8, 7.8, 7.7, 7.7. Then the mean of the four scores per reference.">
  </picture>
</p>

Chef raises maintainability from 5.5 to 7.5; versions 1.3 to 1.5 score alike on a single answer.

### Earlier benches

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/bench/overview-dark.svg">
    <img src="assets/bench/overview.svg" width="880" alt="Same 13 tasks, same model, a blind reviewer asks for fixes until it merges. Plain Claude: first answer accepted 59%, 46 review rounds per 100 tasks, $0.120 per task with fixes. Chef 1.3: 90%, 13 review rounds per 100 tasks, $0.181. Chef 1.4: 92%, 10 review rounds per 100 tasks, $0.185.">
  </picture>
</p>

| | Without chef | Chef 1.4 |
|---|---|---|
| First answer accepted | 59% | **92%** |
| Review rounds per task | 0.46 | **0.10** |
| Cost per task, fixes included | $0.120 | $0.185 |

Chef costs more per answer, and saves the reviewer's rounds.

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/bench/history-merge-dark.svg">
    <img src="assets/bench/history-merge.svg" width="880" alt="Chef across versions, share of first answers a blind reviewer would merge as is: 0.8.1 50%, 0.9.0 44%, 0.10.0 67%, 1.0.0 78%, 1.1.0 78%, 1.2.0 89%, 1.3.0 100%, 1.4.0 100%; plain Claude 44%.">
  </picture>
</p>

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/bench/history-cost-dark.svg">
    <img src="assets/bench/history-cost.svg" width="880" alt="Chef across versions, median cost per task: 0.8.1 $0.167, 0.9.0 $0.184, 0.10.0 $0.180, 1.0.0 $0.155, 1.1.0 $0.145, 1.2.0 $0.156, 1.3.0 $0.169, 1.4.0 $0.173; plain Claude $0.059.">
  </picture>
</p>

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/bench/time-dark.svg">
    <img src="assets/bench/time.svg" width="880" alt="Agent time per task until merged, mean of 39 runs (13 tasks, 3 runs each). Plain Claude: first answer 21 s, first review 23 s, fixes and new reviews 29 s, 41% sent back. Chef 1.1: 57 s, 24 s, 13 s, 15% sent back. Chef 1.2: 42 s, 26 s, 11 s, 13% sent back. Chef 1.3: 44 s, 30 s, 7 s, 10% sent back. Chef 1.4: 46 s, 25 s, 7 s, 8% sent back. Median time of the first answer by version on the Python, Docker and Prometheus tasks: 0.8.1 45 s, 0.9.0 55 s, 0.10.0 46 s, 1.0.0 45 s, 1.1.0 50 s, 1.2.0 41 s, 1.3.0 41 s, 1.4.0 47 s; plain Claude 15 s.">
  </picture>
</p>

Chef is the cheaper option once a human review round costs more than $0.18.

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/bench/break-even-dark.svg">
    <img src="assets/bench/break-even.svg" width="880" alt="Machine cost per task plus a human reviewer's cost per review round, from $0 to $20. Chef 1.4 costs less once a round costs more than $0.18; at $10 per round, plain Claude $14.72, chef 1.3 $11.48 and chef 1.4 $11.19 per task (24% less than plain Claude).">
  </picture>
</p>

Most-used stacks (Node, React, Bash, SQL, PHP, PowerShell, C, C++, Kotlin):

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/bench/stacks-dark.svg">
    <img src="assets/bench/stacks.svg" width="880" alt="Most-used stacks, 9 tasks. Plain Claude: first answer accepted 44%, 74 review rounds per 100 tasks, $0.150 per task with fixes. Chef 1.4: 67%, 37 review rounds per 100 tasks, $0.260 per task with fixes.">
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
