<p align="center">
  <img src="assets/logo.svg" width="160" alt="Chef logo">
</p>

<h1 align="center">Chef</h1>

<p align="center">
  <em>Your kitchen, your rules. Claude cooks the way you do.</em>
</p>

<p align="center">
  <img src="https://img.shields.io/github/stars/Neotoxic-off/chef?style=flat-square&color=D97757&label=stars" alt="Stars">
  <img src="https://img.shields.io/github/last-commit/Neotoxic-off/chef?style=flat-square&color=D97757&label=last%20commit" alt="Last commit">
  <img src="https://img.shields.io/badge/Claude%20Code-plugin-D97757?style=flat-square" alt="Claude Code plugin">
  <img src="https://img.shields.io/badge/languages-19-D97757?style=flat-square" alt="19 languages">
  <img src="https://img.shields.io/badge/devops-6%20tools-D97757?style=flat-square" alt="6 DevOps tools">
</p>

## What it is

Chef is a [Claude Code](https://claude.com/claude-code) plugin that makes Claude follow one set of house coding habits on every task, in every project, without being reminded:

- **Priorities**: clarity, simplicity, maintainability, security. Too complex is wrong. Never assume, always verify.
- **Explicit types** on every variable, parameter, return and field, in every typed language.
- **SOLID**, readable code, few comments: if code needs many, it is not clear enough.
- **Tests**: unit and integration, 90% line and branch coverage gate, mutation testing on critical logic.
- **Never hide a warning or an error**: fix the cause, always.
- **WPF / WinUI**: CommunityToolkit, always.

Each stack has its own reference (linter, formatter, test runner, coverage tool, configs), loaded only when Claude works in it:

| Languages | DevOps and tools |
|---|---|
| C#/.NET, TypeScript/JS, Python, Rust, Go, C, C++, Java, Kotlin, Swift, Dart/Flutter, PHP, Ruby, Scala, Elixir, Lua, Bash, PowerShell, SQL | Docker, Kubernetes/Helm, Terraform/OpenTofu, CI/CD, Ansible, Git |

## Install

In Claude Code:

```
/plugin marketplace add Neotoxic-off/chef
/plugin install chef@chef
```


Update: `/plugin marketplace update chef`.

## Usage

Claude loads the skill by itself on coding tasks. To call it explicitly:

```
/chef:chef
```

To change a habit, edit [`skills/chef/SKILL.md`](skills/chef/SKILL.md) or the stack's file in [`skills/chef/references/`](skills/chef/references/), then push.

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

Same prompt, same model (Sonnet 5.5), fresh folder each time. The only difference: the chef plugin. Every other plugin is off in both arms. 4 tasks × 2 runs per arm, measured by [`bench/run.py`](bench/run.py).

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

Full table: [`bench/results.md`](bench/results.md). Raw data: [`bench/results.jsonl`](bench/results.jsonl). Re-run: `python bench/run.py run && python bench/run.py report`.

Limits: 2 runs per arm is a small sample; type and comment metrics are regex heuristics, except Python annotations (parsed with `ast`).
