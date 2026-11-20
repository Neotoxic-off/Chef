# Raise an existing repo to the 90% coverage gate

Builds on SKILL.md (Tests) and the language file of each stack in the repo. Written for diff-cover 11.0.4 (Nov 2026), not benchmarked; each language's coverage tool is verified in its own file.

## When it applies

- The repo has no coverage gate, or line or branch coverage is under the house 90% (SKILL.md: CI fails under 90% line *and* branch).
- The goal is tests, not production changes. Production code changes only where a test needs a seam (inject the clock, the network, the filesystem), and each one gets its own small batch.

## Coverage tool per stack

Use the tool and gate the language file names; do not pick another.

| Stack | File | Tool |
|---|---|---|
| C# / .NET | `csharp.md` | MTP code coverage (`dotnet test --coverage`) or `coverlet.MTP` |
| TypeScript | `typescript.md` | `@vitest/coverage-v8`, `thresholds` in `vitest.config.ts` |
| Python | `python.md` | `pytest-cov`, `--cov-branch --cov-fail-under` |
| Java | `java.md` | JaCoCo `jacocoTestCoverageVerification` (LINE and BRANCH) |
| Kotlin | `kotlin.md` | Kover `minBound` (LINE and BRANCH) |
| Go, Rust, C, C++, Swift, PHP, Dart | each file | as named there |

## Steps

1. **Baseline.** Turn on line *and* branch coverage, run the full suite, record the numbers per module (package, project, folder). Commit the config with the gate at 90% line and branch from the start: no interim gate below it. Work on a branch: its CI fails the gate until the last batch lands.
2. **New code at 90% now.** Gate changed lines on every PR: `diff-cover coverage.xml --compare-branch=origin/main --fail-under=90` (reads Cobertura, Clover, JaCoCo XML or LCov; run with `uvx diff-cover` or `pipx run diff-cover`). diff-cover checks lines only; review branches in the report.
3. **Rank modules** by risk: money, security, parsing, then most-changed (`git log --format= --name-only | sort | uniq -c | sort -rn`), then lowest coverage. Exclude only generated code and thin UI views, with a comment saying why.
4. **One module per batch.** Write characterization tests first: they pin what the code does today, even where it looks wrong. Then unit tests for each branch and error path, integration tests for each boundary (Testcontainers where the language file says so).
5. **Module done.** A batch is done when its module reaches 90% line and 90% branch.
6. Mutation testing (the language file's tool) on the critical modules once they pass 90%.

Validation per batch: the full test suite, the batch's module at 90% line and branch, plus the linter and type checker. The repo-wide gate passes after the last batch. All tests deterministic: no real clock, random, network or sleep.

## Pitfalls

- Never lower a threshold, exclude a file to raise the number, skip or delete a failing test, or write a test with no assertion. Each one hides the gap instead of closing it.
- A characterization test that pins a bug: name it for what it does (`Parse_WithEmptyInput_ReturnsZero`), and report the suspect behavior. Do not fix the bug in the same batch.
- Branch coverage is usually far below line coverage: plan for it from the baseline.
- Diff holds only tests, coverage config and the seams the tests need. No refactor, rename or restyle of production code.

## Leave for the user

- Suspect behavior the characterization tests found: bug or feature.
- Production refactors bigger than a seam.
