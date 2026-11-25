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

### Chef 1.6 against 1.5, 1.4 and plain Claude

Chef 1.6 had every first answer accepted on the 13, 11 and 7-task benches, like 1.4 and unlike 1.5 (one miss on the 11 tasks). It costs 4% less than 1.5 on the 11 tasks and 6% less on the DevOps and CI tasks, and 2% more on the 13 older tasks; against 1.4 it costs 26% to 36% less. Against plain Claude it costs 1.7 to 2 times as much per task, and takes about 1.6 times as long to a merged change.

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/bench/time-dark.svg">
    <img src="assets/bench/time.svg" width="880" alt="Plain Claude: first answer 65 s, first review 20 s, fixes and new reviews 4 s, 8% sent back; Chef 1.4: first answer 148 s, first review 24 s, fixes and new reviews 0 s, 0% sent back; Chef 1.5: first answer 114 s, first review 24 s, fixes and new reviews 0 s, 0% sent back; Chef 1.6: first answer 114 s, first review 30 s, fixes and new reviews 0 s, 0% sent back. First answer by version, as a multiple of plain Claude&#x27;s: 0.8 3.0×, 0.9 3.7×, 0.10 3.1×, 1.0 3.0×, 1.1 3.3×, 1.2 2.7×, 1.3 2.7×, 1.4 3.1×, 1.5 2.0×, 1.6 1.8×.">
  </picture>
</p>

Chef 1.6 is the cheaper option once a human review round costs more than $0.86.

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/bench/break-even-dark.svg">
    <img src="assets/bench/break-even.svg" width="880" alt="Machine cost per task plus a human reviewer&#x27;s cost per review round. Chef 1.6 costs less once a round costs more than $0.86; at $10 per round, plain Claude $11.65 and chef 1.6 $10.27 per task, 12% less.">
  </picture>
</p>

Chef against caveman and ponytail, 4 tasks, 2 runs each: trends, not proof.

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/bench/styles-dark.svg">
    <img src="assets/bench/styles.svg" width="880" alt="Same day, 4 tasks (Bash, TypeScript bug fix, Python CLI, Python refactor), 2 runs each. Plain Claude: first answer accepted 88%, $0.233 per task, 270 lines to review; Chef 1.5: first answer accepted 100%, $0.389 per task, 419 lines to review; Chef 1.6: first answer accepted 100%, $0.324 per task, 408 lines to review; Caveman 4.1: first answer accepted 100%, $0.165 per task, 251 lines to review; Ponytail 5.3: first answer accepted 88%, $0.208 per task, 229 lines to review">
  </picture>
</p>

Caveman and ponytail shorten replies and code, so they cost less than plain Claude; chef's extra cost buys the tests, linter and type checker it sets up and runs. Chef 1.6 costs 17% less than 1.5 here.

### Code quality per language

One task for each of the 32 most-used references, the mean of a blind reviewer's scores for quality, clarity, maintainability and functionality. Chef 1.6 scores 8.5 against 8.0 for plain Claude, higher on 24 of the 32 languages and lower on 3.

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/bench/quality-dark.svg">
    <img src="assets/bench/quality.svg" width="880" alt="Code quality per language, 0 to 10, without chef then with chef 1.6. All: 8.0 to 8.5. C# 7.8 to 9.2; FastAPI 7.0 to 8.5; Redis 6.5 to 8.0; Angular 7.8 to 9.0; GitHub Actions 7.8 to 8.8; Python 7.2 to 8.2; React 7.8 to 8.8; TypeScript 8.0 to 9.0; MongoDB 7.2 to 8.0; Rails 7.8 to 8.5; Terraform 8.2 to 9.0; Bash 7.5 to 8.0; Django 8.0 to 8.5; PowerShell 7.8 to 8.2; Ruby 8.0 to 8.5; SQL 8.0 to 8.5; C++ 8.2 to 8.5; Docker 8.0 to 8.2; Kotlin 8.8 to 9.0; Next.js 8.0 to 8.2; PHP 8.8 to 9.0; PostgreSQL 8.0 to 8.2; Spring Boot 8.8 to 9.0; Vue 8.0 to 8.2; C 8.8 to 8.8; Java 8.8 to 8.8; Kubernetes 8.0 to 8.0; Rust 8.8 to 8.8; Swift 8.8 to 8.8; ASP.NET Core 8.5 to 8.2; Go 8.8 to 8.5; Laravel 7.2 to 6.5">
  </picture>
</p>

### Across versions

Cost per task as a multiple of plain Claude's, on the three tasks every version ran (Python CLI, Dockerfile + compose, Prometheus).

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/bench/history-cost-dark.svg">
    <img src="assets/bench/history-cost.svg" width="880" alt="Chef across versions: cost per task, as a multiple of plain Claude&#x27;s, on python, docker, prometheus: 0.8 2.8×, 0.9 3.1×, 0.10 3.1×, 1.0 2.6×, 1.1 2.5×, 1.2 2.6×, 1.3 2.9×, 1.4 2.9×, 1.5 2.0×, 1.6 1.9×. Plain Claude: 1.0×.">
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
