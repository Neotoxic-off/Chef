---
name: transform
description: Upgrade or migrate a codebase in small, validated, reviewed batches tracked in TRANSFORM.md (framework or language version upgrade, strict mode, test coverage, dependency migration). Use when the user runs /chef:transform <goal> or asks for a multi-step upgrade or migration of one repository.
hooks:
  Stop:
    - hooks:
        - type: command
          command: 'bash "${CLAUDE_PLUGIN_ROOT}/skills/transform/scripts/stop-gate.sh"'
          timeout: 10
---

# Transform

You run a code transformation the way AWS Transform does: assess, plan, then change in small batches that each prove they still work. The goal is: $ARGUMENTS

Also follow the `chef:chef` skill: invoke it now if it is not loaded. Its rules apply, except where migration mode below narrows them.

## Scope

One repository, one goal. Mainframe (COBOL), VMware and fleets of many repositories are out of scope: the official AWS Transform plugin covers those. Say so and stop.

No goal given, or the goal is vague? Ask the user (AskUserQuestion) before anything else.

## Resume

If `TRANSFORM.md` exists at the project root, read it. Same goal and a batch not `[x]`: do not assess again, continue from the first batch that is not `[x]`. A batch marked `[~]` was interrupted: check `git status` and `git diff`, then finish or restart that batch. Check `git status` for the last `[x]` batch too: a stop can fall between ticking and committing.

Otherwise (another goal, or every batch `[x]`), ask the user whether to replace the old plan before you start.

## 1. Assess

Read before you change anything:

- Versions: language, runtime, framework, SDK, build tool, each with the file that pins it.
- Dependencies: direct ones, their current and target versions, the ones with breaking changes or no release for the target.
- Tests and coverage: what exists, how to run it, the current coverage number if a tool is set up.
- Baseline: run the build and the full test suite once, before any change. Record the exact commands, the result, the failing tests and the warning count. Failures that exist before the change are part of the baseline: list them, do not fix them unless the plan says so.

Look up the official migration guide for the target version. Never assume what changed between versions.

## Recipes

For a common transformation, open `${CLAUDE_PLUGIN_ROOT}/skills/chef/references/INDEX.md` and read the matching recipe before planning:

| Goal | Recipe |
|---|---|
| .NET or .NET Framework upgrade | `dotnet-upgrade.md` |
| TypeScript strict mode, TypeScript, Node or framework major upgrade | `ts-strict.md` |
| Raise test coverage | `test-coverage.md` |
| Java version upgrade | `java-upgrade.md` |
| Python version upgrade | `python-upgrade.md` |

If the recipe is not in the index yet, say so and work from the official docs.

## 2. Plan

Write `TRANSFORM.md` at the project root, the folder Claude Code was started in (the Stop hook reads it there):

```markdown
# Transform: <goal>

Target: <runtime and version, e.g. Python 3.13>

## Inventory
<versions, dependencies, tests, coverage from the assessment>

## Baseline
<commands, result, failing tests, warnings, date and commit>

## Council
<members, and what changed in the plan because of them>

## Batches
- [ ] Batch 1: <one small change>. Validate: `<command>`
- [ ] Batch 2: ...

## Report
<filled at the end>
```

- Batches are small and ordered: each one builds and passes its validation on its own. Dependencies before the code that needs them.
- Every batch names its validation command: build plus the tests it touches, or the full suite when unsure.
- Validation runs on the `Target:` runtime, never on whatever is installed: e.g. `uv run --python 3.13 pytest`, `nvm exec 22 npm test`, a pinned container image.

Before the user sees it, convene the council on the plan (chef's `team.md`): core plus the specialists the migration calls for. Fix the plan with what holds up; put the open disagreements in front of the user. Record the members and what changed in `## Council`. At `lite` or with `council: off`, when the user declines the council, write `Skipped: <level or setting>` under `## Council` instead.

Show the plan and ask the user to approve it (AskUserQuestion). Do not edit code or commit before they approve. Their approval covers the plan commit (`chore: transform plan for <goal>`) and one commit per batch.

## 3. Batches

Batch markers in `TRANSFORM.md`: `[ ]` not started, `[~]` in progress, `[x]` validated and committed. A Stop hook blocks the end of your turn while a batch is `[~]`, while a batch is `[x]` and the plan lacks `Target:` or `## Council`, and while there are more `[x]` batches than commits with `transform batch` in the subject: one commit per batch, never merged.

For each batch, in order:

1. Mark it `[~]`.
2. Make the edit. Nothing outside the batch.
3. Run its validation command. Formatter checks cover only the files the batch changed: formatting failures already in the baseline stay, unless the user approves a separate formatting batch. It fails: fix the cause. Never skip, delete or weaken a test, and never lower a threshold to pass.
4. Give the batch diff (`git diff`) to the `reviewer` agent. Fix what it confirms, then validate again.
5. Mark it `[x]`, then commit the code and `TRANSFORM.md` together: `<type>: transform batch <n>: <what>`.

Two fixes in a row fail, or the batch needs a decision? Leave it `[~]`, tell the user what fails and the options (fix further, split the batch, revert it), and ask. The hook blocks that stop once, then allows the next one.

## Migration mode

The diff holds only what the migration needs.

- Do not restyle, reformat or retype legacy lines the migration does not touch, even when they break chef's rules.
- Chef's style rules (types per the chef skill: signatures and public fields typed, locals per the language's idiom, SOLID, naming) apply to new code and to lines you must change anyway.
- A problem you see on the way goes in the report as a follow-up, not in the diff.

## 4. Report

When every batch is `[x]`, fill `## Report` in `TRANSFORM.md`:

- Before and after: versions, build result, tests passed and failed, warnings, coverage.
- Not verified: what was not run or not checked (other platforms, deploy, manual flows, performance), said plainly.
- Follow-ups: problems seen but left out of the migration.

Run the full baseline commands again for the after column. Commit the report, then tell the user the result in a few lines.
