<p align="center">
  <img src="assets/logo.png" width="160" alt="Chef logo">
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

## What it is

Chef is a [Claude Code](https://claude.com/claude-code) plugin that makes Claude follow one set of house coding habits on every task, in every project, without being reminded:

- **Priorities**: clarity, simplicity, maintainability, security. Too complex is wrong. Never assume, always verify.
- **Not sure? Ask.** Claude asks before guessing what you want.
- **Talk less, do what was asked**: answer first, no recap, no filler, no unrequested work.
- **Explicit types** on every variable, parameter, return and field, in every typed language.
- **SOLID**, readable code, few comments: if code needs many, it is not clear enough.
- **Tests**: unit and integration, 90% line and branch coverage gate, mutation testing on critical logic.
- **Never hide a warning or an error**: fix the cause, always. No suppression comments; lint rules that clash with these habits are turned off in config, with the reason.
- **`try`/`catch` only when nothing else works**: check first (`TryParse`, `dict.get`, `Result` types), except for files and network, where the operation itself is the check.
- **Strict mode**: on by default in new projects, asked first in existing ones.
- **Before heavy commands** (builds, test suites, installs): check free RAM and CPU first, and ask if the machine is loaded.
- **WPF / WinUI / MAUI / Avalonia**: CommunityToolkit, always.
- **Transform** (`/chef:transform <goal>`): upgrades and migrations in the AWS Transform style. Baseline, plan in a committed `TRANSFORM.md`, your approval, then small batches that are each validated, reviewed and committed.

Each stack has its own reference (linter, formatter, test runner, coverage tool, configs), loaded only when Claude works in it. Anything not listed is still covered: Claude looks up its official docs and standard tools first, then applies every rule.

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

## Council of agents

For decisions, new projects, new features and unclear requests, Claude acts as the lead and convenes a council from nine agents shipped with the plugin: three core members always, plus the two or three specialists the problem calls for. They work in parallel without seeing each other's answers, then cross-examine each other; the lead brings you the real choices.

| Agent | Seat | Role |
|---|---|---|
| `council-senior` | core | Knows the stack and the project; proposes the plan and what to reuse. |
| `council-skeptic` | core | Argues it will not work, with evidence, until the plan holds. |
| `council-novice` | core | Knows nothing; asks the simple questions about the need that experts skip. |
| `council-researcher` | specialist | Searches official docs, versions, known issues; cites every source. |
| `council-outsider` | specialist | Never reads the code; says what is correct and appropriate from first principles. |
| `council-security` | specialist | Attacks it: threat model, inputs, secrets, auth, supply chain. |
| `council-ops` | specialist | Runs it in production: deploy, observability, failure modes, rollback, cost. |
| `council-user` | specialist | Speaks for whoever uses the result: real need, UX, accessibility. |
| `council-maintainer` | specialist | Owns the code in two years: readability, tests, dependencies, cost of change. |

One more agent, `reviewer`, did not write the code: it checks the changes against the house rules before you see them. Every working agent ends with the same report: done, files, checks, not verified, risks, questions.

## Install

In Claude Code:

```
/plugin marketplace add Neotoxic-off/chef
/plugin install chef@chef
```

Update: `/plugin marketplace update chef`, then `/reload-plugins`.

## Usage

A `UserPromptSubmit` hook reminds Claude, on every prompt, to load the skill before the first edit or command of any development task. To call it explicitly:

```
/chef:chef
```

To upgrade or migrate a repository (.NET, Java, Python, Node versions, TypeScript strict mode, test coverage), run:

```
/chef:transform <goal>
```

It works like AWS Transform, inside one repository: it measures a baseline build and test run, writes a plan of small batches to `TRANSFORM.md`, has the council check it, and waits for your approval. Then each batch is edited, validated, reviewed and committed. A Stop hook, active only during a transform, keeps Claude from stopping while a batch is edited but not validated. The plan is committed, so a later session resumes where it stopped. Mainframe, VMware and multi-repo migrations are out of scope.

To change a habit, edit [`skills/chef/SKILL.md`](skills/chef/SKILL.md) or the stack's file in [`skills/chef/references/`](skills/chef/references/) (listed in [`INDEX.md`](skills/chef/references/INDEX.md)). Run `bash scripts/check.sh` before you push; CI runs it too.

## With and without chef

Same prompt, same model (Sonnet 5.5): *"Create a Python command-line tool that reads a TOML config file containing a list of endpoints (url, timeout in seconds), validates it, and prints which entries are invalid and why."* Below, the URL check from each output, unedited.

**Without chef**: one 50-line `validate_entry` doing everything, no types, section comments, no tests, no lint config.

```python
def validate_entry(entry):
    """Return a list of problems for one endpoint entry (empty if valid)."""
    if not isinstance(entry, dict):
        return [f"entry must be a table, got {type(entry).__name__}"]

    problems = []

    for key in entry.keys() - {"url", "timeout"}:
        problems.append(f"unknown key '{key}'")

    # url
    if "url" not in entry:
        problems.append("missing 'url'")
    else:
        url = entry["url"]
        if not isinstance(url, str):
            problems.append(f"'url' must be a string, got {type(url).__name__}")
        elif not url.strip():
            problems.append("'url' is empty")
        else:
            try:
                parts = urlsplit(url)
                host = parts.hostname
                parts.port  # raises ValueError if out of range / not numeric
            except ValueError as exc:
                problems.append(f"'url' is malformed ({exc})")
            else:
                if parts.scheme.lower() not in ALLOWED_SCHEMES:
                    ...
    # timeout
    ...
```

**With chef**: one small typed function per check, early returns, named constants, plus `pyproject.toml` with Ruff and `mypy --strict`, and 37 pytest tests that pass with 99% coverage.

```python
ENDPOINTS_KEY: str = "endpoints"
ALLOWED_SCHEMES: frozenset[str] = frozenset({"http", "https"})
ALLOWED_KEYS: frozenset[str] = frozenset({"url", "timeout"})

EXIT_OK: int = 0
EXIT_INVALID_ENTRIES: int = 1
EXIT_UNREADABLE: int = 2


@dataclass(frozen=True, slots=True)
class Issue:
    location: str
    reason: str


def validate_url(value: object) -> str | None:
    """Return why the URL is invalid, or None when it is valid."""
    if not isinstance(value, str):
        return f"url must be a string, got {type(value).__name__}"
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
        return f"url scheme must be http or https, got {parts.scheme or 'none'!r}"
    if not hostname:
        return "url has no host"
    if port == 0:
        return "url port must not be 0"
    return None
```

## Benchmark

Same prompt, same model (Sonnet 5.5), fresh folder each time. The only difference: the chef plugin. Every other plugin is off in both arms. 4 tasks × 2 runs per arm.

| Task | Metric | Without chef | With chef |
|---|---|---|---|
| C# library | Test cases written | 0 | 6.5 |
| | Tests pass | no tests | 2/2 |
| | `var` (inferred types) | 3 | 0 |
| | `TreatWarningsAsErrors` | 0/2 | 2/2 |
| Python CLI | Test cases written | 0 | 13.5 |
| | Tests pass | no tests | 2/2 |
| | Fully annotated functions | 0% | 100% |
| | Ruff + strict type checker config | 0/2 | 2/2 |
| | `try` blocks | 4 | 2 |
| TypeScript module | Test cases written | 0 | 6 |
| | Tests pass | 0/1 | 0/2 |
| | `strict` tsconfig | 1/2 | 2/2 |
| | Untyped `const`/`let` | 2.5 | 2.5 |
| Dockerfile + CI | `HEALTHCHECK` | 0/2 | 2/2 |
| | Base image pinned by digest, actions pinned by SHA | 0/2 | 0/2 |
| All tasks | Comment lines per code line | 0.05–0.11 | 0.01–0.03 |
| | Cost per task | $0.08–0.12 | $0.15–0.29 |
| | Time per task | 10–24 s | 18–69 s |

Chef makes Claude write tests, explicit types and strict lint configs it otherwise skips, at about 2× the cost and 2.5× the time. Weak spots seen: the TypeScript tests it wrote did not pass (cause not captured: this harness discarded the logs), TypeScript declarations were no more typed than without chef, and digest/SHA pinning was not applied. Chef did read the Docker rules (`HEALTHCHECK` comes only from them), but the benchmark gave Claude no tool to look up a real digest or SHA, so it did not invent one.

Limits: 2 runs per arm is a small sample; type and comment metrics are regex heuristics, except Python annotations (parsed with `ast`).
