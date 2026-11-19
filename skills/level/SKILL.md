---
name: level
description: Set the chef level (lite, full or max) for this project in .chef.md. Use when the user runs /chef:level <lite|full|max> or asks to change how much process chef applies.
---

# Level

The argument is: $ARGUMENTS

The levels are defined in the `chef:chef` skill, section "Levels and project config".

## Valid argument: `lite`, `full` or `max`

1. `.chef.md` exists at the project root: set its `level:` line to the argument, or add that line at the top if there is none. Change nothing else.
2. `.chef.md` is missing: ask the user once (AskUserQuestion) whether to create it. On yes, create it with only `level: <argument>`. On no, use the level for this session only.
3. Confirm in one line, e.g. `Level: lite (saved in .chef.md).`

## No argument or an invalid one

Change nothing. Show the current level (`level:` in `.chef.md`, else `full (default)`) and this table:

| Level | Behavior |
|---|---|
| `lite` | All code rules, no council, no reviewer, few agents, asks only when blocked. |
| `full` | Default: the chef skill as written. |
| `max` | Council on every non-trivial change, reviewer on every change. |

End with the usage line: `/chef:level lite|full|max`.
