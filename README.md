<p align="center">
  <img src="assets/logo.png" width="180" alt="Chef logo">
</p>

<h1 align="center">Chef</h1>

<p align="center">
  <em>Your kitchen, your rules. Claude cooks the way you do.</em>
</p>

<p align="center">
  <img src="https://img.shields.io/github/stars/Neotoxic-off/chef?style=flat-square&color=D97757&label=stars" alt="Stars">
  <img src="https://img.shields.io/github/last-commit/Neotoxic-off/chef?style=flat-square&color=D97757&label=last%20commit" alt="Last commit">
  <img src="https://img.shields.io/badge/Claude%20Code-plugin-D97757?style=flat-square" alt="Claude Code plugin">
  <img src="https://img.shields.io/badge/languages-34-D97757?style=flat-square" alt="34 languages">
  <img src="https://img.shields.io/badge/references-127-D97757?style=flat-square" alt="127 references">
</p>

<p align="center">
  <strong>Tested code in 100% of the code runs, without chef 0%.</strong><br>
  <strong>98% line coverage &middot; explicit types &middot; strict linters &middot; pinned images &middot; tested alert rules</strong><br>
  <strong>And the output works either way:</strong> hidden tests, container health checks and promtool pass in 100% of runs, with or without chef.<br>
  <strong>v0.9 costs 11% fewer tokens than v0.8.1</strong> for the same results.<br>
  <sub>Benchmarked in Claude Code, the same agent with and without the plugin: 3 tasks, Sonnet 5.5, 2 runs per arm, every result checked by real tools. <a href="#numbers">Details</a>.</sub>
</p>

---

You know the kitchen. Every pan has its place, every dish is tasted before it leaves, nobody hides a burnt sauce under parsley. Chef puts that kitchen inside Claude Code: one set of house habits, applied on every task, in every project, without being reminded.

## Numbers

Share of runs that meet each check (2 runs per arm). *Old* is chef v0.8.1, *new* is chef v0.9.0.

| Check | Without chef | Chef 0.8.1 | Chef 0.9.0 |
|---|---|---|---|
| Works: hidden test, container `/health`, `promtool check` | 100% | 100% | 100% |
| Python: tests written (mean) | 0 | 21 | 27.5 |
| Python: line coverage | 0% | 98.4% | 98.5% |
| Python: `mypy --strict` errors (mean) | 1 | 0 | 0 |
| Python: Ruff and strict type checker configured | 0% | 100% | 100% |
| Docker: base image pinned by digest | 0% | 100% | 100% |
| Docker: non-root user, healthcheck, `.dockerignore`, hardened compose, limits | 100% | 100% | 100% |
| Docker: hadolint findings | 0 | 0 | 0 |
| Prometheus: alert rule unit tests (`promtool test rules`), passing | 0% | 100% | 100% |
| Prometheus: every alert has `runbook_url` | 0% | 100% | 100% |
| Prometheus: Prometheus image pinned | 0% | 100% | 100% |

Without chef, Claude writes code and config that work, and nothing around them: no tests, no rule tests, unpinned images, no strict tooling. With chef, the same output ships with tests, coverage, explicit types, pinned images and tested alert rules. Docker hardening was already good without chef on this task.

### Tokens and cost

Mean per task. Tokens are input (including cache reads and writes) plus output, from the `modelUsage` that `claude -p` reports.

| Task | Without chef | Chef 0.8.1 | Chef 0.9.0 | 0.9.0 vs 0.8.1 |
|---|---|---|---|---|
| Python CLI | 78k tokens, $0.060, 15 s | 215k, $0.159, 47 s | 185k, $0.154, 43 s | −14% tokens |
| Dockerfile + compose | 76k, $0.054, 20 s | 319k, $0.147, 63 s | 240k, $0.120, 40 s | −25% tokens |
| Prometheus | 106k, $0.067, 30 s | 308k, $0.198, 42 s | 329k, $0.182, 44 s | +7% tokens |
| **Mean** | **87k, $0.060** | **281k, $0.168** | **251k, $0.152** | **−11% tokens, −10% cost** |

```mermaid
xychart-beta
    title "Tokens per task (thousands)"
    x-axis ["Python", "Docker", "Prometheus"]
    y-axis "k tokens" 0 --> 350
    bar [78, 76, 106]
    bar [215, 319, 308]
    bar [185, 240, 329]
```

<sub>Bars in each group: without chef, chef 0.8.1, chef 0.9.0.</sub>

**The price is real:** chef 0.9.0 uses about 2.9× the tokens, 2.5× the cost and 1.5–2.9× the time of no plugin: it writes and runs tests, configs and checkers that the plain run skips. No run used subagents, so `/chef:level lite` changes nothing on tasks this small; it saves the council and the reviewer on bigger ones.

**Where v0.9 saves.** `SKILL.md` is loaded into every session and re-read on every turn from the cache:

| File | 0.8.1 | 0.9.0 | When it is read |
|---|---|---|---|
| `skills/chef/SKILL.md` | 20.3 KB (≈5.1k tokens) | 9.5 KB (≈2.4k tokens) | Every session |
| `skills/chef/team.md` | in SKILL.md | 5.0 KB (≈1.2k tokens) | Only when agents, a council or the reviewer are used |
| `references/INDEX.md` | 5.3 KB | 4.6 KB | Before touching code |

The team and council procedure moved to `team.md`, the WPF/MAUI/Avalonia rules moved to `references/csharp.md`, and the prose was tightened. No rule was removed.

Every result is checked by running tools on the output, with the same settings for both arms and the agent's own tool config ignored: a hidden test that calls the function the prompt asked for, `docker build` and a request to `/health`, `promtool check config`, `check rules` and `test rules`, `mypy --strict`, Ruff, hadolint, and measured line coverage. See [Benchmark details](#benchmark-details).

## Before / after

Same prompt: *"Create a Python command-line tool that reads a TOML config file containing a list of endpoints (url, timeout in seconds), validates it, and prints which entries are invalid and why."* The URL check from each output, unedited.

<table>
<tr><th>Without chef</th><th>With chef</th></tr>
<tr><td valign="top">

One 50-line function doing everything, no types, section comments, no tests, no lint config.

```python
def validate_entry(entry):
    """Return a list of problems for one
    endpoint entry (empty if valid)."""
    if not isinstance(entry, dict):
        return [f"entry must be a table, ..."]

    problems = []

    for key in entry.keys() - {"url", "timeout"}:
        problems.append(f"unknown key '{key}'")

    # url
    if "url" not in entry:
        problems.append("missing 'url'")
    else:
        url = entry["url"]
        if not isinstance(url, str):
            problems.append(f"'url' must be ...")
        elif not url.strip():
            problems.append("'url' is empty")
        else:
            try:
                parts = urlsplit(url)
                host = parts.hostname
                parts.port  # raises ValueError
            except ValueError as exc:
                problems.append(f"malformed ({exc})")
            ...
    # timeout
    ...
```

</td><td valign="top">

One small typed function per check, early returns, named constants. Plus Ruff, `mypy --strict`, and 37 tests at 99% coverage.

```python
ALLOWED_SCHEMES: frozenset[str] = frozenset(
    {"http", "https"})


def validate_url(value: object) -> str | None:
    if not isinstance(value, str):
        return f"url must be a string, ..."
    if not value.strip():
        return "url is empty"
    if any(char.isspace() for char in value):
        return "url must not contain whitespace"
    return validate_url_parts(value)


def validate_url_parts(url: str) -> str | None:
    try:
        parts: SplitResult = urlsplit(url)
        hostname: str | None = parts.hostname
        port: int | None = parts.port
    except ValueError as error:
        return f"url is malformed ({error})"
    if parts.scheme not in ALLOWED_SCHEMES:
        return f"url scheme must be http or https"
    if not hostname:
        return "url has no host"
    if port == 0:
        return "url port must not be 0"
    return None
```

</td></tr>
</table>

## How it works

The house rules, in priority order: **clarity, simplicity, maintainability, security.** Security is never traded away.

- **Not sure? Ask.** Claude asks before guessing what you want, and remembers the answer in `.chef.md`.
- **Talk less.** Result first, about 10 lines, then what was skipped and the risk. No recap, no filler.
- **Explicit types** on every variable, parameter, return and field, in every typed language.
- **Tests with every change:** unit and integration, a 90% line and branch coverage gate, mutation testing on critical logic.
- **Never hide a warning.** Fix the cause. No suppression comments, no `|| true`, no lowered thresholds.
- **SOLID, few comments.** If code needs many, it is not clear enough.
- **`try`/`catch` only when nothing else works:** check first (`TryParse`, `dict.get`, `Result`), except for files and network.
- **Before heavy commands** (builds, test suites, installs): check free RAM and CPU first.

Each stack has its own reference (linter, formatter, test runner, coverage tool, configs), loaded only when Claude works in it. A stack not listed is still covered: Claude looks up its official tools first, then applies every rule.

**Rules the model skips are enforced by hooks.** `pin-gate.sh` blocks once per session if a GitHub workflow Claude edited uses an action not pinned by commit SHA; workflows you edit yourself are not checked. During `/chef:transform`, a stop gate requires a `Target:` runtime, a `## Council` section, and one commit per ticked batch.

### The council

For decisions, new projects and unclear requests, Claude acts as the lead and convenes a council: three core members always, plus the two or three specialists the problem calls for. They answer in parallel without seeing each other, then cross-examine; the lead brings you the real choices.

| Agent | Seat | Role |
|---|---|---|
| `council-senior` | core | Knows the stack and the project; proposes the plan and what to reuse. |
| `council-skeptic` | core | Argues it will not work, with evidence, until the plan holds. |
| `council-novice` | core | Knows nothing; asks the simple questions experts skip. |
| `council-researcher` | specialist | Official docs, versions, known issues; cites every source. |
| `council-outsider` | specialist | Never reads the code; reasons from first principles. |
| `council-security` | specialist | Threat model, inputs, secrets, auth, supply chain. |
| `council-ops` | specialist | Deploy, observability, failure modes, rollback, cost. |
| `council-user` | specialist | The real need of whoever uses the result: UX, accessibility. |
| `council-maintainer` | specialist | Owns the code in two years: readability, tests, cost of change. |

One more agent, `reviewer`, did not write the code: it checks every change against the house rules before you see it.

## Install

In Claude Code, as two separate prompts:

```
/plugin marketplace add Neotoxic-off/chef
```
```
/plugin install chef@chef
```

Update: `/plugin marketplace update chef`, then `/reload-plugins`.

That's it. A `UserPromptSubmit` hook routes every development prompt through chef from now on.

## Commands

| Command | What it does |
|---|---|
| `/chef:chef` | Load the house rules now. Usually not needed: the hook does it on every development prompt. |
| `/chef:level [lite \| full \| max]` | Set how much ceremony chef uses in this project, saved in `.chef.md`. No argument shows the current level. |
| `/chef:status` | The active level, the `.chef.md` overrides, the detected stacks, and this session's tokens, subagents and time. |
| `/chef:transform <goal>` | Upgrade or migrate the repo in small batches: baseline, plan in `TRANSFORM.md`, council, your approval, then each batch validated, reviewed and committed. Resumes where it stopped. |

| Level | What changes |
|---|---|
| `lite` | Every code rule (types, tests, lint, security). No council, no reviewer agent. Cheapest. |
| `full` | Default. Council for decisions, reviewer on changes. |
| `max` | Council on every non-trivial change, reviewer always. |

## Stacks covered

| Area | Covered |
|---|---|
| Languages | C#/.NET, TypeScript/JS, Python, Rust, Go, C, C++, Java, Kotlin, Swift, Dart, PHP, Ruby, Scala, Elixir, Lua, Bash, PowerShell, SQL, Zig, Haskell, OCaml, F#, Clojure, Erlang, R, Julia, Perl, Objective-C, Solidity, WebAssembly, CUDA, embedded C/C++, VHDL/Verilog |
| Frontend | React, Next.js, Vue/Nuxt, Angular, Svelte/SvelteKit, Astro, React Router/Remix, SolidJS, Qwik, htmx, Blazor, Tailwind, Vite/webpack/Rolldown, Playwright/Cypress, Storybook |
| Backend | ASP.NET Core, NestJS/Express/Fastify, Django, FastAPI/Flask, Spring Boot, Laravel, Rails, Symfony, Phoenix, Axum/Actix, Go web, Ktor, Quarkus/Micronaut, Deno/Bun/Hono |
| Mobile, desktop, games | Flutter, React Native/Expo, Jetpack Compose, SwiftUI, WPF/WinUI, .NET MAUI, Avalonia, Electron, Tauri, Qt, Unity, Godot, Unreal |
| Cloud and infrastructure | Docker, Kubernetes/Helm, Terraform/OpenTofu, Pulumi, Bicep, AWS CDK, AWS, Azure, GCP, serverless, GitOps, secrets, Ansible, Nginx/Caddy/Traefik, Linux/systemd, Nix, service mesh, CI/CD, Git, Make/just, monorepos, config files |
| Observability | OpenTelemetry, Prometheus, Grafana, Loki, Tempo/Jaeger, logging, SLOs |
| Data and AI | PostgreSQL, Redis/Valkey, MongoDB, Kafka/RabbitMQ, Elasticsearch/OpenSearch, ORMs, pandas/Polars, notebooks, PyTorch/scikit-learn, LLM apps, Airflow/Dagster/dbt/Spark, Flink |
| Cross-cutting | REST/OpenAPI, GraphQL, gRPC, security (OWASP), accessibility (WCAG), i18n, WebSockets |
| Transformations | .NET Framework and .NET upgrades, Java and Spring Boot upgrades (OpenRewrite), Python version upgrades, TypeScript strict mode and Node/framework majors, raising test coverage to 90% |

## FAQ

**Does it need a config file?**
No. `.chef.md` at the project root is created only when you set a level or answer a question chef would otherwise ask again. Commit it to share the choices with your team.

**It costs more. Can I turn it down?**
`/chef:level lite` keeps every code rule but drops the council and the reviewer agent, which is where most of the extra cost goes.

**Will it rewrite my legacy code?**
No. Its style rules apply to the lines it adds or must change. Strict mode is asked first in an existing project, and `/chef:transform` keeps the diff to what the migration needs.

**How do I change a habit?**
Edit [`skills/chef/SKILL.md`](skills/chef/SKILL.md), or the stack's file in [`skills/chef/references/`](skills/chef/references/) (listed in [`INDEX.md`](skills/chef/references/INDEX.md)). Run `bash scripts/check.sh` before you push; CI runs it too.

**Why "chef"?**
Because the kitchen has rules, and the dish is tasted before it leaves.

## Benchmark details

Same prompt, same model (Sonnet 5.5), fresh git folder each time, run on Nov 19, 2026. Three arms: no plugin, chef 0.8.1 and chef 0.9.0. User settings, other plugins and MCP servers are off in every arm (`--setting-sources project --strict-mcp-config`); only the chef arms get `--plugin-dir`. Each prompt ends with "Work autonomously: nobody will answer questions."

The harness is in [`bench/`](bench/):

```bash
bash bench/run.sh <out-dir> 2 none= old=<chef-0.8.1-dir> new=<chef-dir>
python bench/score.py <out-dir> > scores.json
```

`run.sh` runs the arms of each task in parallel, and `score.py` needs pytest, pytest-cov, mypy, Ruff, PyYAML and a running Docker daemon (hadolint and promtool run from their official images).

| Task | Prompt, in short | What is checked |
|---|---|---|
| Python CLI | TOML endpoint validator, `find_invalid(path)` in `endpoints.py` | Hidden pytest, tests written, line coverage, `mypy --strict`, Ruff, tool config |
| Dockerfile + compose | Containerize a stdlib HTTP service with `/health` | `docker build`, `/health` answers, hadolint, digest pin, non-root, healthcheck, `.dockerignore`, `docker compose config`, `read_only` + `no-new-privileges` or `cap_drop: ALL`, resource limits |
| Prometheus | Scrape config, alerts for down, 5xx ratio > 5%, p95 > 500 ms, compose | `promtool check config --syntax-only`, `check rules`, `test rules`, `for`, `severity`, `summary`, `runbook_url`, `histogram_quantile` on `_bucket`, pinned image |

<details>
<summary><strong>Weak spots and limits</strong></summary>

- 2 runs per arm is a small sample, and the token counts vary a lot between runs (Docker with chef 0.8.1: 242k and 391k). The −11% is a mean over 6 runs per arm, not a guarantee per task; on Prometheus, 0.9.0 used 7% more.
- No run used subagents, so these tasks measure the rules, not the council or the reviewer.
- Docker Desktop stopped at some point during the no-plugin and 0.8.1 runs, and was restarted before the 0.9.0 runs and the scoring. An agent that tried `docker build` in those runs may have failed. Every Docker output still built and answered `/health` at scoring time.
- Times are inflated by three runs in parallel on the same machine. Compare the arms, not the absolute seconds.
- Token counts per file in the "Where v0.9 saves" table are estimated at 4 bytes per token.
- The previous benchmark (0.8.1, five tasks: C#, TypeScript, Python, Docker + CI, Python 3.8 to 3.13 transformation) is in the git history of this README.

</details>
